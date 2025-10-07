#!/usr/bin/env python3

"""Detect version changes in pyproject.toml and emit GitHub outputs."""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

PATTERN = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def read_version_from_text(text: str) -> str | None:
    if not text:
        return None
    match = PATTERN.search(text)
    return match.group(1) if match else None


def read_current_version(pyproject_path: pathlib.Path) -> str:
    try:
        current_text = pyproject_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - fail fast in CI
        raise SystemExit("pyproject.toml not found") from exc

    version = read_version_from_text(current_text)
    if not version:
        raise SystemExit("Version not found in pyproject.toml")
    return version


def read_previous_version(pyproject_path: pathlib.Path) -> str | None:
    rel_path = pyproject_path.as_posix()
    try:
        previous_text = subprocess.check_output(  # noqa: S603, S607
            ["git", "show", f"HEAD^:{rel_path}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    return read_version_from_text(previous_text)


def main() -> None:
    pyproject_path = pathlib.Path("pyproject.toml")

    current_version = read_current_version(pyproject_path)
    previous_version = read_previous_version(pyproject_path) or ""

    if not previous_version:
        print("Previous version not found; assuming release required.")

    should_publish = current_version != previous_version

    if should_publish:
        prev_label = previous_version or "none"
        print(f"Detected version change: {prev_label} -> {current_version}")
    else:
        print("No version change detected; skipping release.")

    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise SystemExit("GITHUB_OUTPUT environment variable is required")

    with open(output_path, "a", encoding="utf-8") as file:
        file.write(f"current_version={current_version}\n")
        file.write(f"previous_version={previous_version}\n")
        file.write(f"should_publish={'true' if should_publish else 'false'}\n")


if __name__ == "__main__":
    main()

