"""Run all Day 26 demos and save evidence. Uses Gemini/WeatherAPI quota."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def main():
    REPORTS.mkdir(exist_ok=True)
    (ROOT / ".lab-runtime").mkdir(exist_ok=True)
    secrets = []
    for location in ("04-lab/mcp-client/.env", "04-lab/mcp-server/.env"):
        for name, value in dotenv_values(ROOT / location).items():
            if "KEY" in name and value:
                secrets.append(value)

    def redact(text):
        for value in secrets:
            text = text.replace(value, "[REDACTED]")
        return text

    cases = (
        ("lab01", [sys.executable, "01-function-calling/weather_function_calling.py"], "[model yêu cầu]"),
        ("lab02", [sys.executable, "02-mcp-basics/weather_client.py"], "Haiphong: 33"),
        ("registry", [sys.executable, "03-production/registry_client.py"], "Best match: get_weather_v2"),
        ("versioning", [sys.executable, "03-production/versioned_client.py"], '"api_version": "2.0"'),
        ("auth", [sys.executable, "03-production/verify_auth.py"], "PASS auth"),
        ("lab04", [str(ROOT / "04-lab/mcp-client/.venv/Scripts/python.exe"),
                   "04-lab/mcp-client/verify_setup.py", "--agent", "--output", "reports/lab04-verification.json"],
                   "All requested checks passed."),
    )
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "checks": [], "passed": False}
    for name, command, marker in cases:
        try:
            result = subprocess.run(command, cwd=ROOT,
                                    env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                                    capture_output=True, encoding="utf-8", timeout=360)
            passed = result.returncode == 0 and marker in result.stdout
            if name == "lab01":
                passed = passed and result.stdout.count("[app thực thi]") >= 2 and "29°C" in result.stdout and "30°C" in result.stdout
            (REPORTS / f"{name}-output.txt").write_text(redact(result.stdout), encoding="utf-8")
            (ROOT / ".lab-runtime" / f"{name}-verification.err.log").write_text(redact(result.stderr), encoding="utf-8")
            summary["checks"].append({"name": name, "passed": passed, "exit_code": result.returncode})
        except subprocess.TimeoutExpired:
            passed = False
            summary["checks"].append({"name": name, "passed": False, "error": "Timed out"})
        summary["passed"] = len(summary["checks"]) == len(cases) and all(check["passed"] for check in summary["checks"])
        print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
        (REPORTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
