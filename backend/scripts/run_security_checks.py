"""Run baseline security checks (Bandit + Safety) for the backend."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"
REQUIREMENTS = ROOT / "requirements.txt"


def run(cmd: list[str], cwd: Path | None = None):
    print(f"\n=== Running: {' '.join(cmd)} ===")
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_dev_dependencies():
    if REQUIREMENTS_DEV.exists():
        run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_DEV)])


def main():
    ensure_dev_dependencies()
    run([sys.executable, "-m", "bandit", "-r", "app", "-ll", "-iii"])
    if REQUIREMENTS.exists():
        run([sys.executable, "-m", "safety", "check", "--full-report", "-r", str(REQUIREMENTS)])


if __name__ == "__main__":
    main()
