from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from trustdata.control import create_app


ROOT = Path(__file__).resolve().parents[1]


def make_client(tmp_path: Path) -> TestClient:
    (tmp_path / "configs").mkdir(exist_ok=True)
    (tmp_path / "product").mkdir(exist_ok=True)
    (tmp_path / "product" / "control.html").write_text("<html>console</html>", encoding="utf-8")
    (tmp_path / "configs" / "trust.yaml").write_text((ROOT / "configs" / "trust.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "configs" / "llm_mining.yaml").write_text((ROOT / "configs" / "llm_mining.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    return TestClient(create_app(tmp_path))


def wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(80):
        payload = client.get(f"/api/jobs/{job_id}").json()
        if payload["state"] in {"succeeded", "failed"}:
            return payload
        time.sleep(0.025)
    raise AssertionError("job did not finish")


def test_config_masks_key_and_persists_only_to_dotenv(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.put("/api/config/llm", json={"config": {"llm": {"model": "local-model"}}, "api_key": "super-secret-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_key_configured"] is True
    assert "super-secret-key" not in response.text
    assert "super-secret-key" in (tmp_path / ".env").read_text(encoding="utf-8")
    assert "super-secret-key" not in (tmp_path / "configs" / "llm_mining.yaml").read_text(encoding="utf-8")


def test_upload_preflight_and_assessment_job_are_isolated(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    content = b"record_id,entity_id,rating\nr1,e1,4.5\nr2,e1,3.5\n"
    upload = client.post("/api/uploads", files={"file": ("reviews.csv", content, "text/csv")})
    assert upload.status_code == 200
    assert upload.json()["preview"]["canonical_missing"] == []
    started = client.post("/api/jobs", json={"kind": "assess", "params": {"upload_id": upload.json()["upload_id"], "scenario": "ranking_integrity"}})
    assert started.status_code == 200
    job = wait_for_job(client, started.json()["id"])
    assert job["state"] == "succeeded"
    assert any(item["path"] == "results/scored.csv" for item in job["artifacts"])
    assert "outputs/ui-runs/" in job["workspace"]
    restarted = make_client(tmp_path)
    assert any(item["id"] == job["id"] for item in restarted.get("/api/jobs").json())


def test_job_allowlist_and_artifact_path_protection(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.post("/api/jobs", json={"kind": "arbitrary_shell", "params": {}}).status_code == 400
    assert client.get("/api/jobs/not-a-job/artifacts/../../.env").status_code in {404, 400}
