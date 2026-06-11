# Photos at an Exposition — User Manual

A guide to the photo-gallery website system: how to set it up from scratch,
what each program does, every option it accepts, and how the pieces fit
together.

The system turns folders of photographs into a complete, self-contained
website you can open in any browser or upload to any host. You never write
HTML — you organize your photos into folders, describe them in a simple form
(a pair of spreadsheets or a scanned JSON file), and the builder generates
everything: a home page with a slideshow, a page per gallery, a page per
photo, and optional "Read More" pages for the photos you want to write about.

> **New here?** You've received a zip of the programs. Start with
> [section 2, Requirements and first-time setup](#2-requirements-and-first-time-setup) —
> it walks you from an empty folder to a finished site.

> **On Windows?** The commands in this manual are shown in macOS/Linux form.
> On Windows they work the same with three small substitutions:
>
> - Type **`python`** (or **`py`**) instead of `python3`.
> - Type **`pip`** (or **`py -m pip`**) instead of `pip3`.
> - To open the finished site, use **`start website\index.html`** (or just
>   double-click `index.html`) instead of `open`.
>
> Forward slashes in paths work on Windows too, so the only change you really
> need is `python3` → `python`. Everything else — Pillow, the scripts, the
> generated website — behaves identically. One tip: if you ever hand-edit
> `photo_config.json` on Windows, write paths with forward slashes
> (`C:/Users/You/...`) or doubled backslashes (`C:\\Users\\You\\...`); the
> tools always write them correctly on their own.

---

## Table of contents

1. [What the system builds](#1-what-the-system-builds)
2. [Requirements and first-time setup](#2-requirements-and-first-time-setup)
3. [Quick start](#3-quick-start)
3.5. [A worked example, start to finish](#35-a-worked-example-start-to-finish)
4. [Folder layout and conventions](#4-folder-layout-and-conventions)
5. [The configuration file](#5-the-configuration-file)
6. [Two ways to build the config](#6-two-ways-to-build-the-config)
7. [Validating the config](#7-validating-the-config)
8. [Building the website](#8-building-the-website)
9. ["Read More" pages and sidecar files](#9-read-more-pages-and-sidecar-files)
10. [The standalone slideshow builder](#10-the-standalone-slideshow-builder)
11. [Program reference](#11-program-reference)
12. [Common recipes](#12-common-recipes)
13. [Troubleshooting](#13-troubleshooting)
14. [Appendix: configuration field reference](#14-appendix-configuration-field-reference)

---

## 1. What the system builds

The builder produces a **four-layer website**:

| Layer | Page | What it shows |
|-------|------|---------------|
| 1 | **Home** (`index.html`) | A rotating slideshow plus a button for every gallery. |
| 2 | **Gallery index** (`<gallery>.html`) | A grid of thumbnails for one gallery, each with its caption. |
| 3 | **Photo page** (`<gallery>_<n>.html`) | One large photo with prev/next arrows, zoom, a Download button, and (if present) a "Read More" button. |
| 4 | **Read More page** (`<gallery>_<n>_notes.html`) | An extended write-up about a single photo. Built only for photos that have notes. |

Alongside the pages, the builder creates `photos/`, `thumbnails/`, and
`originals/` (print-quality downloads), plus `css/` and `js/`. The whole
`website/` folder is self-contained: no web server required — double-click
`index.html`.

The pipeline is always the same three ideas:

```
  your photos + descriptions  →  photo_config.json  →  website/
        (source folders)            (the recipe)      (the result)
```

---

## 2. Requirements and first-time setup

This section takes you from the zip file to a working site.

### 2.1 What you need installed

- **Python 3** (3.8 or newer). Check with `python3 --version`.
- **Pillow**, the image library the builder uses for thumbnails and downloads:

  ```bash
  pip3 install pillow
  ```

- **Optional: the `markdown` package**, only if you want rich formatting
  (bullet lists, headings, links) in your "Read More" pages. Plain paragraphs,
  **bold**, and *italic* work without it.

  ```bash
  pip3 install markdown
  ```

### 2.2 Create the project folder

Unzip the programs and arrange a project like this. The zip gives you
`scripts/`; you create an empty `user_files/` beside it. `website/` is
generated later — you don't make it yourself.

```
Project_Gallery/            ← project root; run all commands from here
├── scripts/           ← the programs (from the zip)
└── user_files/             ← you create this; your photos and settings go here
```

```bash
mkdir -p ~/Project_Gallery/user_files
cd ~/Project_Gallery
# move the unzipped scripts/ folder in here if it isn't already
```

> **Always run the commands from the project root** (`~/Project_Gallery`).
> The tools look for things like `user_files/photos.csv` relative to where you
> are standing, so the project root is the spot where all the defaults line up.

### 2.3 Gather your photographs into galleries

A **gallery is simply a sub-folder of `user_files/`** that contains image
files. Make one folder per gallery and drop the photos in.

```
user_files/
├── colonnade/        ← gallery 1: put its .jpg/.png files here
├── gardens/          ← gallery 2
└── kings_mountain/   ← gallery 3
```

Tips for naming and organizing:

- Use short, simple folder names, lowercase with underscores
  (`kings_mountain`). The name becomes the gallery's default title with
  underscores turned to spaces ("Kings Mountain"), and a no-spaces id
  (`kings_mountain`) used in page filenames.
- Supported image types: `.jpg .jpeg .png .gif .bmp .tiff .webp`.
- The **order photos appear** on the site is something you control later (in
  the spreadsheet or JSON) — not the file order on disk.
- **Optional high-resolution downloads.** If you want the site's Download
  button to offer full-quality originals while showing smaller display images
  in the gallery, keep a matching backup folder named `<gallery>_original`
  (e.g. `gardens_original`) holding the full-size files. These backup folders
  are never treated as galleries themselves.

### 2.4 Build the recipe, validate, and generate

Once your photos are in gallery folders, choose one of the two workflows in
[section 6](#6-two-ways-to-build-the-config) to create `photo_config.json`.
The fastest first pass is to let the system scan your folders:

```bash
python3 scripts/generate_photo_config.py --form --user-dir user_files
```

Then validate and build:

```bash
python3 scripts/validate_photo_config.py
python3 scripts/photos_exposition.py user_files/photo_config.json --clean
open website/index.html
```

### 2.5 Write your "Read More" pages (the `.md` files)

Captions are short. For any photo that deserves a story — a heirloom, a family
record, a place with history — add a **sidecar Markdown file** next to the
photo, named to match it. For `Jade_Vase.jpg` in `user_files/heirlooms/`,
create `user_files/heirlooms/Jade_Vase.md`. Full details and the file format
are in [section 9](#9-read-more-pages-and-sidecar-files). You can write these
at any time and simply rebuild.

### 2.6 First-time checklist

- [ ] Python 3 and Pillow installed (`pip3 install pillow`).
- [ ] `Project_Gallery/scripts/` (from the zip) and an empty
      `Project_Gallery/user_files/` in place.
- [ ] One sub-folder per gallery inside `user_files/`, photos dropped in.
- [ ] (Optional) `<gallery>_original` backup folders for high-res downloads.
- [ ] `photo_config.json` created (scan or CSV — section 6).
- [ ] Validator passes (section 7).
- [ ] Site built with `--clean` and opened in a browser (section 8).
- [ ] (Optional) `.md` sidecars written for the photos worth a story (section 9).

---

## 3. Quick start

For when the project is already set up. Run from the project root
(`~/Project_Gallery`).

```bash
cd ~/Project_Gallery

# 1. Create / refresh the recipe from your spreadsheets …
python3 scripts/csv_to_config.py
#    … or by scanning your folders:
#    python3 scripts/generate_photo_config.py --form --user-dir user_files

# 2. Check the recipe for mistakes
python3 scripts/validate_photo_config.py

# 3. Build the website from scratch
python3 scripts/photos_exposition.py user_files/photo_config.json --clean

# 4. View it
open website/index.html
```

---

## 3.5 A worked example, start to finish

This walkthrough builds the two example galleries that ship with the package —
**gardens** and **pets**, four photos each — so you can watch every command and
its output before pointing the tools at your own photographs. It runs the whole
loop: scan → export to a spreadsheet → edit → rebuild → validate → build → view.

> **Why two config-builders appear below.** `generate_photo_config.py` gives you
> a first config by *scanning* your folders; the CSV pair (`config_to_csv.py`
> then `csv_to_config.py`) is the comfortable way to *edit* it afterward. You
> don't need both every time — this example uses each once so you can see how
> they connect.
>
> In the transcripts, a value after the colon is what **you type**; an empty
> prompt means you pressed **Enter** to accept the default shown in `[brackets]`.

### Step 1 — Set your working directory

Run every command from the project root:

```bash
cd ~/Project_Gallery
```

### Step 2 — Scan the folders into a first config

```bash
python3 scripts/generate_photo_config.py --user-dir user_files
```

```text
╔══════════════════════════════════════════════════════════╗
║       Photos at an Exposition — Config Generator         ║
╚══════════════════════════════════════════════════════════╝

────────────────────────────────────────────────────────────
  SITE INFORMATION
────────────────────────────────────────────────────────────
  Website title [Photographs by J. Cooper Rose]: Photographs by X. Y. Z
  Subtitle [A Photographic Journey]:
  Photographer name [J. Cooper Rose]: X. Y. Z
  Overview / welcome text [Welcome to my photographic collection.]:
  Date published [June 2026]:
  Copyright year [2026]:

────────────────────────────────────────────────────────────
  DIRECTORIES
────────────────────────────────────────────────────────────
  User (source) directory: /Users/you/Project_Gallery/user_files
  Output directory (generated website) [/Users/you/Project_Gallery/website]:
  Support files directory (css/logo/js) [/Users/you/Project_Gallery/user_files/support_files]:

────────────────────────────────────────────────────────────
  GALLERIES
────────────────────────────────────────────────────────────
  Found 2 potential gallery folder(s):
    gardens  (4 images)
    pets  (4 images)

  Gallery folder: gardens  (4 photos)
  Include 'gardens' as a gallery? [Y/n]: y
  Gallery ID (no spaces) [gardens]:
  Display name [Gardens]:
  Description [Photos from Gardens]:
  Added 'Gardens' with 4 photo(s).

  Gallery folder: pets  (4 photos)
  Include 'pets' as a gallery? [Y/n]: y
  Gallery ID (no spaces) [pets]:
  Display name [Pets]:
  Description [Photos from Pets]:
  Added 'Pets' with 4 photo(s).

────────────────────────────────────────────────────────────
  SLIDESHOW
────────────────────────────────────────────────────────────
  Gallery: Gardens
  First photo (default): gardens1.jpg
    Choose a different slideshow photo? [y/N]: n
  Selected: gardens1.jpg

  Gallery: Pets
  First photo (default): pets1.jpg
    Choose a different slideshow photo? [y/N]: n
  Selected: pets1.jpg

────────────────────────────────────────────────────────────
  OPTIONS
────────────────────────────────────────────────────────────
  Thumbnail width  (px) [300]: 200
  Thumbnail height (px) [300]: 200
  Thumbnail display size on page (px) [280]: 190
  Slideshow interval (seconds) [5]:
  Show gallery name captions on slideshow? [Y/n]: y

  Writing config to: /Users/you/Project_Gallery/user_files/photo_config.json

  ============================================================
  Configuration saved: /Users/you/Project_Gallery/user_files/photo_config.json
  ============================================================
  Galleries : 2
  Photos    : 8
  Slideshow : 2 photo(s)
  Output dir: /Users/you/Project_Gallery/website
```

Notice the paths are **absolute**. The generators resolve them, so the build
works no matter which directory you launch it from.

### Step 3 — Export the config to a spreadsheet

```bash
python3 scripts/config_to_csv.py
```

This writes `user_files/site_settings.csv` and `user_files/photos.csv`. Open
`photos.csv` in any spreadsheet program — it starts out like this:

| gallery_id | gallery_name | gallery_desc | source_directory | photo_file | note | in_slideshow | notes_title | notes_body |
|---|---|---|---|---|---|---|---|---|
| gardens | Gardens | Photos from Gardens | …/user_files/gardens | gardens1.jpg | | yes | | |
| gardens | Gardens | Photos from Gardens | …/user_files/gardens | gardens2.jpg | | no | | |
| gardens | Gardens | Photos from Gardens | …/user_files/gardens | gardens3.jpg | | no | | |
| gardens | Gardens | Photos from Gardens | …/user_files/gardens | gardens4.jpg | | no | | |
| pets | Pets | Photos from Pets | …/user_files/pets | pets1.jpg | | yes | | |
| pets | Pets | Photos from Pets | …/user_files/pets | pets2.jpg | | no | | |
| pets | Pets | Photos from Pets | …/user_files/pets | pets3.jpg | | no | | |
| pets | Pets | Photos from Pets | …/user_files/pets | pets4.jpg | | no | | |

### Step 4 — Edit the spreadsheet

Change the **`in_slideshow`** column: set `gardens1.jpg` to `no`, `gardens2.jpg`
to `yes`, `gardens3.jpg` to `yes`, and `pets4.jpg` to `yes` (leave `pets1.jpg`
at `yes`). Save the file. The home-page slideshow will now rotate through four
photos — `gardens2.jpg`, `gardens3.jpg`, `pets1.jpg`, and `pets4.jpg`. This is
also where you would add captions (the `note` column) or remove a photo from a
gallery.

### Step 5 — Rebuild the config from the spreadsheet

```bash
python3 scripts/csv_to_config.py
```

This regenerates `user_files/photo_config.json` with your edits.

### Step 6 — Validate before building

```bash
python3 scripts/validate_photo_config.py --config user_files/photo_config.json
```

```text
Validating: /Users/you/Project_Gallery/user_files/photo_config.json

── Tier 1: JSON Syntax ─────────────────────────────────────────────
  ✓ JSON syntax is valid — no missing commas, quotes, or brackets.

── Tier 2: Required Fields ─────────────────────────────────────────
  ✓ Found 'output_directory'
  ✓ Found 'site_info'
  ✓ Found 'slideshow_config'
  ✓ Found 'slideshow_photos'
  ✓ Found 'galleries'
  ✓ Found site_info.title: 'Photographs by X. Y. Z'
  ✓ Found site_info.photographer_name: 'X. Y. Z'
  ✓ Found site_info.copyright_year: '2026'

── Gallery Checks ──────────────────────────────────────────────────
  ✓ Gallery 'gardens': source_directory found
  ✓ Gallery 'gardens': 4 photo(s), 0 note(s)
  ✓ Gallery 'pets': source_directory found
  ✓ Gallery 'pets': 4 photo(s), 0 note(s)

── Slideshow Checks ────────────────────────────────────────────────
  ✓ slideshow_photos[1]: gardens / gardens2.jpg
  ✓ slideshow_photos[2]: gardens / gardens3.jpg
  ✓ slideshow_photos[3]: pets / pets1.jpg
  ✓ slideshow_photos[4]: pets / pets4.jpg

── Output Directory ────────────────────────────────────────────────
  ✓ output_directory: /Users/you/Project_Gallery/website
  ✓ Directory does not exist yet — will be created on build

────────────────────────────────────────────────────────────
  Result: PASSED — no errors or warnings
```

### Step 7 — Build the website

```bash
python3 scripts/photos_exposition.py user_files/photo_config.json --clean
```

The builder copies the photos, generates thumbnails, and writes the pages into
`website/`, finishing with:

```text
Website generated successfully in: /Users/you/Project_Gallery/website
Open /Users/you/Project_Gallery/website/index.html in your browser to view.
```

### Step 8 — Open it

```bash
open website/index.html
```

You'll see the home page with the four-photo slideshow, a button for each
gallery, the thumbnail grids (at the 190 px size you chose), and a dedicated
page for every photo with click-to-zoom and prev/next navigation. That's the
full cycle — from here you would add your own captions, `.md` "Read More"
stories, and galleries, re-running steps 5–7 whenever you change something.

---

## 4. Folder layout and conventions

```
Project_Gallery/                     ← project root (run commands here)
├── scripts/                    ← the programs (and the CSS template)
│   ├── generate_photo_config.py
│   ├── csv_to_config.py
│   ├── config_to_csv.py
│   ├── validate_photo_config.py
│   ├── photos_exposition.py
│   └── build_slideshow.py
├── user_files/                      ← YOUR content lives here
│   ├── photo_config.json            ← the recipe (generated)
│   ├── site_settings.csv            ← site-wide settings (CSV workflow)
│   ├── photos.csv                   ← one row per photo (CSV workflow)
│   ├── Genealogy/                   ← a gallery: photos + optional .md sidecars
│   ├── Genealogy_original/          ← optional full-resolution backup
│   ├── pets/
│   └── …
└── website/                         ← the generated site (output)
```

### Gallery folders

Each gallery is one sub-folder of `user_files/` containing image files. The
folder name becomes the default gallery name (underscores become spaces) and
the gallery id (used in page filenames).

### `_original` backup folders

If a folder named `<Gallery>_original` sits next to a gallery (for example
`Genealogy_original` beside `Genealogy`), the builder uses it as the source of
the **full-resolution download copies**, so you can keep smaller display
images live while still offering high-quality downloads. These backup folders
are **ignored** when scanning for galleries — they never become galleries of
their own.

### Sidecar files

A Markdown file named to match a photo — `Anna_Ruby_Falls.md` next to
`Anna_Ruby_Falls.jpg` — supplies that photo's "Read More" page. See
[section 9](#9-read-more-pages-and-sidecar-files).

### Reserved / legacy fields

Some configs carry `support_files_directory` and `max_galleries`. The current
builder generates its own CSS/JS and imposes no gallery limit, so these two
fields are **ignored**. They do no harm; you can leave or remove them.

---

## 5. The configuration file

`photo_config.json` is the single recipe the builder reads. You rarely write
it by hand — `csv_to_config.py` or `generate_photo_config.py` produces it —
but it helps to understand its shape.

```jsonc
{
  "site_info": {
    "title":             "Photographs by X, Y. Z",
    "subtitle":          "A Photographic Journey",
    "photographer_name": "X. Y. Z",
    "overview":          "Welcome to my photographic collection.",
    "date_published":    "May 2026",
    "copyright_year":    "2026"
  },
  "output_directory":       "/Users/yourname/Project_Gallery/website",
  "thumbnail_size":         [300, 300],     // pixel box thumbnails are fit into
  "thumbnail_display_size": 280,            // grid cell size on the page
  "print_max_px":           3000,           // long-edge cap for download copies
  "slideshow_config":  { "interval_seconds": 5, "show_captions": true },
  "galleries": [
    {
      "id":               "genealogy",          // no spaces
      "name":             "Genealogy",
      "description":      "Photos from Genealogy",
      "source_directory": "/Users/yourname/Project_Gallery/user_files/Genealogy",
      "photos":           ["DHR1opt.jpg", "JCR1opt.jpg", "…"],
      "notes":            { "DHR1opt.jpg": "The family Bible", "…": "" },
      "extended_notes":   { }                   // optional; usually from CSV/sidecars
    }
  ],
  "slideshow_photos": [
    { "gallery_id": "genealogy", "photo_file": "DHR1opt.jpg" }
  ]
}
```

Key points:

- **`photos` order = page order.** Reorder this list to reorder the gallery.
- **`notes`** are the short captions under thumbnails and on photo pages.
- **`slideshow_photos`** picks which images appear in the home-page slideshow,
  in order. One per gallery is the usual convention.
- **`output_directory`** may be absolute or relative to where you run the
  build. (macOS treats paths case-insensitively.)

A full field-by-field table is in [the appendix](#14-appendix-configuration-field-reference).

---

## 6. Two ways to build the config

You can maintain your site in **spreadsheets** or have the system **scan your
folders**. Both produce the same `photo_config.json`. Pick whichever you
prefer; you can switch at any time (and convert between them).

### Path A — the CSV workflow (recommended for ongoing editing)

You keep two spreadsheets in `user_files/`:

- **`site_settings.csv`** — one row per setting (`field,value`).
- **`photos.csv`** — one row per photo.

Create starter files to edit:

```bash
python3 scripts/csv_to_config.py --sample
```

Edit them in any spreadsheet program, then build the config:

```bash
python3 scripts/csv_to_config.py
```

`photos.csv` columns (a header row is required):

| Column | Required | Meaning |
|--------|----------|---------|
| `gallery_id` | yes | Short id, no spaces (e.g. `family_reunion`). Groups rows into galleries. |
| `gallery_name` | yes | Display name (e.g. "Family Reunion"). |
| `gallery_desc` | no | Optional gallery description. |
| `source_directory` | yes | Full path to the folder holding the photo. |
| `photo_file` | yes | Filename only (e.g. `IMG_001.jpg`). |
| `note` | no | Caption shown under the photo. |
| `in_slideshow` | yes | `yes` or `no` — include this photo in the home slideshow. |
| `seq` | no | Integer ordering **within** a gallery. Number sparsely (10, 20, 30…) so you can insert later. Blank rows sort after numbered ones. If no row has a `seq`, CSV order is used. |
| `notes_title` | no | Heading for the photo's "Read More" page. |
| `notes_body` | no | Body text for the "Read More" page. Use `\n\n` for paragraph breaks, or quote the cell and use real line breaks. A sidecar `.md` file, if present, overrides this. |

`site_settings.csv` has just two columns, `field` and `value`, with rows for
`title`, `subtitle`, `overview`, `photographer_name`, `date_published`,
`copyright_year`, `output_directory`, `thumbnail_width`, `thumbnail_height`,
`thumbnail_display_size`, `slideshow_interval_seconds`, and
`slideshow_show_captions`.

The reverse tool exports your current config back into these two CSVs — handy
if you started from a scan, or hand-edited the JSON and want your spreadsheets
back in sync:

```bash
python3 scripts/config_to_csv.py
```

### Path B — scan the folders

`generate_photo_config.py` walks `user_files/`, treats each sub-folder
(except `_original` backups and support folders) as a gallery, and writes a
ready-to-edit config. Two modes:

```bash
# Form mode — no questions; writes a pre-filled photo_config.json you then edit
python3 scripts/generate_photo_config.py --form --user-dir user_files

# Wizard mode — interactive; prompts for titles, captions, slideshow picks
python3 scripts/generate_photo_config.py --user-dir user_files
```

Form mode is the fast path: it fills in every gallery with blank captions you
fill in afterward (in the JSON, or by exporting to CSV with
`config_to_csv.py`).

---

## 7. Validating the config

Before every build, check the recipe:

```bash
python3 scripts/validate_photo_config.py
```

It runs in two tiers and prints a ✓ / ⚠ / ✗ for each check:

- **Tier 1 — Syntax.** Confirms the JSON is well-formed and, if not, points to
  the exact line and column.
- **Tier 2 — Content.** Confirms required fields exist; flags duplicate
  gallery ids, names, or source folders (a classic sign of a mistyped
  `gallery_id` that split one gallery in two); duplicate or missing photos;
  notes that reference photos not in the list; and slideshow picks that don't
  match a real photo. It also checks that source folders and photo files
  actually exist on disk.

Add `--no-disk` to skip the file-existence checks (useful when validating a
config meant for a different machine):

```bash
python3 scripts/validate_photo_config.py --no-disk
```

A non-zero exit code means errors were found. Warnings (⚠) don't stop a build
but are worth reading.

---

## 8. Building the website

```bash
python3 scripts/photos_exposition.py user_files/photo_config.json --clean
```

The config path is **required** (it's the one argument). What the builder does,
in order:

1. Optionally cleans previously generated output (with `--clean`).
2. Creates the folder structure.
3. Copies each photo and generates a thumbnail (fit within `thumbnail_size`).
4. Publishes a print-quality download copy of each photo into `originals/`,
   downscaled so its long edge is at most `print_max_px` (default 3000),
   preferring the `<gallery>_original` backup folder if one exists.
5. Generates the CSS and JavaScript.
6. Generates the home, gallery, photo, and "Read More" pages.

### The `--clean` flag

Without `--clean`, the builder adds to and overwrites files but leaves orphans
behind — if you removed or renamed a gallery, its old pages and images linger.
With `--clean`, it first removes the generated `photos/`, `thumbnails/`,
`originals/`, `css/`, `js/`, and top-level `*.html` from the output directory,
then rebuilds. **Use `--clean` whenever you add, remove, or rename a gallery.**
It only ever deletes files the builder itself creates, so it can't harm
unrelated files in the output folder.

> Re-running without `--clean` is faster because existing `originals/` copies
> are skipped — handy when you've only edited captions or notes.

---

## 9. "Read More" pages and sidecar files

A "Read More" page (layer 4) is a longer write-up attached to a single photo.
There are two ways to supply one; if both exist for a photo, the **sidecar
wins**.

1. **CSV `notes_body`** — fill the `notes_body` (and optional `notes_title`)
   column in `photos.csv`. Good for short notes.
2. **Sidecar file** — a Markdown file beside the photo, matched by filename.
   Best for longer pieces. For `DHR1opt.jpg` in `user_files/Genealogy/`, create
   `user_files/Genealogy/DHR1opt.md` (or `.txt`).

### Sidecar format

```markdown
---
title: The Family Bible
---
This Bible was carried by **Douglas Hall Rose**…

It passed to each eldest son in turn, and the marriage
records on the flyleaf go back to 1832.
```

- The optional `--- title: … ---` block at the very top becomes the page
  heading. Without it, the heading falls back to the filename with underscores
  turned to spaces (`Anna_Ruby_Falls.md` → "Anna Ruby Falls").
- Everything below is the body. Separate paragraphs with a blank line.
- Basic Markdown — `**bold**`, `*italic*`, blank-line paragraphs — always
  works. Richer Markdown (bullet lists, headings, links, block quotes) renders
  fully only if the optional `markdown` package is installed
  (`pip3 install markdown`).

### Placeholder stubs

A sidecar whose body contains **only an HTML comment** is treated as empty —
no "Read More" button or page is generated until you replace the comment with
real text. This lets you scaffold a file in advance:

```markdown
---
title: A Chinese Jade Vase
---
<!-- Write the story behind this photo here, then rebuild the site.
     Until you replace this comment with real text, this photo will
     NOT show a "Read More" button. -->
```

Rebuild after editing; the page appears automatically once there's real text.

### A simple way to add stories in bulk

1. Decide which photos deserve a write-up.
2. For each, create `<PhotoName>.md` in the same gallery folder.
3. Give it a `title:` block and write your text in plain paragraphs.
4. Rebuild with `--clean` and open the gallery — those photos now show a
   "Read More" button.

---

## 10. The standalone slideshow builder

`build_slideshow.py` is a **separate tool** from the website. Don't confuse the
two slideshows:

- The **home-page slideshow** inside the website is produced by
  `photos_exposition.py` from `slideshow_photos`. You don't run anything extra
  for it.
- **`build_slideshow.py`** produces a single self-contained `slideshow.html`
  file — a full-screen viewer, separate from the gallery site. Use it when you
  just want a quick standalone slideshow of a folder tree.

It has three sub-commands:

```bash
# Scan a media tree → photo_config.json
python3 scripts/build_slideshow.py scan --media-dir ./media --output photo_config.json

# Build slideshow.html from an existing config (understands photo_config.json too)
python3 scripts/build_slideshow.py build --config user_files/photo_config.json --output slideshow.html

# Do both at once
python3 scripts/build_slideshow.py all --media-dir user_files --title "Rose Family Photos" --sort name
```

Options for `scan` / `all`: `--media-dir`, `--title`, `--sort name|date|random`,
`--no-recursive`, `--output`. See the [program reference](#11-program-reference).

---

## 11. Program reference

All commands are shown run from the project root (`~/Project_Gallery`).

### generate_photo_config.py — scan folders into a config

Walks a user directory, treats each sub-folder (skipping `*_original` backups
and `support_files/slideshow/css/js`) as a gallery, and writes
`photo_config.json`.

| Option | Short | Default | Meaning |
|--------|-------|---------|---------|
| `--user-dir` | `-u` | *(prompts)* | The folder whose sub-folders are your galleries. |
| `--output` | `-o` | `photo_config.json` | Config filename/path. Relative names are written inside the user dir. |
| `--form` | `-f` | off | Non-interactive: scan and write a pre-filled config (blank captions), no questions. |

Without `--form`, it runs an interactive wizard (site info, gallery selection,
slideshow picks, thumbnail options).

> **Note:** form mode writes `photo_config.json` **into the user directory**,
> overwriting any existing one there. Keep a copy if yours is hand-tuned.

### csv_to_config.py — spreadsheets into a config

| Option | Short | Default | Meaning |
|--------|-------|---------|---------|
| `--photos` | `-p` | `user_files/photos.csv` | Per-photo CSV. |
| `--site` | `-s` | `user_files/site_settings.csv` | Site-settings CSV. |
| `--output` | `-o` | `user_files/photo_config.json` | Where to write the config. |
| `--sample` | | off | Write starter `site_settings.csv` and `photos.csv` into `user_files/`, then exit. |

### config_to_csv.py — config back into spreadsheets

| Option | Short | Default | Meaning |
|--------|-------|---------|---------|
| `--config` | `-c` | `user_files/photo_config.json` | Config to export. |
| `--output-dir` | `-o` | `user_files` | Folder to write the two CSVs into. |

### validate_photo_config.py — check a config

| Option | Short | Default | Meaning |
|--------|-------|---------|---------|
| `--config` | `-c` | `user_files/photo_config.json` | Config to validate. |
| `--no-disk` | | off | Skip checks that read the file system (folder/file existence). |

Exit code is non-zero if any errors are found.

### photos_exposition.py — build the website

| Argument / Option | Default | Meaning |
|-------------------|---------|---------|
| `config` *(positional, required)* | — | Path to `photo_config.json`. |
| `--clean` | off | Remove previously generated output first (use when adding/removing/renaming galleries). |

### build_slideshow.py — standalone slideshow

Sub-commands: `scan`, `build`, `all`.

| Option | Applies to | Default | Meaning |
|--------|-----------|---------|---------|
| `--media-dir` | scan, all | `./media` | Root folder of gallery sub-folders. |
| `--title` | scan, all | `Rose Family Photos` | Headline shown in the viewer. |
| `--sort` | scan, all | `name` | Image order: `name`, `date`, or `random`. |
| `--no-recursive` | scan, all | (recursive on) | Don't descend into sub-sub-folders. |
| `--output` | all sub-commands | varies | Output path. For `build`, defaults near the media root's sibling `website/`, else `./slideshow.html`. |
| `--config` | build | `photo_config.json` | Config to read. |
| `--config-out` | all | `photo_config.json` | Where `all` writes its interim config. |

---

## 12. Common recipes

**Set up a brand-new site.** Create `user_files/` with one sub-folder per
gallery, drop photos in, then scan and build (see
[section 2](#2-requirements-and-first-time-setup)).

**Trim the site to a few galleries.** Keep only the galleries you want in
`photos.csv` (or the `galleries` list), rebuild the config, then build with
`--clean`.

**Add a new photo to a gallery.** Drop the image into the gallery folder, add a
row to `photos.csv` (or add the filename to that gallery's `photos` list),
rebuild the config, validate, and build.

**Add a new gallery.** Create a new sub-folder in `user_files/`, put photos in
it, add its rows to `photos.csv` (or re-scan with `generate_photo_config.py`),
then build with `--clean`.

**Write a "Read More" page.** Create `<PhotoName>.md` beside the photo with a
`title:` block and your text, then rebuild. (Or fill `notes_title` /
`notes_body` in `photos.csv`.)

**Change which photo represents a gallery in the slideshow.** Edit that
gallery's entry in `slideshow_photos` (or set `in_slideshow` in `photos.csv`),
then rebuild.

**Reorder a gallery's photos.** Use the `seq` column in `photos.csv` (number
sparsely: 10, 20, 30…), or reorder the `photos` list in the JSON.

---

## 13. Troubleshooting

**`ModuleNotFoundError: No module named 'PIL'` when building.** Pillow isn't
installed: `pip3 install pillow`.

**"Warning: … not found, skipping" during a build.** A photo listed in the
config isn't in its source folder — the filename changed or the file was
removed. Fix the filename in `photos.csv`/JSON, or restore the file. Run the
validator to catch these before building.

**A gallery appears twice (e.g. "Gardens" and "Gardens Original").** Older
versions of `generate_photo_config.py` mistook `_original` backup folders for
galleries. The current version skips any folder ending in `_original`. If you
see this, you're running an old copy — update the script.

**Duplicate gallery name / source warnings from the validator.** Usually a
mistyped `gallery_id` that split one gallery into two. Make all rows for one
gallery share the exact same `gallery_id`.

**"Read More" text shows raw `##` or `-` characters.** The richer Markdown
features need the optional package: `pip3 install markdown`. Plain paragraphs,
**bold**, and *italic* work without it.

**A folder name's capitalization differs from the config (e.g. `Heirlooms`
vs `heirlooms`).** macOS ignores case, so the site still builds. Git, however,
can track a different case than the disk — if a file seems "missing" from a
commit, check the case of the tracked path.

**The download button gives a small image.** Downloads come from `originals/`,
capped at `print_max_px` (default 3000 px long edge) and sourced from the
`<gallery>_original` backup if present. Raise `print_max_px` in the config, or
make sure your full-resolution files are in the `_original` folder.

---

## 14. Appendix: configuration field reference

Top-level fields in `photo_config.json`:

| Field | Type | Used by builder | Meaning |
|-------|------|-----------------|---------|
| `site_info.title` | string | yes | Site title (home page, tab title). |
| `site_info.subtitle` | string | yes | Shown under the title. |
| `site_info.photographer_name` | string | yes | Footer / copyright name. |
| `site_info.overview` | string | yes | Welcome text. |
| `site_info.date_published` | string | yes | Shown in the footer. |
| `site_info.copyright_year` | string | yes | Footer copyright year. |
| `output_directory` | string | yes | Where the site is written. Absolute or relative. |
| `thumbnail_size` | `[w, h]` | yes | Pixel box thumbnails are fit within. |
| `thumbnail_display_size` | int | yes | Grid cell size (px) on gallery pages. |
| `print_max_px` | int | yes | Long-edge cap for download copies (default 3000). |
| `slideshow_config.interval_seconds` | int | yes | Seconds between slides. |
| `slideshow_config.show_captions` | bool | yes | Show gallery-name captions on slides. |
| `galleries[]` | list | yes | One object per gallery (see below). |
| `slideshow_photos[]` | list | yes | `{gallery_id, photo_file}` picks for the home slideshow, in order. |
| `support_files_directory` | string | **no (legacy)** | Ignored — the builder generates its own CSS/JS. |
| `max_galleries` | int/null | **no (legacy)** | Ignored — no gallery limit is enforced. |

Per-gallery fields (`galleries[]`):

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | Short identifier, **no spaces**. Drives page filenames. |
| `name` | string | Display name. |
| `description` | string | Optional gallery description. |
| `source_directory` | string | Folder holding this gallery's photos (and sidecars). |
| `photos` | list | Filenames, **in display order**. |
| `notes` | object | `{filename: caption}` short captions. |
| `extended_notes` | object | Optional `{filename: {title, body}}` for "Read More" (from CSV). Sidecar `.md` files override this. |

---

*Generated for the Project Gallery system. Keep this file in the project root
so it travels with the code.*
