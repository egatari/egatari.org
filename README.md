# egatari.org

The source of <https://egatari.org/>: the landing page, the gallery of example lessons, and the published Egatari specification.

Status: being set up (2026-11-11). The site is still served from the [egatari-spec](https://github.com/egatari/egatari-spec) repository. This repository takes over at Egatari 1.0 (v0.7).

## How the site is built (plan)

- `/` is the landing page, `/en/` its English version, and `/gallery/` the example lessons (in Japanese; some lessons are in English). Their source lives here.
- The specification is built from a pinned tag of `egatari/egatari-spec` (for example `wd-2026-11-10`), and every URL it has today is kept: `/egatari-1.0`, `/egatari-player-1.0`, `/extensions/…`, `/schema/…`, `/fixtures/…`, `/logo/…`. `https://egatari.org/schema/…` identifiers appear inside lesson files and must never move.
- The spec's own front page moves from `/` to `/spec/`.
- After the switch, egatari-spec no longer publishes Pages. It stays the source of the specification text.
- `src/` is overlaid on the spec build. It may add paths but never overwrite one the spec build serves (except `index.html`, whose spec page has moved to `/spec/`); `tools/compare-urls.py` checks this before and after assembling, and proves every old URL is byte-identical.
- The gallery is generated: edit `src/gallery/lessons.json`, run `python3 tools/build-gallery.py`, and commit both. Lesson files are not committed here: downloads link to the egatari/examples release, and 「再生」 opens `/gallery/play/?id=<id>`. The site build fetches the play-only files of the release pinned in `src/gallery/samples.lock.json`, checks every byte against it, and writes them as `/gallery/files/<id>.ega.bin` (served as `application/octet-stream`, so they never render on egatari.org). After changing `release` in lessons.json, run `python3 tools/gallery_files.py lock` and commit the lock. The player in `src/gallery/play/` (`site-play.js`, `site-play.css`) is Egatari Studio's site player, vendored as built; `BUILD.json` names the Studio commit and the SHA-256 of each file, and holds the page policy that `index.html` carries in its `<meta>`.
- Fonts are self-hosted subsets (OFL): after changing copy, run `uv run --with fonttools --with brotli python3 tools/subset-fonts.py <dir with the source TTFs>`. The site makes no third-party requests.

## License

Site content CC BY 4.0, code MIT (to be confirmed with the first content commit).
