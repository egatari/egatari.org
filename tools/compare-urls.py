#!/usr/bin/env python3
"""Prove that the assembled egatari.org site (NEW) serves every URL that the
egatari-spec Jekyll build alone (OLD) serves, with identical bytes -- except
that the spec's own front page moves from "/" (index.html) to "/spec/"
(spec/index.html) -- and that everything else in NEW is exactly the overlay
(this repository's src/ directory).

The overlay may ADD paths (assets/, gallery/, robots.txt, ...) but may never
take a path the spec build serves. The one exception is index.html: the
spec's front page has moved to /spec/, and the overlay's index.html (the
landing page) takes "/".

Usage:
    compare-urls.py --check-overlay <old_site_dir> <overlay_dir>
        Before assembling: fail if the overlay would overwrite any path of
        the spec build (other than index.html), or the moved front page.
    compare-urls.py <old_site_dir> <new_site_dir> <overlay_dir>
        After assembling: the full proof.

Exit status:
    0  OK.
    1  usage / input error (bad arguments, missing directories, empty OLD).
    2  one or more collisions, content or coverage differences found.
"""
from __future__ import annotations

import sys
from pathlib import Path

# The overlay must provide these (the landing page and the temporary robots.txt).
REQUIRED_OVERLAY = {"index.html", "robots.txt"}
# Overlay paths allowed to coincide with an OLD path, because the OLD file
# moves elsewhere (see expected_new_path).
OVERLAY_MAY_REPLACE = {"index.html"}


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


def need_dir(path: Path, what: str) -> bool:
    if not path.is_dir():
        print(f"error: {what} not found: {path}", file=sys.stderr)
        return False
    return True


def overlay_collisions(old_files: list[str], overlay_files: list[str]) -> list[str]:
    """Overlay paths that would overwrite a path the spec build serves."""
    taken = {expected_new_path(rel) for rel in old_files}
    taken |= set(old_files) - OVERLAY_MAY_REPLACE
    return [
        f"OVERLAY COLLIDES with the spec build: '{rel}'"
        for rel in overlay_files
        if rel in taken
    ]


def check_overlay(old_root: Path, overlay_root: Path) -> int:
    old_files = list_files(old_root)
    overlay_files = list_files(overlay_root)
    if not old_files:
        print(f"error: old site dir is empty: {old_root}", file=sys.stderr)
        return 1
    problems = overlay_collisions(old_files, overlay_files)
    for rel in sorted(REQUIRED_OVERLAY - set(overlay_files)):
        problems.append(f"MISSING required overlay file: '{rel}'")
    print(f"spec build: {len(old_files)} file(s); overlay: {len(overlay_files)} file(s)")
    if problems:
        print(f"\nFOUND {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 2
    print("OK: the overlay only adds paths (and takes / from the moved spec front page).")
    return 0


def full_proof(old_root: Path, new_root: Path, overlay_root: Path) -> int:
    old_files = list_files(old_root)
    new_files = set(list_files(new_root))
    overlay_files = list_files(overlay_root)

    if not old_files:
        print(f"error: old site dir is empty, nothing to compare: {old_root}", file=sys.stderr)
        return 1

    problems: list[str] = overlay_collisions(old_files, overlay_files)
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

    added = 0
    for rel in overlay_files:
        new_file = new_root / rel
        if not new_file.is_file():
            problems.append(f"MISSING overlay file in new build: '{rel}'")
            continue
        if new_file.read_bytes() != (overlay_root / rel).read_bytes():
            problems.append(f"OVERLAY FILE DIFFERS in new build: '{rel}'")
        added += 1

    extra = sorted(new_files - expected_paths - set(overlay_files))
    for rel in extra:
        problems.append(
            f"UNEXPECTED FILE in new build (not from the spec build, not from the overlay): '{rel}'"
        )

    for rel in sorted(REQUIRED_OVERLAY - set(overlay_files)):
        problems.append(f"MISSING required overlay file: '{rel}'")

    print(f"old build: {len(old_files)} file(s) under {old_root}")
    print(f"new build: {len(new_files)} file(s) under {new_root}")
    print(f"overlay:   {len(overlay_files)} file(s) under {overlay_root}")
    print(f"checked:   {checked} old URL(s) mapped onto new build")
    print(f"added:     {added} overlay path(s)")
    for rel in overlay_files:
        print(f"  + {rel}")

    if problems:
        print(f"\nFOUND {len(problems)} difference(s):")
        for p in problems:
            print(f"  - {p}")
        return 2

    print(
        "\nOK: every URL served by the spec build alone is served byte-identical "
        "by the assembled build, with only / moved to /spec/; every other file "
        "is an overlay addition that overwrites nothing."
    )
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) == 3 and args[0] == "--check-overlay":
        old_root, overlay_root = Path(args[1]).resolve(), Path(args[2]).resolve()
        if not (need_dir(old_root, "old site dir") and need_dir(overlay_root, "overlay dir")):
            return 1
        return check_overlay(old_root, overlay_root)
    if len(args) == 3:
        old_root, new_root, overlay_root = (Path(a).resolve() for a in args)
        if not (
            need_dir(old_root, "old site dir")
            and need_dir(new_root, "new site dir")
            and need_dir(overlay_root, "overlay dir")
        ):
            return 1
        return full_proof(old_root, new_root, overlay_root)
    print(
        f"usage: {argv[0]} --check-overlay <old_site_dir> <overlay_dir>\n"
        f"       {argv[0]} <old_site_dir> <new_site_dir> <overlay_dir>",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
