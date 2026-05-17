# Photos at an Exposition — User Manual

This manual walks you through building your own photo website from start to
finish. No web development background needed — if you can drag files into
folders and copy-paste a command into a terminal window, you can do this.

By the end you'll have:

- A home page with a rotating slideshow header and one button per gallery
- A thumbnail page for each gallery
- A page for every photo with click-to-zoom and prev/next arrows
- A separate full-screen slideshow viewer for showing photos at gatherings

The whole site is just files on your hard drive. Nothing depends on the
internet — you can copy the `website/` folder onto a USB stick or send it to
someone in a zip file and it works.

## Table of contents

1. What you need before you start
2. Step 1 — Lay out your photos
3. Step 2 — (Optional) Write captions
4. Step 3 — Generate the config file
5. Step 4 — Edit the config file
6. Step 5 — Build the website
7. Step 6 — Build the slideshow viewer
8. Step 7 — Open your website
9. Updating: adding photos, fixing captions, re-running the scripts
10. Tips and shortcuts
11. Troubleshooting

## 1. What you need before you start

**A computer** with Python 3 installed. Most Macs and Linux machines have it.
On Windows you may need to install Python from <https://python.org>. To
check, open a terminal and type:

```bash
python3 --version
```

If you see something like `Python 3.11.5`, you're set. If you see "command
not found," install Python first.

**The Pillow library**, which the scripts use to make thumbnails. Install it
once:

```bash
pip3 install Pillow
```

**The three scripts** from this repository, somewhere on your computer.
Anywhere is fine; a folder called `scripts/` next to your photos is tidy.

**A folder to work in.** This manual uses `project_gallery` as the example
name, but you can call it anything.

## 2. Step 1 — Lay out your photos

Create one folder per gallery inside a folder called `user_files`. Each
gallery folder holds the photos that will appear together in one section of
your site.

```
project_gallery/
└── user_files/
    ├── Colonnade/
    │   ├── Bedroom.jpg
    │   ├── Dining_Area.jpg
    │   └── Front_Hall.jpg
    ├── Gardens/
    │   ├── Rose_Bed.jpg
    │   └── Wisteria.jpg
    └── Kings_Mountain/
        ├── Blacksmith.jpg
        ├── Cotton_Field.jpg
        └── Old_Barn.jpg
```

A few rules:

- **Folder names become gallery names.** `Kings_Mountain` becomes "Kings
  Mountain" on the website. Underscores turn into spaces, and the words
  get capitalized.
- **Use letters, numbers, underscores, and hyphens.** Spaces in folder
  names mostly work but cause headaches later — stick to `Kings_Mountain`,
  not `Kings Mountain`.
- **Supported photo formats:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`,
  `.tiff`, `.tif`, `.webp`.
- **No nested galleries.** Photos go directly inside a gallery folder, not
  in sub-folders below it.

## 3. Step 2 — (Optional) Write captions

You have three ways to add a caption to a photo. You can mix and match, and
you can always add captions later — they're not required to build the site.

**Option A — Caption file inside the gallery folder.** Create a plain text
file called `notes.txt` inside any gallery folder. Each line is one caption
in this format:

```
Blacksmith.jpg | The Blacksmith at his Forge.<br>It was a festival day at the park.
Cotton_Field.jpg | Cotton Field. Until I saw this field, I did not know what a cotton field looks like close up.
Old_Barn.jpg | The Old Two Story Barn
```

The filename comes first, then a pipe character `|`, then the caption.
Use `<br>` anywhere in a caption to force a line break. Captions can be as
short or long as you like.

You can also name the file `captions.txt` or `notes.csv` — the script
looks for all three.

**Option B — Edit `photo_config.json` later.** If you don't make a
`notes.txt`, you'll get blank caption slots in the config file that you
can fill in after the next step.

**Option C — Skip captions.** Photos without captions just show up
without captions. No big deal.

## 4. Step 3 — Generate the config file

The config file (`photo_config.json`) is the brain of your project. It
lists every gallery, every photo, every caption, the website title, and
which photo represents each gallery in the home-page slideshow.

You build it once, then edit it whenever you want to change something.

Open a terminal, navigate to wherever you put `project_gallery`, and run:

```bash
python3 scripts/generate_photo_config.py --user-dir project_gallery/user_files --form
```

The `--form` flag means "skip the questions, just scan." It writes
`photo_config.json` into `project_gallery/user_files/` with:

- Default site title and photographer name (you'll edit these next)
- One gallery entry per folder it found
- Every photo listed in alphabetical order
- A blank caption for every photo (unless you used a `notes.txt`)
- The first photo of each gallery picked as the slideshow representative

If you'd rather answer questions instead of editing the JSON, leave off
`--form`:

```bash
python3 scripts/generate_photo_config.py --user-dir project_gallery/user_files
```

The wizard walks you through site info, gallery-by-gallery confirmation,
slideshow photo picks, and thumbnail size. Either way, the end result is
the same JSON file.

## 5. Step 4 — Edit the config file

Open `project_gallery/user_files/photo_config.json` in any text editor
(TextEdit, Notepad, VS Code, BBEdit — anything that handles plain text).

You'll see something like this near the top:

```json
{
  "site_info": {
    "title": "Photographs by J. Cooper Rose",
    "subtitle": "A Photographic Journey",
    "photographer_name": "J. Cooper Rose",
    "overview": "Welcome to my photographic collection.",
    "date_published": "May 2026",
    "copyright_year": "2026"
  },
  ...
```

Change these to your own values. Then scroll down to find each gallery and
its notes:

```json
{
  "id": "kings_mountain",
  "name": "Kings Mountain",
  "description": "Photos from Kings Mountain",
  "source_directory": "/Users/you/project_gallery/user_files/Kings_Mountain",
  "photos": [
    "Blacksmith.jpg",
    "Cotton_Field.jpg",
    "Old_Barn.jpg"
  ],
  "notes": {
    "Blacksmith.jpg": "",
    "Cotton_Field.jpg": "",
    "Old_Barn.jpg": ""
  }
}
```

Type your caption between the empty `""` marks:

```json
  "notes": {
    "Blacksmith.jpg": "The Blacksmith at his Forge.<br>It was a festival day.",
    "Cotton_Field.jpg": "Cotton Field. Until I saw this field, I did not know what a cotton field looks like close up.",
    "Old_Barn.jpg": "The Old Two Story Barn"
  }
```

**A few quick rules about JSON editing:**

- Keep all the quote marks `"` — they're required.
- A comma goes between entries but **not after the last one** in a list
  or block.
- If you want a literal quote inside a caption, escape it as `\"`.
- Use `<br>` for line breaks inside captions. Other simple HTML like
  `<em>...</em>` also works.

You can also **reorder photos** by rearranging the `photos` list, and
**change the slideshow pick** for each gallery by editing
`slideshow_photos` near the top of the file.

## 6. Step 5 — Build the website

```bash
python3 scripts/photos_exposition.py project_gallery/user_files/photo_config.json
```

This reads the config and writes a complete website into
`project_gallery/website/`:

- `index.html` — the home page
- `colonnade.html`, `gardens.html`, etc. — one index per gallery
- `colonnade_0.html`, `colonnade_1.html`, ... — one page per photo
- `photos/` — full-size copies of every photo
- `thumbnails/` — 300×300 thumbnails
- `css/style.css` — page styling
- `js/slideshow.js` — home-page slideshow logic

Re-running this script is safe — it overwrites whatever was there.

## 7. Step 6 — Build the slideshow viewer

The slideshow viewer is a separate, single-file HTML page that's great for
showing photos at family gatherings — sidebar of galleries, thumbnail
strip, autoplay, fullscreen, keyboard arrows. Build it with:

```bash
python3 scripts/build_slideshow.py build --config project_gallery/user_files/photo_config.json
```

It writes `slideshow.html` into your `project_gallery/website/` folder
(right next to `index.html`). If you want it somewhere else, add
`--output some/other/path/slideshow.html`.

You can also do steps 5 and 7 in any order. They don't depend on each
other.

## 8. Step 7 — Open your website

In Finder (Mac) or File Explorer (Windows), open the `website/` folder
and double-click `index.html`. Your browser opens and your site appears.

To view the slideshow viewer, double-click `slideshow.html` from the same
folder.

**To share the site with someone else,** zip the entire `website/` folder
and send it. They unzip and open `index.html` — no further setup needed.

**To put it on the web,** any static hosting service works: GitHub Pages,
Netlify, AWS S3, your own server. Upload the contents of `website/` and
point your domain at it.

## 9. Updating

The most common workflows once your site exists:

### Adding new photos to an existing gallery

1. Drop the new files into the right folder under `user_files/`
2. Re-run `generate_photo_config.py --form` to refresh the JSON. **This
   resets every note to blank**, so if you've already typed captions, see
   the safer option below.
3. Re-run `photos_exposition.py` and `build_slideshow.py`

**To preserve existing captions**, skip step 2 and instead manually add
the new filenames to the right gallery's `photos` list AND `notes`
dictionary in `photo_config.json`. The scripts will pick them up on the
next build.

### Fixing or adding a caption

1. Open `photo_config.json` and edit the caption
2. Re-run `photos_exposition.py` and `build_slideshow.py`
3. Hard-refresh the browser (Cmd-Shift-R on Mac, Ctrl-Shift-R elsewhere)

### Changing the site title or overview text

1. Open `photo_config.json` and edit the `site_info` block at the top
2. Re-run `photos_exposition.py`. (The slideshow viewer also picks this
   up if you re-run `build_slideshow.py`.)

### Reordering photos within a gallery

Rearrange the entries in that gallery's `photos` list inside
`photo_config.json`, then re-run `photos_exposition.py` and
`build_slideshow.py`.

### Reordering galleries

Reorder the entries in the top-level `galleries` list inside
`photo_config.json`.

### Picking a different slideshow representative photo

Find `slideshow_photos` near the top of `photo_config.json` and change
the `photo_file` for that gallery.

## 10. Tips and shortcuts

**Use `<br>` for line breaks** inside captions. The viewer turns it into
a real line break.

**Keep a backup of `photo_config.json`** before re-running
`generate_photo_config.py --form`, since `--form` resets notes to blank.
A copy named `photo_config.backup.json` saves a lot of grief.

**Keyboard shortcuts in the slideshow viewer:**

- `→` or `↓` — next photo
- `←` or `↑` — previous photo
- `Space` — play / pause
- `F` — toggle fullscreen
- `N` — toggle the caption overlay
- `Home` / `End` — jump to first / last photo in the current gallery
- `Escape` — exit fullscreen

**The wizard vs. the form mode.** The wizard
(`generate_photo_config.py` with no flags) is friendlier for first-time
setup. The form mode (`--form`) is faster for scanning a fresh folder
when you'll edit the JSON anyway.

**Multiple sites.** Run the scripts against different `user_files/`
directories to produce separate websites. Each `project_gallery/`
folder is fully self-contained.

## 11. Troubleshooting

**"Notes don't show up in the slideshow."** Almost always means the
slideshow was built from an older version of `photo_config.json` before
you added the captions. Re-run `build_slideshow.py` and hard-refresh
the browser (Cmd-Shift-R / Ctrl-Shift-R).

**"Photos look broken — missing image icons."** Check the
`source_directory` for that gallery in `photo_config.json`. If you
moved your `user_files/` folder, those paths point to where it used to
be. Re-run `generate_photo_config.py --form` to refresh the paths, or
hand-edit them.

**"Thumbnails are tiny / huge."** Change `thumbnail_size` and
`thumbnail_display_size` near the top of `photo_config.json`, then
re-run `photos_exposition.py`.

**"`pip3 install Pillow` says 'externally managed environment'."**
On newer Python installs you may need `pip3 install Pillow
--break-system-packages` or to use a virtual environment. Search
"pip externally-managed-environment" for your specific platform.

**"Python script crashes on a huge photo."** `photos_exposition.py`
already raises Pillow's safety limit and pre-shrinks giant images
before thumbnailing. If you hit a wall anyway, downsize the original
file (anything under 50 megapixels is comfortable).

**"The slideshow viewer opens but every image is a broken icon."** The
slideshow HTML expects the photos to live in the same directory tree
it was generated from. If you moved `slideshow.html` somewhere
unrelated, the photo paths break. Keep `slideshow.html` inside
`project_gallery/website/`, or pass `--output` so the script can
compute paths correctly.

**"I see the gallery name and filename, but no caption text."** Two
likely causes: (1) the caption is blank in `photo_config.json`, or (2)
you've toggled captions off. Click the `📝 Notes` button at the bottom
of the slideshow, or press `N`.

**Anything else?** Open `photo_config.json` and look at what's actually
in there for the photo in question. The config is the source of truth
— if the data is right there and the website is wrong, rebuild. If the
data is wrong there, fix the config and rebuild.
