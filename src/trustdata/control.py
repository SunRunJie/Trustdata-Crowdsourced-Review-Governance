"""Local-only API backing the TrustData visual control console.

The console deliberately exposes a small, allow-listed set of operations.  It
is not a remote execution service: it is designed for a single user running on
the same machine as this repository.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hmac import compare_digest
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .assessment import REQUIRED_FIELDS, assess_records, prepare_canonical_records
from .env import load_env_file, set_env_value
from .io import SUPPORTED_SUFFIXES, read_table, write_table
from .llm_mining import _normalise_platform_domains


MAX_UPLOAD_BYTES = 200 * 1024 * 1024
JOB_KINDS = {
    "assess",
    "mine",
    "trustdata",
    "verify_manifest",
    "tests",
    "publish_dashboard",
}
_CONFIG_KEYS = {
    "llm": {"api_type", "model", "api_key_env", "base_url", "max_tokens", "temperature"},
    "crawl": {"request_delay", "max_pages_total", "max_pages_per_entity", "user_agent", "request_timeout", "platform_domains"},
    "verification": {"min_citation_score", "verification_level"},
    "output": {"include_source_url", "include_citation_snippet", "include_content_hash"},
}
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONSOLE_SESSION_COOKIE = "trustdata_console_session"
_CSRF_HEADER = "x-csrf-token"
_SESSION_TTL_SECONDS = 2 * 60 * 60
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_relative(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(400, "路径必须位于当前任务工作区内")
    return candidate


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _masked(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}{'*' * max(4, len(value) - 7)}{value[-4:]}"


class LocalRequestGuard:
    """Require same-origin, session-bound writes for the local console."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _host(request: Request) -> str:
        host = request.headers.get("host", "")
        if not host or "," in host or "@" in host or any(char.isspace() for char in host):
            raise HTTPException(403, "控制台只接受本机 Host")
        try:
            from urllib.parse import urlsplit

            parsed = urlsplit(f"//{host}")
            port = parsed.port
        except ValueError as exc:
            raise HTTPException(403, "控制台 Host 格式无效") from exc
        if (
            parsed.netloc != host
            or parsed.username
            or parsed.password
            or parsed.hostname not in _LOCAL_HOSTS
        ):
            raise HTTPException(403, "控制台只接受本机 Host")
        if port is not None and not 1 <= port <= 65535:
            raise HTTPException(403, "控制台 Host 端口无效")
        return host

    @staticmethod
    def _cleanup(sessions: dict[str, tuple[str, float]], now: float) -> None:
        for session_id, (_, expires_at) in list(sessions.items()):
            if expires_at <= now:
                del sessions[session_id]

    def _session(self, request: Request) -> tuple[str, str]:
        import time

        now = time.time()
        requested = request.cookies.get(_CONSOLE_SESSION_COOKIE, "")
        with self._lock:
            self._cleanup(self._sessions, now)
            existing = self._sessions.get(requested)
            if existing is not None:
                token, _ = existing
                self._sessions[requested] = (token, now + _SESSION_TTL_SECONDS)
                return requested, token
            session_id = secrets.token_urlsafe(32)
            token = secrets.token_urlsafe(32)
            self._sessions[session_id] = (token, now + _SESSION_TTL_SECONDS)
            return session_id, token

    def csrf_response(self, request: Request) -> JSONResponse:
        self._host(request)
        session_id, token = self._session(request)
        response = JSONResponse({"csrf_token": token, "expires_in": _SESSION_TTL_SECONDS})
        response.set_cookie(
            _CONSOLE_SESSION_COOKIE,
            session_id,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=_SESSION_TTL_SECONDS,
            path="/",
        )
        return response

    def require_write(self, request: Request, media_type: str) -> None:
        host = self._host(request)
        expected_origin = f"{request.url.scheme}://{host}"
        if request.url.scheme != "http" or request.headers.get("origin") != expected_origin:
            raise HTTPException(403, "写操作必须来自同源本机控制台")
        received_media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
        if received_media_type != media_type:
            raise HTTPException(415, f"写操作必须使用 {media_type}")
        session_id = request.cookies.get(_CONSOLE_SESSION_COOKIE, "")
        supplied = request.headers.get(_CSRF_HEADER, "")
        import time

        with self._lock:
            self._cleanup(self._sessions, time.time())
            entry = self._sessions.get(session_id)
        if entry is None or not supplied or not compare_digest(entry[0], supplied):
            raise HTTPException(403, "CSRF token 无效或已过期；请刷新页面后重试")


class LocalJobs:
    """Thread-safe, in-memory job index with durable job folders and logs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.runs_root = root / "outputs" / "ui-runs"
        self.upload_root = self.runs_root / "uploads"
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trustdata-ui")

    def upload(self, source: UploadFile) -> dict[str, Any]:
        suffix = Path(source.filename or "").suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES | {".yaml", ".yml"}:
            raise HTTPException(400, "仅支持 CSV、JSON、JSONL、Parquet 或 YAML 文件")
        upload_id = uuid.uuid4().hex
        destination = self.upload_root / f"{upload_id}{suffix}"
        total = 0
        with destination.open("wb") as handle:
            while chunk := source.file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    destination.unlink(missing_ok=True)
                    raise HTTPException(413, "文件超过 200 MB 限制")
                handle.write(chunk)
        payload: dict[str, Any] = {
            "upload_id": upload_id,
            "filename": Path(source.filename or destination.name).name,
            "bytes": total,
            "suffix": suffix,
        }
        if suffix in SUPPORTED_SUFFIXES:
            try:
                frame = read_table(destination)
                payload["preview"] = {
                    "rows": int(len(frame)),
                    "columns": [str(column) for column in frame.columns],
                    "sample": json.loads(frame.head(8).to_json(orient="records", force_ascii=False, date_format="iso")),
                    "canonical_missing": [field for field in REQUIRED_FIELDS if field not in frame.columns],
                }
            except Exception as exc:
                payload["preview_error"] = str(exc)
        return payload

    def create(self, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        if kind not in JOB_KINDS:
            raise HTTPException(400, f"不支持的任务类型：{kind}")
        job_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        workspace = self.runs_root / job_id
        workspace.mkdir(parents=True)
        job = {
            "id": job_id,
            "kind": kind,
            "state": "queued",
            "created_at": _utc_now(),
            "started_at": None,
            "finished_at": None,
            "workspace": workspace,
            "events": [],
            "params": params,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        self._snapshot(job)
        self._executor.submit(self._execute, job_id)
        return self.public(job)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            record = self.runs_root / job_id / "run.json"
            if not record.is_file() or record.parent.parent != self.runs_root:
                raise HTTPException(404, "未找到任务")
            saved = json.loads(record.read_text(encoding="utf-8"))
            job = {
                "id": job_id, "kind": saved.get("kind", "unknown"), "state": saved.get("state", "unknown"),
                "created_at": saved.get("created_at"), "started_at": saved.get("started_at"), "finished_at": saved.get("finished_at"),
                "workspace": record.parent, "events": self._saved_events(record.parent), "params": saved.get("params", {}), "error": saved.get("error"),
            }
            with self._lock:
                self._jobs[job_id] = job
        return job

    def list(self) -> list[dict[str, Any]]:
        known = {job_id: self.get(job_id) for job_id in list(self._jobs)}
        for record in self.runs_root.glob("20*/run.json"):
            known.setdefault(record.parent.name, self.get(record.parent.name))
        return [self.public(job) for job in sorted(known.values(), key=lambda item: str(item["created_at"]), reverse=True)]

    @staticmethod
    def _saved_events(workspace: Path) -> list[dict[str, Any]]:
        log = workspace / "run.log"
        if not log.is_file():
            return []
        return [
            {"index": index, "at": "历史日志", "message": line}
            for index, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines())
        ]

    def public(self, job: dict[str, Any], after: int | None = None) -> dict[str, Any]:
        events = job["events"] if after is None else job["events"][max(0, after):]
        return {
            "id": job["id"], "kind": job["kind"], "state": job["state"],
            "created_at": job["created_at"], "started_at": job["started_at"],
            "finished_at": job["finished_at"], "error": job["error"],
            "workspace": str(job["workspace"].relative_to(self.root)).replace("\\", "/"),
            "events": events, "event_count": len(job["events"]),
            "artifacts": self._artifacts(job["workspace"]),
        }

    def _append(self, job: dict[str, Any], text: str) -> None:
        clean = self._redact(text.rstrip())
        if not clean:
            return
        event = {"index": len(job["events"]), "at": _utc_now(), "message": clean}
        with self._lock:
            job["events"].append(event)
        (job["workspace"] / "run.log").open("a", encoding="utf-8").write(clean + "\n")

    def _redact(self, text: str) -> str:
        env_path = self.root / ".env"
        if not env_path.is_file():
            return text
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                value = line.split("=", 1)[1].strip().strip("'\"")
                if len(value) >= 4:
                    text = text.replace(value, "[REDACTED]")
        return text

    def _snapshot(self, job: dict[str, Any]) -> None:
        safe_params = {key: value for key, value in job["params"].items() if "key" not in key.lower()}
        payload = {"id": job["id"], "kind": job["kind"], "state": job["state"], "params": safe_params,
                   "created_at": job["created_at"], "started_at": job["started_at"], "finished_at": job["finished_at"], "error": job["error"]}
        (job["workspace"] / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _copy_upload(self, upload_id: str, workspace: Path) -> Path:
        candidates = list(self.upload_root.glob(f"{upload_id}.*"))
        if len(candidates) != 1:
            raise ValueError("上传文件不存在或已失效")
        source = candidates[0]
        destination = workspace / "input" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def _run_subprocess(self, job: dict[str, Any], command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        self._append(job, "$ " + " ".join(command[1:]))
        process = subprocess.Popen(command, cwd=cwd or self.root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace")
        assert process.stdout is not None
        for line in process.stdout:
            self._append(job, line)
        status = process.wait()
        if status:
            raise RuntimeError(f"任务进程退出码为 {status}")

    def _execute(self, job_id: str) -> None:
        job = self.get(job_id)
        with self._lock:
            job["state"] = "running"
            job["started_at"] = _utc_now()
        self._snapshot(job)
        try:
            self._append(job, f"开始执行 {job['kind']}")
            self._dispatch(job)
        except Exception as exc:
            with self._lock:
                job["state"] = "failed"
                job["error"] = self._redact(str(exc))
            self._append(job, f"[FAIL] {exc}")
        else:
            with self._lock:
                job["state"] = "succeeded"
            self._append(job, "[OK] 任务完成")
        finally:
            with self._lock:
                job["finished_at"] = _utc_now()
            self._snapshot(job)

    def _dispatch(self, job: dict[str, Any]) -> None:
        kind, params, workspace = job["kind"], job["params"], job["workspace"]
        if kind == "assess":
            source = self._copy_upload(str(params.get("upload_id", "")), workspace)
            frame = prepare_canonical_records(read_table(source))
            config = _read_yaml(self.root / "configs" / "trust.yaml")
            scenario = str(params.get("scenario", "ranking_integrity"))
            scored = assess_records(frame, config, scenario)
            target = workspace / "results" / "scored.csv"
            write_table(scored, target)
            summary = {"records": int(len(scored)), "scenario": scenario,
                       "average_data_trust_score": float(scored["data_trust_score"].mean()),
                       "tier_distribution": {str(k): int(v) for k, v in scored["tier"].value_counts().items()}}
            (workspace / "results" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            self._append(job, f"已评估 {len(scored):,} 条记录")
        elif kind == "mine":
            from .llm_mining import run_mining
            load_env_file(self.root / ".env")
            task = str(params.get("task", "")).strip()
            task_upload_id = str(params.get("task_upload_id", ""))
            if task_upload_id:
                task_source: Path | str = self._copy_upload(task_upload_id, workspace)
                if task_source.suffix.lower() not in {".yaml", ".yml"}:
                    raise ValueError("任务文件必须是 YAML 格式")
            elif task:
                task_source = task
            else:
                raise ValueError("请填写自然语言挖掘任务或上传 YAML 任务文件")
            target = workspace / "results" / "mined.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            config_copy = workspace / "config" / "llm_mining.yaml"
            config_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root / "configs" / "llm_mining.yaml", config_copy)
            run_mining(config_copy, task_source, target, verbose=True)
            self._append(job, "挖掘结果与来源可用性报告已写入 results/")
        elif kind == "trustdata":
            command = [sys.executable, str(self.root / "scripts" / "run_trustdata.py"), "--output", str(workspace / "results"), "--processed", str(self.root / "data" / "processed")]
            self._run_subprocess(job, command)
        elif kind == "verify_manifest":
            run_id = str(params.get("run_id", ""))
            source_workspace = self.runs_root / run_id if run_id else workspace
            if source_workspace.parent != self.runs_root:
                raise ValueError("只能校验控制台工作区中的运行清单")
            manifest = source_workspace / "results" / "run_manifest.json"
            if not manifest.is_file():
                raise ValueError("目标运行尚无 results/run_manifest.json")
            self._run_subprocess(job, [sys.executable, str(self.root / "scripts" / "verify_run_manifest.py"), "--manifest", str(manifest)])
        elif kind == "publish_dashboard":
            if not bool(params.get("confirmed", False)):
                raise ValueError("发布正式演示产物需要明确确认")
            run_id = str(params.get("run_id", ""))
            source_workspace = self.runs_root / run_id
            source = source_workspace / "results"
            summary = source / "result_summary.json"
            manifest = source / "run_manifest.json"
            if source_workspace.parent != self.runs_root or not summary.is_file() or not manifest.is_file():
                raise ValueError("请选择一个成功完成的控制台受控基准运行")
            from .pipeline import _write_dashboard_script, _write_json
            dashboard = json.loads(summary.read_text(encoding="utf-8"))
            _write_json(self.root / "app" / "data" / "dashboard.json", dashboard)
            _write_dashboard_script(self.root / "product" / "dashboard-data.js", dashboard)
            self._append(job, "已发布产品看板")
        elif kind == "tests":
            self._run_subprocess(job, [sys.executable, "-m", "pytest", "-q"])

    def _artifacts(self, workspace: Path) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or path.name == "run.log" or path.stat().st_size > 20 * 1024 * 1024:
                continue
            relative = path.relative_to(workspace).as_posix()
            if relative.startswith("input/"):
                continue
            items.append({"path": relative, "bytes": path.stat().st_size, "suffix": path.suffix.lower()})
        return items


def create_app(root: Path) -> FastAPI:
    """Create the local control-console application for *root*."""
    root = root.resolve()
    jobs = LocalJobs(root)
    request_guard = LocalRequestGuard()
    app = FastAPI(title="TrustData Local Console", docs_url=None, redoc_url=None)
    product = root / "product"
    app.mount("/product", StaticFiles(directory=product), name="product")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        request_guard._host(request)
        session_id, _ = request_guard._session(request)
        response = HTMLResponse((product / "control.html").read_text(encoding="utf-8"))
        response.set_cookie(
            _CONSOLE_SESSION_COOKIE,
            session_id,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=_SESSION_TTL_SECONDS,
            path="/",
        )
        return response

    @app.get("/api/csrf")
    def csrf(request: Request) -> JSONResponse:
        return request_guard.csrf_response(request)

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return {
            "local_only": True,
            "python": sys.version.split()[0],
            "root": str(root),
            "env_configured": (root / ".env").is_file(),
            "recent_runs": sorted((path.name for path in (root / "outputs" / "ui-runs").glob("20*")), reverse=True)[:12],
        }

    @app.get("/api/config/llm")
    def get_llm_config() -> dict[str, Any]:
        config = _read_yaml(root / "configs" / "llm_mining.yaml")
        key_name = str(config.get("llm", {}).get("api_key_env", "LLM_API_KEY"))
        load_env_file(root / ".env")
        value = os.environ.get(key_name, "")
        return {"config": config, "api_key_env": key_name, "api_key_configured": bool(value), "api_key_masked": _masked(value)}

    @app.put("/api/config/llm")
    async def put_llm_config(request: Request) -> dict[str, Any]:
        request_guard.require_write(request, "application/json")
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(400, "配置必须是 JSON 对象")
        config = _read_yaml(root / "configs" / "llm_mining.yaml")
        supplied = payload.get("config", {})
        if not isinstance(supplied, dict):
            raise HTTPException(400, "config 必须是对象")
        for section, keys in _CONFIG_KEYS.items():
            values = supplied.get(section)
            if values is None:
                continue
            if not isinstance(values, dict) or set(values) - keys:
                raise HTTPException(400, f"{section} 包含不允许的配置项")
            config.setdefault(section, {}).update(values)
        platform_domains = config.get("crawl", {}).get("platform_domains")
        try:
            _normalise_platform_domains(platform_domains)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        key_name = str(config.get("llm", {}).get("api_key_env", "LLM_API_KEY"))
        if not _ENV_NAME.fullmatch(key_name):
            raise HTTPException(400, "api_key_env 无效")
        api_key = payload.get("api_key")
        if api_key is not None:
            if not isinstance(api_key, str) or not api_key.strip():
                raise HTTPException(400, "API Key 不能为空")
            set_env_value(root / ".env", key_name, api_key.strip())
        (root / "configs" / "llm_mining.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return get_llm_config()

    @app.post("/api/uploads")
    def upload(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
        request_guard.require_write(request, "multipart/form-data")
        return jobs.upload(file)

    @app.post("/api/jobs")
    async def start_job(request: Request) -> dict[str, Any]:
        request_guard.require_write(request, "application/json")
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(400, "任务必须是 JSON 对象")
        kind = payload.get("kind")
        params = payload.get("params", {})
        if not isinstance(kind, str) or not isinstance(params, dict):
            raise HTTPException(400, "任务类型或参数无效")
        return jobs.create(kind, params)

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str) -> dict[str, Any]:
        return jobs.public(jobs.get(job_id))

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        return jobs.list()

    @app.get("/api/jobs/{job_id}/events")
    def job_events(job_id: str, after: int = 0) -> dict[str, Any]:
        return jobs.public(jobs.get(job_id), after=after)

    @app.get("/api/jobs/{job_id}/artifacts/{artifact_path:path}")
    def artifact(job_id: str, artifact_path: str) -> FileResponse:
        job = jobs.get(job_id)
        path = (job["workspace"] / _safe_relative(artifact_path)).resolve()
        if job["workspace"] not in path.parents or not path.is_file():
            raise HTTPException(404, "未找到任务产物")
        return FileResponse(path, filename=path.name)

    return app
