#!/usr/bin/env python3
"""Subset the site fonts to the glyphs the pages use, as WOFF2.

    uv run --with fonttools --with brotli python3 tools/subset-fonts.py <font_dir>

<font_dir> holds the OFL source fonts from github.com/google/fonts:
  ShipporiMinchoB1-ExtraBold.ttf   (ofl/shipporiminchob1)
  BIZUDPGothic-Regular.ttf         (ofl/bizudpgothic)
  BIZUDPGothic-Bold.ttf            (ofl/bizudpgothic)

The Mincho (display) font is cut to the text of headings and the other
display elements (see DISPLAY_*); the Gothic (body) fonts to all text of
src/**/*.html. Printable ASCII is always kept. Re-run after changing copy,
and commit the woff2 files under src/assets/fonts/.
"""
from __future__ import annotations

import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = SRC / "assets" / "fonts"

DISPLAY_TAGS = {"h1", "h2"}
DISPLAY_CLASSES = {"num", "area-name", "headline", "page-title"}
SKIP_TAGS = {"script", "style", "code", "pre"}
ASCII = "".join(chr(c) for c in range(0x20, 0x7F))
EXTRA = "→…・、。「」（）？！ー"

FONTS = [
    ("ShipporiMinchoB1-ExtraBold.ttf", "shippori-mincho-b1-800.woff2", "display"),
    ("BIZUDPGothic-Regular.ttf", "biz-udpgothic-400.woff2", "body"),
    ("BIZUDPGothic-Bold.ttf", "biz-udpgothic-700.woff2", "body"),
]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool]] = []  # (tag, display, skip)
        self.body: set[str] = set()
        self.display: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            for k, v in attrs:
                if k in ("alt", "aria-label", "title") and v:
                    self.body.update(v)
            return
        classes = set((dict(attrs).get("class") or "").split())
        parent_display = self.stack[-1][1] if self.stack else False
        parent_skip = self.stack[-1][2] if self.stack else False
        display = parent_display or tag in DISPLAY_TAGS or bool(classes & DISPLAY_CLASSES)
        skip = parent_skip or tag in SKIP_TAGS
        for k, v in attrs:
            if k in ("aria-label", "title") and v:
                self.body.update(v)
        self.stack.append((tag, display, skip))

    def handle_endtag(self, tag):
        while self.stack:
            t, _, _ = self.stack.pop()
            if t == tag:
                break

    def handle_data(self, data):
        if not self.stack:
            return
        _, display, skip = self.stack[-1]
        if skip:
            return
        self.body.update(data)
        if display:
            self.display.update(data)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    font_dir = Path(argv[1])
    c = Collector()
    pages = sorted(SRC.rglob("*.html"))
    for page in pages:
        c.feed(page.read_text(encoding="utf-8"))
        c.close()
        c.reset()
        c.stack.clear()
    texts = {
        "display": "".join(sorted((c.display | set(ASCII) | set(EXTRA)) - {"\n", "\r", "\t"})),
        "body": "".join(sorted((c.body | set(ASCII) | set(EXTRA)) - {"\n", "\r", "\t"})),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for src_name, out_name, kind in FONTS:
        src = font_dir / src_name
        if not src.is_file():
            print(f"error: missing {src}", file=sys.stderr)
            return 1
        out = OUT / out_name
        subprocess.run(
            [
                sys.executable, "-m", "fontTools.subset", str(src),
                f"--text={texts[kind]}",
                "--flavor=woff2",
                "--layout-features=*",
                "--no-hinting",
                "--desubroutinize",
                f"--output-file={out}",
            ],
            check=True,
        )
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size:,} bytes, {len(texts[kind])} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
