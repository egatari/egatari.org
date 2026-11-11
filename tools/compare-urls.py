#!/usr/bin/env python3
"""Prove that the assembled egatari.org site (NEW) serves every URL that the
egatari-spec Jekyll build alone (OLD) serves, with identical bytes -- except
that the spec's own front page moves from "/" (index.html) to "/spec/"
(spec/index.html). NEW is allowed exactly two files that OLD never had: the
placeholder landing page (index.html) and robots.txt.

Usage:
    compare-urls.py <old_site_dir> <new_site_dir>

Exit status:
    0  every file in OLD is present in NEW at its expected path with
       identical bytes, and NEW has no files beyond the expected mapping
       plus the two allowed extras.
    1  usage / input error (bad arguments, missing directories, empty OLD).
    2  one or more content or coverage differences found.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Files the NEW build is allowed to have that OLD (the spec built alone)
# never produces: the placeholder landing page and the temporary robots.txt.
ALLOWED_NEW_ONLY = {"index.html", "robots.txt"}


def list_files(root: Path) -> list[str]:
    """All regular files under root, as POSIX-style paths relative to root."""
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


def expected_new_path(old_rel: str) -> str:
    """Where a file from the OLD (spec-only) build must appear in NEW."""
    if old_rel == "index.html":
        # The spec's own front page moves from / to /spec/.
        return "spec/index.html"
    return old_rel


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <old_site_dir> <new_site_dir>", file=sys.stderr)
        return 1

    old_root = Path(argv[1]).resolve()
    new_root = Path(argv[2]).resolve()

    if not old_root.is_dir():
        print(f"error: old site dir not found: {old_root}", file=sys.stderr)
        return 1
    if not new_root.is_dir():
        print(f"error: new site dir not found: {new_root}", file=sys.stderr)
        return 1

    old_files = list_files(old_root)
    new_files = set(list_files(new_root))

    if not old_files:
        print(f"error: old site dir is empty, nothing to compare: {old_root}", file=sys.stderr)
        return 1

    problems: list[str] = []
    expected_paths: set[str] = set()
    checked = 0

    for rel in old_files:
        target = expected_new_path(rel)
        expected_paths.add(target)
        checked += 1

        new_file = new_root / target
        if not new_file.is_file():
            problems.append(f"MISSING in new build: '{rel}' -> expected '{target}'")
            continue

        old_bytes = (old_root / rel).read_bytes()
        new_bytes = new_file.read_bytes()
        if old_bytes != new_bytes:
            problems.append(
                f"CONTENT DIFFERS: '{rel}' -> '{target}' "
                f"({len(old_bytes)} bytes old, {len(new_bytes)} bytes new)"
            )

    extra = sorted(new_files - expected_paths - ALLOWED_NEW_ONLY)
    for rel in extra:
        problems.append(
            f"UNEXPECTED FILE in new build (not in old, not an allowed addition): '{rel}'"
        )

    for rel in sorted(ALLOWED_NEW_ONLY):
        if rel not in new_files:
            problems.append(f"MISSING expected addition in new build: '{rel}'")

    print(f"old build: {len(old_files)} file(s) under {old_root}")
    print(f"new build: {len(new_files)} file(s) under {new_root}")
    print(f"checked:   {checked} old URL(s) mapped onto new build")
    print(f"allowed additions present: {sorted(ALLOWED_NEW_ONLY & new_files)}")

    if problems:
        print(f"\nFOUND {len(problems)} difference(s):")
        for p in problems:
            print(f"  - {p}")
        return 2

    print(
        "\nOK: every URL served by the spec build alone is served byte-identical "
        "by the assembled build, with only / moved to /spec/."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
