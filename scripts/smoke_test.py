#!/usr/bin/env python3
"""Project smoke test runner.

Runs local checks to verify DB init, one-shot fetch, and (if Flask is installed)
starts the web server briefly and validates API endpoints.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def http_json(url: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return True, f"status={resp.status} items={len(payload) if isinstance(payload, list) else 'n/a'}"
    except urllib.error.URLError as exc:
        return False, str(exc)


def main() -> int:
    print("== Smoke test: syntax checks ==")
    ok, out = run_cmd([sys.executable, "-m", "py_compile", "app.py", "db.py", "fetch_trades.py"])
    print("PASS" if ok else "FAIL", "py_compile")
    if not ok:
        print(out)
        return 1

    print("\n== Smoke test: database init ==")
    ok, out = run_cmd([sys.executable, "db.py"])
    print("PASS" if ok else "FAIL", "db.py")
    if out:
        print(out)
    if not ok:
        return 1

    print("\n== Smoke test: one-shot sync ==")
    ok, out = run_cmd([sys.executable, "fetch_trades.py"])
    print("PASS" if ok else "FAIL", "fetch_trades.py")
    if out:
        print(out)
    if not ok:
        return 1

    print("\n== Smoke test: API endpoints (requires Flask installed) ==")
    try:
        import flask  # noqa: F401
    except Exception:
        print("SKIP Flask not installed in current environment.")
        return 0

    server = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        time.sleep(2)
        ok1, msg1 = http_json("http://127.0.0.1:5000/api/traders")
        print(("PASS" if ok1 else "FAIL"), "/api/traders", msg1)

        # Query first trader if present.
        if ok1:
            with urllib.request.urlopen("http://127.0.0.1:5000/api/traders", timeout=5) as resp:
                traders = json.loads(resp.read().decode("utf-8"))
            if traders:
                addr = traders[0]["address"]
                ok2, msg2 = http_json(f"http://127.0.0.1:5000/api/traders/{addr}/trades")
                print(("PASS" if ok2 else "FAIL"), f"/api/traders/{addr}/trades", msg2)
                if not ok2:
                    return 1
        if not ok1:
            return 1
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
