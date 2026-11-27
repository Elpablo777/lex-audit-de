"""Startet FastAPI-Backend (:8010) und Next.js-Portal (:3000) gemeinsam mit einem Befehl."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _api_healthy(url: str = "http://127.0.0.1:8010/api/v1/health") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.0) as resp:
            return int(resp.status) == 200
    except Exception:
        return False


def main() -> int:
    pnpm_bin = "pnpm.cmd" if os.name == "nt" else "pnpm"
    api_proc: subprocess.Popen[bytes] | None = None

    if not _api_healthy():
        print("[lexaudit] Starte FastAPI-Backend auf http://127.0.0.1:8010 ...")
        api_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "lexaudit_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8010",
                "--timeout-keep-alive",
                "75",
            ],
            cwd=str(ROOT),
        )
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if _api_healthy():
                break
            time.sleep(0.35)
    else:
        print("[lexaudit] FastAPI-Backend läuft bereits auf http://127.0.0.1:8010.")

    print("[lexaudit] Starte Next.js-Webportal auf http://127.0.0.1:3000 ...")
    env = dict(os.environ)
    env["LEXAUDIT_WEB_ONLY"] = "1"
    mode = "dev" if "--dev" in sys.argv else "start:web"
    web_cmd = [pnpm_bin, "--dir", "apps/web", "dev:web" if mode == "dev" else "start:web"]
    web_proc = subprocess.Popen(web_cmd, cwd=str(ROOT), env=env)

    def _shutdown(*_args: object) -> None:
        for proc in (web_proc, api_proc):
            if proc and proc.poll() is None:
                proc.terminate()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        return web_proc.wait()
    finally:
        for proc in (web_proc, api_proc):
            if proc and proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
