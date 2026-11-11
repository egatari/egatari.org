#!/usr/bin/env python3
"""The sample lesson files that /gallery/play/ plays, pinned by src/gallery/samples.lock.json.

    python3 tools/gallery_files.py lock            # (re)write the lock from lessons.json's release; review the diff, commit it
    python3 tools/gallery_files.py fetch <site>    # build: download, verify, write <site>/gallery/files/<id>.ega.bin
    ... [--from <dir>]                             # read the release files from a folder instead of downloading

Standard library only. No lesson file is committed here: the build downloads the
play-only files of the pinned egatari/examples release and refuses any byte that
differs from the lock (SHA256SUMS itself, then each file's size and SHA-256, which
must also match its SHA256SUMS line). The files are written as <id>.ega.bin, which
GitHub Pages serves as application/octet-stream: opening one directly downloads it
and it never renders on egatari.org (spec §10.1). The player
(src/gallery/play/site-play.js, from Egatari Studio) checks size and SHA-256 again
before playing.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "src" / "gallery" / "lessons.json"
LOCK = ROOT / "src" / "gallery" / "samples.lock.json"
REPO = "egatari/examples"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
MAX = 25 * 1024 * 1024


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get(tag: str, name: str, src: Path | None) -> bytes:
    if src:
        return (src / name).read_bytes()
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310 (fixed https host)
        data = r.read(MAX + 1)
    if len(data) > MAX:
        raise SystemExit(f"error: {name}: larger than {MAX} bytes")
    return data


def sums_of(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-f]{64}) [ *]?(\S+)$", line.strip())
        if m:
            out[m.group(2)] = m.group(1)
    return out


def write_lock(src: Path | None) -> int:
    data = json.loads(LESSONS.read_text(encoding="utf-8"))
    tag = data["release"]
    sums_bytes = get(tag, "SHA256SUMS", src)
    sums = sums_of(sums_bytes.decode("utf-8"))
    lessons = []
    for lesson in data["lessons"]:
        lid, file = lesson["id"], lesson["play"]
        if not ID_RE.match(lid):
            raise SystemExit(f"error: id {lid!r} is not [a-z0-9-]")
        b = get(tag, file, src)
        if sums.get(file) != sha(b):
            raise SystemExit(f"error: {file} differs from SHA256SUMS")
        lessons.append({"id": lid, "file": file, "sha256": sha(b), "size": len(b), "title": lesson["title"], "lang": lesson.get("lang", "ja")})
    lock = {"repo": REPO, "tag": tag, "sums": sha(sums_bytes), "lessons": lessons}
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {LOCK.relative_to(ROOT)} ({tag}, {len(lessons)} lessons)")
    return 0


def fetch(site: Path, src: Path | None) -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    data = json.loads(LESSONS.read_text(encoding="utf-8"))
    if lock["tag"] != data["release"]:
        raise SystemExit(f"error: the lock pins {lock['tag']} but lessons.json says {data['release']}: run `python3 tools/gallery_files.py lock`")
    pinned = {x["id"] for x in lock["lessons"]}
    missing = [x["id"] for x in data["lessons"] if x["id"] not in pinned]
    if missing:
        raise SystemExit(f"error: not in the lock: {', '.join(missing)}")
    sums_bytes = get(lock["tag"], "SHA256SUMS", src)
    if sha(sums_bytes) != lock["sums"]:
        raise SystemExit(f"error: SHA256SUMS of {lock['tag']} differs from the lock")
    sums = sums_of(sums_bytes.decode("utf-8"))
    out = site / "gallery" / "files"
    out.mkdir(parents=True, exist_ok=True)
    for x in lock["lessons"]:
        if not ID_RE.match(x["id"]) or not HEX_RE.match(x["sha256"]) or not 0 < x["size"] <= MAX:
            raise SystemExit(f"error: lock entry {x.get('id')!r} is malformed")
        if sums.get(x["file"]) != x["sha256"]:
            raise SystemExit(f"error: {x['file']}: the lock and SHA256SUMS disagree")
        b = get(lock["tag"], x["file"], src)
        if len(b) != x["size"] or sha(b) != x["sha256"]:
            raise SystemExit(f"error: {x['file']}: the bytes differ from the lock")
        (out / f"{x['id']}.ega.bin").write_bytes(b)
    print(f"wrote {len(lock['lessons'])} files to {out} ({lock['tag']})")
    return 0


def main(argv: list[str]) -> int:
    src = None
    if "--from" in argv:
        i = argv.index("--from")
        src = Path(argv[i + 1])
        del argv[i:i + 2]
    if argv[:1] == ["lock"] and len(argv) == 1:
        return write_lock(src)
    if argv[:1] == ["fetch"] and len(argv) == 2:
        return fetch(Path(argv[1]), src)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
