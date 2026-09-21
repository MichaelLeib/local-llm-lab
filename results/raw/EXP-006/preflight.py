#!/usr/bin/env python3
"""Non-inference EXP-006 readiness check.

This script never starts TinyTitan, loads a model, starts a server, or sends a
request. It only verifies files, host state, and the explicit inference gate.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = ROOT / "source" / "tinytitan"
MODEL = ROOT / "model" / "qwen3.8-flash-next_125B_A6B_4Bit"
BIN = SOURCE / ".build" / "release"


def run(*args: str) -> str:
    p = subprocess.run(args, text=True, capture_output=True)
    return p.stdout.strip() or p.stderr.strip()


def main() -> int:
    checks: dict[str, object] = {}
    checks["source_exists"] = SOURCE.is_dir()
    checks["model_exists"] = MODEL.is_dir()
    checks["manifest_exists"] = (MODEL / "manifest.json").is_file()
    checks["receipt_exists"] = (MODEL / "verified-install.json").is_file()
    checks["repacker_arm64"] = run("lipo", "-archs", str(BIN / "TinyTitanRepack")) == "arm64"
    checks["cli_arm64"] = run("lipo", "-archs", str(BIN / "TinyTitanCLI")) == "arm64"
    checks["server_arm64"] = run("lipo", "-archs", str(BIN / "TinyTitanServer")) == "arm64"
    checks["swap"] = run("sysctl", "-n", "vm.swapusage")
    checks["memory_pressure"] = run("memory_pressure", "-Q")
    checks["disk"] = run("df", "-h", "/")
    checks["competing_processes"] = run("pgrep", "-af", "TinyTitanCLI|TinyTitanServer|TinyTitanRepack|slipstream|mlx_lm|llama-server")
    if checks["manifest_exists"]:
        try:
            checks["manifest_json"] = json.loads((MODEL / "manifest.json").read_text())
        except Exception as exc:  # pragma: no cover - diagnostic path
            checks["manifest_json_error"] = repr(exc)
    checks["inference_gate"] = "not_consumed_by_preflight"
    out = ROOT / "preflight-latest.json"
    out.write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"artifact": str(out), "checks": checks}, indent=2))
    required = ["source_exists", "manifest_exists", "receipt_exists", "repacker_arm64", "cli_arm64", "server_arm64"]
    return 0 if all(checks.get(k) is True for k in required) else 2


if __name__ == "__main__":
    raise SystemExit(main())
