"""Serve the complete TrustData solution from the repository root."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local TrustData solution portal.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="127.0.0.1", help="Default is local-only access")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    required = [
        ROOT / "product" / "index.html",
        ROOT / "product" / "app.js",
        ROOT / "app" / "data" / "dashboard.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing solution assets: {missing}. Run scripts/run_trustdata.py first."
        )

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    url = f"http://{args.bind}:{args.port}/product/"
    try:
        with socketserver.ThreadingTCPServer((args.bind, args.port), handler) as server:
            server.daemon_threads = True
            print(f"[OK] TrustData solution portal: {url}")
            print("[INFO] Press Ctrl+C to stop the local service.")
            if not args.no_browser:
                threading.Timer(0.6, lambda: webbrowser.open(url)).start()
            server.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] TrustData local service stopped.")
    except OSError as exc:
        raise SystemExit(
            f"Cannot listen on {args.bind}:{args.port}: {exc}. Try --port 8080."
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
