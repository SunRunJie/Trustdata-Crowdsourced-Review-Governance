"""Start the local TrustData visual control console."""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path


# Some Windows terminals still expose a legacy code page.  Do not let an
# informational Chinese message prevent the local service from starting.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.control import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local TrustData visual control console.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="127.0.0.1", help="Only local loopback addresses are allowed")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.bind not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("TrustData 控制台仅支持本机回环地址（127.0.0.1、localhost 或 ::1）。")
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("缺少控制台依赖。请运行 .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt") from exc

    url = f"http://{args.bind}:{args.port}/"
    try:
        print(f"[OK] TrustData 本机控制台：{url}")
        print("[INFO] 仅本机可访问；按 Ctrl+C 停止服务。")
        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        uvicorn.run(create_app(ROOT), host=args.bind, port=args.port, log_level="warning")
    except KeyboardInterrupt:
        print("\n[OK] TrustData local service stopped.")
    except OSError as exc:
        raise SystemExit(
            f"Cannot listen on {args.bind}:{args.port}: {exc}. Try --port 8080."
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
