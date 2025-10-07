#!/usr/bin/env python3

"""Update project version and workflow metadata for releases."""

from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PYPROJECT_PATH = ROOT / "pyproject.toml"
WORKFLOW_PATH = ROOT / ".github/workflows/publish_node.yml"

PYPROJECT_PATTERN = re.compile(r'(?m)^(\s*version\s*=\s*)["\'][^"\']+["\']')
DESC_PATTERN = re.compile(
    r'(description:\s*Release version\s*\()(?:current:[^)]*|e\.g\.[^)]*)(\))'
)


def update_pyproject(version: str) -> None:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    new_text, count = PYPROJECT_PATTERN.subn(rf"\1\"{version}\"", text, count=1)
    if count != 1:
        raise SystemExit("Failed to update version in pyproject.toml")
    PYPROJECT_PATH.write_text(new_text, encoding="utf-8")


def update_workflow_description(version: str) -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    new_text, count = DESC_PATTERN.subn(
        rf"\1\"current: {version}\"\2", text, count=1
    )
    if count == 0:
        placeholder = "description: Release version (e.g."
        if placeholder in text:
            new_text = text.replace(
                "description: \"Release version (e.g. 0.0.4)\"",
                f"description: \"Release version (current: {version})\"",
                1,
            )
        else:
            raise SystemExit("Failed to update description in workflow file")
    WORKFLOW_PATH.write_text(new_text, encoding="utf-8")


def normalize_version(value: str | None) -> str:
    if not value:
        raise SystemExit("RELEASE_VERSION environment variable not set")

    version = value.lstrip("vV")
    if not version:
        raise SystemExit("Normalized version is empty")
    if not re.match(r"^[0-9]+(\.[0-9]+)*$", version):
        raise SystemExit(
            "RELEASE_VERSION must be in numeric dotted format (e.g. 0.0.4)"
        )
    return version


def main() -> None:
    version = normalize_version(os.environ.get("RELEASE_VERSION"))
    update_pyproject(version)
    update_workflow_description(version)


if __name__ == "__main__":
    main()

