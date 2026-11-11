# egatari.org

The source of <https://egatari.org/>: the landing page, the gallery of example lessons, and the published Egatari specification.

Status: being set up (2026-11-11). The site is still served from the [egatari-spec](https://github.com/egatari/egatari-spec) repository. This repository takes over at Egatari 1.0 (v0.7).

## How the site is built (plan)

- `/` is the landing page and `/gallery/` the example lessons. Their source lives here.
- The specification is built from a pinned tag of `egatari/egatari-spec` (for example `wd-2026-11-10`), and every URL it has today is kept: `/egatari-1.0`, `/egatari-player-1.0`, `/extensions/…`, `/schema/…`, `/fixtures/…`, `/logo/…`. `https://egatari.org/schema/…` identifiers appear inside lesson files and must never move.
- The spec's own front page moves from `/` to `/spec/`.
- After the switch, egatari-spec no longer publishes Pages. It stays the source of the specification text.

## License

Site content CC BY 4.0, code MIT (to be confirmed with the first content commit).
