"""Basic documentation checks to keep Regia docs up-to-date.

This script intentionally stays lightweight; CI calls it on every PR.
"""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REQUIRED_DOCS = [
    "README.md",
    "admin-guide.md",
    "developer-guide.md",
    "user-guide.md",
    "troubleshooting.md",
    "doc-style.md",
]

MANDATORY_HEADINGS = {
    "README.md": "# Regia",
    "admin-guide.md": "# Admin & Operations Guide",
    "developer-guide.md": "# Developer Handbook",
    "user-guide.md": "# User Journey Guide",
    "troubleshooting.md": "# Logging & Troubleshooting",
    "doc-style.md": "# Documentation Style Guide",
}

README_DOCS_LINK = "docs/README.md"


def fail(message: str) -> None:
    print(f"[docs] {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not DOCS_DIR.exists():
        fail("docs directory missing")

    for relative in REQUIRED_DOCS:
        path = DOCS_DIR / relative
        if not path.exists():
            fail(f"required doc missing: {relative}")
        text = path.read_text(encoding="utf-8")
        heading = MANDATORY_HEADINGS.get(relative)
        if heading and heading not in text.splitlines()[0]:
            fail(f"{relative} missing expected heading '{heading}'")

    readme_path = REPO_ROOT / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")
    if README_DOCS_LINK not in readme_text:
        fail("Root README must link to docs/README.md")

    print("Documentation checks passed ✔")


if __name__ == "__main__":
    main()
