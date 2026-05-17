# Photos at an Exposition

Turn a folder of photographs into a polished static website plus a standalone
slideshow viewer — no web server, no database, no JavaScript framework.
Drop photos into folders, run three scripts, and open the result in any browser.

The pipeline is built around plain files: photos on disk, a single
`photo_config.json` manifest, and generated HTML. Everything is editable by
hand, version-controllable, and portable — copy the `website/` folder to a
USB stick, a thumb drive, or any web host and it just works.

## How it fits together

```
   ┌──────────────────────┐
   │  user_files/         │   Your photos, grouped into folders.
   │   ├─ Colonnade/      │   One folder per gallery. Optional
   │   ├─ Gardens/        │   notes.txt files for captions.
   │   └─ Kings_Mountain/ │
   └──────────┬───────────┘
              │
              │  generate_photo_config.py
              ▼
   ┌──────────────────────┐
   │  photo_config.json   │   Single source of truth: gallery
   │                      │   structure, photo order, captions,
   └──────────┬───────────┘   site title, slideshow picks.
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
   photos_       build_slideshow.py
   exposition.py
       │             │
       ▼             ▼
   ┌──────────────────────┐
   │  website/            │   Static site with home page,
   │   ├─ index.html      │   gallery indexes, per-photo pages
   │   ├─ <gallery>.html  │   with zoom, AND a single-file
   │   ├─ slideshow.html  │   slideshow viewer.
   │   ├─ photos/         │
   │   ├─ thumbnails/     │
   │   ├─ css/            │
   │   └─ js/             │
   └──────────────────────┘
```

The three scripts are independent. You can run `photos_exposition.py` and
`build_slideshow.py` against the same `photo_config.json`, or use just one,
or run them dozens of times as you tweak captions and re-order photos.

## Quick start

```bash
# 1. Lay out your photos
mkdir -p project_gallery/user_files/Gardens
cp ~/Pictures/garden_*.jpg project_gallery/user_files/Gardens/

# 2. Build a config (--form mode skips prompts; use without --form for a wizard)
python3 scripts/generate_photo_config.py --user-dir project_gallery/user_files --form

# 3. Generate the website
python3 scripts/photos_exposition.py project_gallery/user_files/photo_config.json

# 4. Add the standalone slideshow viewer
python3 scripts/build_slideshow.py build \
    --config project_gallery/user_files/photo_config.json

# 5. Open the result
open project_gallery/website/index.html
```

## Project layout

```
project_gallery/
├── user_files/                   # Source photos and config — you own these
│   ├── photo_config.json
│   ├── Colonnade/
│   │   ├── notes.txt             # Optional captions: filename | text
│   │   └── *.jpg
│   ├── Gardens/
│   │   └── *.jpg
│   └── Kings_Mountain/
│       ├── notes.txt
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

The `scripts/` directory holds the three Python tools; put them anywhere
convenient. The `website/` folder can be re-generated from scratch at any
time — nothing in it is precious.

## The three scripts

**`generate_photo_config.py`** — Builds `photo_config.json` by scanning your
`user_files/` directory. Two modes:

- *Wizard* (default): asks for site title, picks one slideshow photo per
  gallery, lets you choose thumbnail size. Run it once when you start a
  project; re-run it any time you want to rebuild the config from scratch.
- *Form* (`--form`): non-interactive scan that produces a pre-filled config
  with sensible defaults and blank notes for every photo. Edit the JSON by
  hand afterward.

Both modes look for an optional `notes.txt` (or `captions.txt` / `notes.csv`)
inside each gallery folder. Each line is `filename.jpg | Caption text here`.

**`photos_exposition.py`** — Reads `photo_config.json` and builds the full
static website: home page with rotating slideshow header, per-gallery
thumbnail grids, and a dedicated page for every photo with 1x → 2x → 3x
click-to-zoom and prev/next navigation. Copies photos into `website/photos/`
and generates 300×300 thumbnails in `website/thumbnails/`.

**`build_slideshow.py`** — Produces a single-file `slideshow.html` viewer
that lives next to the rest of the site. Has a sidebar gallery list, a
thumbnail strip, autoplay with adjustable speed, fullscreen mode, keyboard
navigation, and an overlay that shows the photo's caption. Self-contained:
all CSS and JavaScript embedded, so it works offline and survives being
copied anywhere alongside the photo folders.

## Requirements

- **Python 3.9 or later**
- **Pillow** (PIL) — for thumbnail generation. Install with `pip3 install Pillow`.
- A modern web browser to view the output (Chrome, Firefox, Safari, Edge).
  No web server required — everything runs from `file://` URLs.

## Workflow tips

Most of the time you'll want to follow this loop:

1. Add new photos to a folder under `user_files/`
2. Re-run `generate_photo_config.py --form` to refresh the JSON (it
   preserves the directory layout but starts notes empty for new photos)
3. Hand-edit `photo_config.json` to add captions and reorder photos
4. Re-run `photos_exposition.py` and `build_slideshow.py`
5. Refresh `website/index.html` in your browser (a hard refresh —
   Cmd-Shift-R / Ctrl-Shift-R — beats stale caches)

For day-to-day caption tweaks you can skip the regenerate step and edit
`photo_config.json` directly. Captions support inline `<br>` for line
breaks.

## License

Released under the MIT License. See the [LICENSE](LICENSE) file for the
full text. In short: use it, modify it, redistribute it — just keep the
copyright notice with the code.

## Status

Active personal project. Issues and PRs welcome but cadence is irregular.
