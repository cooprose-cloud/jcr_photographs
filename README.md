# Photos at an Exposition

Turn a folder of photographs into a polished static website plus a standalone
slideshow viewer — no web server, no database, no JavaScript framework.
Drop photos into folders, run the scripts, and open the result in any browser.

The pipeline is built around plain files: photos on disk, a single
`photo_config.json` manifest, and generated HTML. Everything is editable by
hand, version-controllable, and portable — copy the `website/` folder to a
USB stick, a thumb drive, or any web host and it just works.

> **Full guide:** this README is the quick orientation. For the complete
> walkthrough — including a start-to-finish worked example, every option, and
> troubleshooting — see **[USER_MANUAL.md](USER_MANUAL.md)**.

## How it fits together

```
   ┌──────────────────────┐
   │  user_files/         │   Your photos, grouped into folders
   │   ├─ Colonnade/      │   (one folder per gallery), plus optional
   │   ├─ Gardens/        │   captions via notes.txt, spreadsheets,
   │   └─ Kings_Mountain/ │   or .md sidecar files.
   └──────────┬───────────┘
              │   Build the config two ways:
              │     • generate_photo_config.py  — scan folders (wizard or --form)
              │     • csv_to_config.py          — from site_settings.csv + photos.csv
              ▼
   ┌──────────────────────┐
   │  photo_config.json   │   Single source of truth: gallery structure,
   │                      │   photo order, captions, slideshow picks.
   └──────────┬───────────┘   Check it with validate_photo_config.py.
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
   photos_       build_slideshow.py
   exposition.py
       │             │
       ▼             ▼
   ┌──────────────────────┐
   │  website/            │   Static site with home page, gallery
   │   ├─ index.html      │   indexes, per-photo pages with zoom,
   │   ├─ <gallery>.html  │   AND a single-file slideshow viewer.
   │   ├─ slideshow.html  │
   │   ├─ photos/         │
   │   ├─ thumbnails/     │
   │   ├─ css/            │
   │   └─ js/             │
   └──────────────────────┘
```

The scripts are independent. You can run `photos_exposition.py` and
`build_slideshow.py` against the same `photo_config.json`, or use just one,
or run them dozens of times as you tweak captions and re-order photos.

## Quick start

```bash
# 1. Lay out your photos: one folder per gallery under user_files/
mkdir -p project_gallery/user_files/Gardens
cp ~/Pictures/garden_*.jpg project_gallery/user_files/Gardens/

# 2. Build a config — either scan your folders…
python3 scripts/generate_photo_config.py --user-dir project_gallery/user_files --form
#    …or drive it from spreadsheets instead:
#    python3 scripts/csv_to_config.py --sample   # writes starter CSVs to edit
#    python3 scripts/csv_to_config.py            # builds the config from them

# 3. (Optional but recommended) Check the config before building
python3 scripts/validate_photo_config.py --config project_gallery/user_files/photo_config.json

# 4. Generate the website
python3 scripts/photos_exposition.py project_gallery/user_files/photo_config.json --clean

# 5. Add the standalone slideshow viewer
python3 scripts/build_slideshow.py build \
    --config project_gallery/user_files/photo_config.json

# 6. Open the result
open project_gallery/website/index.html
```

> **On Windows:** use `python` (or `py`) instead of `python3`, `pip` instead
> of `pip3`, and `start website\index.html` (or just double-click it) instead
> of `open`. Everything else is identical.

## Project layout

```
project_gallery/
├── user_files/                   # Source photos and config — you own these
│   ├── photo_config.json         # the manifest (generated)
│   ├── site_settings.csv         # site-wide settings (CSV workflow)
│   ├── photos.csv                # one row per photo (CSV workflow)
│   ├── Colonnade/
│   │   ├── notes.txt             # optional captions: filename | text
│   │   ├── Bedroom.md            # optional "Read More" sidecar
│   │   └── *.jpg
│   ├── Gardens/
│   │   └── *.jpg
│   └── Kings_Mountain/
│       └── *.jpg
└── website/                      # Generated output — safe to delete and rebuild
    ├── index.html
    ├── <gallery_id>.html
    ├── <gallery_id>_<n>.html
    ├── slideshow.html
    ├── photos/<gallery_id>/...
    ├── thumbnails/<gallery_id>/...
    ├── css/style.css
    └── js/slideshow.js
```

The `scripts/` directory holds the Python tools; put them anywhere convenient.
The `website/` folder can be re-generated from scratch at any time — nothing
in it is precious.

## The scripts

**Build the config (pick one route):**

- **`generate_photo_config.py`** — Builds `photo_config.json` by scanning your
  `user_files/` directory. *Wizard* mode (default) asks for site title,
  slideshow picks, and thumbnail size; *Form* mode (`--form`) is a
  non-interactive scan that writes a pre-filled config with blank captions to
  edit afterward. Looks for an optional `notes.txt` (or `captions.txt` /
  `notes.csv`) in each gallery folder, one line per `filename.jpg | Caption`.
- **`csv_to_config.py`** — Builds the same `photo_config.json` from two
  spreadsheets, `site_settings.csv` and `photos.csv`. Run with `--sample` to
  write starter CSVs. The comfortable way to maintain captions and ordering.
- **`config_to_csv.py`** — The reverse: exports an existing config back into
  those two CSVs, so you can switch to the spreadsheet workflow or get your
  sheets back in sync after hand-editing the JSON.

**Check it:**

- **`validate_photo_config.py`** — Validates the config in two tiers: JSON
  syntax, then content (required fields, duplicate/missing photos, captions or
  slideshow picks that reference photos that don't exist, and that source
  folders and files exist on disk). Catches mistakes before you build.

**Build the output:**

- **`photos_exposition.py`** — Reads `photo_config.json` and builds the full
  static website: home page with rotating slideshow header, per-gallery
  thumbnail grids, and a dedicated page for every photo with 1x → 2x → 3x
  click-to-zoom and prev/next navigation. Copies photos into `website/photos/`
  and generates thumbnails (default 300×300, configurable) in
  `website/thumbnails/`. Use `--clean` when adding, removing, or renaming
  galleries.
- **`build_slideshow.py`** — Produces a single-file `slideshow.html` viewer
  that lives next to the rest of the site: sidebar gallery list, thumbnail
  strip, autoplay with adjustable speed, fullscreen mode, keyboard navigation,
  and a caption overlay. Self-contained — all CSS and JavaScript embedded — so
  it works offline and survives being copied anywhere alongside the photos.

## Requirements

- **Python 3.9 or later**
- **Pillow** (PIL) — for thumbnail generation. Install with
  `pip3 install Pillow` (`pip install Pillow` on Windows).
- **Optional: the `markdown` package** — only for rich formatting (lists,
  headings, links) in "Read More" pages. Plain paragraphs, **bold**, and
  *italic* work without it.
- A modern web browser to view the output (Chrome, Firefox, Safari, Edge).
  No web server required — everything runs from `file://` URLs.

## Workflow tips

A typical editing loop:

1. Add new photos to a folder under `user_files/`.
2. Refresh the config — re-run `generate_photo_config.py --form`, or edit
   `photos.csv` and re-run `csv_to_config.py`.
3. Add captions and reorder photos (in `photos.csv`, or directly in
   `photo_config.json`). For longer write-ups, drop a `.md` sidecar next to a
   photo to create its "Read More" page.
4. Validate, then rebuild: `validate_photo_config.py`, then
   `photos_exposition.py --clean` and `build_slideshow.py`.
5. Hard-refresh `website/index.html` in your browser (Cmd-Shift-R /
   Ctrl-Shift-R) to beat stale caches.

Captions support inline `<br>` for line breaks.

## License

Released under the MIT License. See the [LICENSE](LICENSE) file for the full
text. In short: use it, modify it, redistribute it — just keep the copyright
notice with the code.

## Status

Active personal project. Issues and PRs welcome but cadence is irregular.
