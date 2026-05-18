#!/usr/bin/env python3
"""
build_slideshow.py  –  GRASP Photo Slideshow Builder
=====================================================
Scans a media directory tree, writes photo_config.json,
then generates a standalone slideshow.html.

Usage
-----
  # Step 1 – scan directories and write config
  python build_slideshow.py scan  --media-dir ./media  --output photo_config.json

  # Build from photos_exposition photo_config.json directly
  python build_slideshow.py build --config user_files/photo_config.json --output slideshow.html

  # Do both in one shot
  python3 scripts/build_slideshow.py all   --media-dir /users/jamesrose/project_gallery/user_files --output slideshow.html  --title "Rose Family Photos"  --sort  name 

  # Optional flags (apply to scan / all):
  #   --title "Rose Family Photos"   – headline shown in the viewer
  #   --sort  name|date|random       – image order within each gallery
  #   --recursive                    – descend into sub-sub-folders (default: on)
  
"""

import os
import sys
import json
import argparse
import random
import html as html_mod
from pathlib import Path
from datetime import datetime

# ── image extensions we care about ──────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}

# ── helpers ──────────────────────────────────────────────────────────────────

def nice_name(raw: str) -> str:
    """Turn a folder name like 'old_photos_1940s' into 'Old Photos 1940s'."""
    return raw.replace("_", " ").replace("-", " ").title()


def image_sort_key(path: Path, sort: str):
    if sort == "date":
        try:
            return path.stat().st_mtime
        except OSError:
            return 0
    if sort == "random":
        return random.random()
    return path.name.lower()          # "name" (default)


# ── SCAN ─────────────────────────────────────────────────────────────────────

def scan_galleries(media_dir: Path, sort: str, recursive: bool) -> list[dict]:
    """
    Walk media_dir.  Each sub-directory becomes one gallery.
    Images sitting directly in media_dir go into a "__root__" gallery
    named after the folder itself.
    """
    media_dir = media_dir.resolve()
    if not media_dir.is_dir():
        sys.exit(f"ERROR: media directory not found: {media_dir}")

    # Collect: dir -> [image Paths]
    buckets: dict[Path, list[Path]] = {}

    glob_fn = media_dir.rglob if recursive else media_dir.glob
    for p in sorted(glob_fn("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            buckets.setdefault(p.parent, []).append(p)

    galleries = []
    for folder in sorted(buckets.keys()):
        images = sorted(buckets[folder], key=lambda p: image_sort_key(p, sort))

        if folder == media_dir:
            label = nice_name(media_dir.name)
        else:
            try:
                rel = folder.relative_to(media_dir)
                label = nice_name(str(rel).replace(os.sep, " › "))
            except ValueError:
                label = nice_name(folder.name)

        # Store paths relative to media_dir so the config is portable
        rel_images = []
        for img in images:
            try:
                src = str(img.relative_to(media_dir)).replace("\\", "/")
            except ValueError:
                src = str(img).replace("\\", "/")
            rel_images.append({"src": src, "note": ""})

        if rel_images:
            galleries.append({
                "label":  label,
                "folder": str(folder.relative_to(media_dir)).replace("\\", "/") if folder != media_dir else ".",
                "images": rel_images,
            })

    return galleries


def cmd_scan(args) -> dict:
    media_dir = Path(args.media_dir)
    sort      = getattr(args, "sort", "name")
    recursive = getattr(args, "recursive", True)

    print(f"Scanning  : {media_dir}")
    galleries = scan_galleries(media_dir, sort, recursive)

    total = sum(len(g["images"]) for g in galleries)
    config = {
        "title":      getattr(args, "title", "Photo Slideshow"),
        "media_root": str(media_dir.resolve()).replace("\\", "/"),
        "generated":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sort":       sort,
        "galleries":  galleries,
        "total":      total,
    }

    out = Path(args.output) if hasattr(args, "output") and args.output else Path("photo_config.json")
    out.write_text(json.dumps(config, indent=2))

    print(f"Galleries : {len(galleries)}")
    print(f"Images    : {total}")
    print(f"Config    : {out}")
    return config


# ── BUILD ─────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
/* ── reset & base ─────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg:        #0a0a0f;
  --surface:   #14141e;
  --panel:     #1c1c2a;
  --border:    #2e2e44;
  --accent:    #c9a84c;
  --accent2:   #8b6914;
  --text:      #e8e0d0;
  --muted:     #7a7090;
  --radius:    6px;
  --trans:     .3s ease;
}}
html, body {{ height: 100%; background: var(--bg); color: var(--text);
              font-family: 'Georgia', 'Times New Roman', serif; overflow: hidden; }}

/* ── layout ───────────────────────────────────────── */
#app {{ display: flex; height: 100vh; width: 100vw; }}

/* sidebar */
#sidebar {{
  width: 260px; min-width: 200px; max-width: 340px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  transition: transform var(--trans);
  z-index: 10;
  resize: horizontal; overflow: auto;
}}
#sidebar-head {{
  padding: 18px 16px 12px;
  border-bottom: 1px solid var(--border);
}}
#sidebar-head h1 {{
  font-size: .75rem; letter-spacing: .18em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 6px;
}}
#sidebar-head h2 {{
  font-size: 1.05rem; font-weight: normal; color: var(--text); line-height: 1.3;
}}
#gallery-list {{
  flex: 1; overflow-y: auto; padding: 8px 0;
}}
#gallery-list::-webkit-scrollbar {{ width: 4px; }}
#gallery-list::-webkit-scrollbar-track {{ background: transparent; }}
#gallery-list::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

.gal-item {{
  padding: 9px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background var(--trans), border-color var(--trans);
  display: flex; justify-content: space-between; align-items: center;
}}
.gal-item:hover {{ background: var(--panel); }}
.gal-item.active {{ border-left-color: var(--accent); background: var(--panel); }}
.gal-item .gal-label {{ font-size: .88rem; line-height: 1.3; }}
.gal-item .gal-count {{ font-size: .72rem; color: #fff;
                        background: var(--bg); border-radius: 10px;
                        padding: 1px 6px; margin-left: 8px; white-space: nowrap; }}

#sidebar-foot {{
  padding: 10px 14px;
  border-top: 1px solid var(--border);
  font-size: .72rem; color: var(--muted); text-align: center;
}}

/* main stage */
#stage {{
  flex: 1; display: flex; flex-direction: column; position: relative; overflow: hidden;
}}

/* image area */
#img-wrap {{
  flex: 1; display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden; background: #000;
}}
#main-img {{
  max-width: 100%; max-height: 100%;
  object-fit: contain;
  transition: opacity .5s ease-in-out;
  user-select: none;
}}
#main-img.fade {{ opacity: 0; }}

/* side arrows */
.arrow-btn {{
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 52px; height: 52px;
  background: rgba(0,0,0,.55);
  border: 1px solid var(--border);
  border-radius: 50%;
  color: var(--text); font-size: 1.4rem;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background var(--trans), opacity var(--trans);
  opacity: 0;
  z-index: 5;
}}
#img-wrap:hover .arrow-btn {{ opacity: 1; }}
.arrow-btn:hover {{ background: rgba(201,168,76,.25); }}
#btn-prev {{ left: 14px; }}
#btn-next {{ right: 14px; }}

/* thumbnail strip */
#thumb-strip {{
  height: 86px; min-height: 86px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex; align-items: center;
  overflow-x: auto; overflow-y: hidden;
  gap: 4px; padding: 6px 10px;
  scroll-behavior: smooth;
}}
#thumb-strip::-webkit-scrollbar {{ height: 4px; }}
#thumb-strip::-webkit-scrollbar-track {{ background: transparent; }}
#thumb-strip::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

.thumb {{
  flex-shrink: 0;
  width: 68px; height: 68px;
  object-fit: cover;
  border: 2px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  opacity: .55;
  transition: opacity var(--trans), border-color var(--trans), transform var(--trans);
}}
.thumb:hover {{ opacity: .85; transform: scale(1.05); }}
.thumb.active {{ border-color: var(--accent); opacity: 1; }}

/* info bar — hidden, info moved into note overlay */
#info-bar {{ display: none; }}

/* controls bar */
#ctrl-bar {{
  height: 42px; min-height: 42px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  gap: 10px; padding: 0 12px;
}}
.ctrl-btn {{
  background: transparent; border: 1px solid var(--border);
  color: var(--text); border-radius: var(--radius);
  padding: 4px 12px; font-size: .78rem; cursor: pointer;
  transition: background var(--trans), border-color var(--trans);
  font-family: inherit;
}}
.ctrl-btn:hover {{ background: var(--panel); border-color: var(--accent); }}
.ctrl-btn.active {{ background: var(--accent2); border-color: var(--accent); color: #fff; }}

#speed-label {{ font-size: .72rem; color: var(--muted); }}
#speed-sel {{
  background: var(--panel); border: 1px solid var(--border);
  color: var(--text); border-radius: var(--radius);
  padding: 3px 6px; font-size: .78rem; cursor: pointer;
  font-family: inherit;
}}

/* fullscreen overlay */
#fs-overlay {{
  display: none; position: fixed; inset: 0;
  background: #000;
  z-index: 100; align-items: center; justify-content: center;
  flex-direction: column;
}}
#fs-overlay.visible {{ display: flex; }}
#fs-img {{
  max-width: calc(100vw - 160px);
  max-height: calc(100vh - 140px);
  object-fit: contain;
  transition: opacity .5s ease-in-out;
  border: 4px solid #FFD700;
  border-radius: 4px;
  box-shadow: 0 0 24px rgba(255,215,0,.55);
}}
#fs-img.fade {{ opacity: 0; }}
#fs-close {{
  position: fixed; top: 16px; right: 20px;
  background: rgba(0,0,0,.6); border: 1px solid var(--border);
  color: var(--text); font-size: 1.4rem; width: 38px; height: 38px;
  border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;
  z-index: 102;
}}
.fs-arrow {{
  position: fixed; top: 50%; transform: translateY(-50%);
  width: 64px; height: 64px;
  background: #2c3e50;
  border: 2px solid #FFD700;
  border-radius: 50%;
  color: #fff; font-size: 2.2rem; font-weight: bold;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .2s, box-shadow .2s, transform .15s;
  opacity: .92; z-index: 101;
  box-shadow: 0 0 14px rgba(44,62,80,.7);
  user-select: none;
}}
.fs-arrow:hover {{
  background: #1a252f;
  box-shadow: 0 0 22px rgba(255,215,0,.55);
  transform: translateY(-50%) scale(1.1);
}}
#fs-prev {{ left: 18px; }}
#fs-next {{ right: 18px; }}

/* fullscreen auto-play bar */
#fs-ctrl {{
  position: fixed; bottom: 0; left: 0; right: 0;
  background: rgba(44,62,80,.88);
  border-top: 2px solid #3498db;
  display: flex; align-items: center; justify-content: center;
  gap: 12px; padding: 10px 16px;
  z-index: 102;
  backdrop-filter: blur(6px);
  transition: opacity .5s ease, transform .5s ease;
}}
#fs-ctrl.hidden {{
  opacity: 0;
  transform: translateY(100%);
  pointer-events: none;
}}
.fs-ctrl-btn {{
  background: #3498db; border: none; color: #fff;
  border-radius: 5px; padding: 6px 16px;
  font-size: .82rem; cursor: pointer; font-family: inherit;
  transition: background .2s;
}}
.fs-ctrl-btn:hover  {{ background: #2980b9; }}
.fs-ctrl-btn.active {{ background: #FFD700; color: #2c3e50; font-weight: bold; }}
#fs-speed {{
  background: #34495e; border: 1px solid #3498db;
  color: #fff; border-radius: 4px;
  padding: 4px 8px; font-size: .8rem; font-family: inherit; cursor: pointer;
}}
#fs-pos {{
  color: #ecf0f1; font-size: .8rem; min-width: 70px; text-align: center;
}}

/* notes overlay */
#note-overlay {{
  display: none;
  position: absolute; bottom: 0; left: 0; right: 0;
  background: rgba(44,62,80,.82);
  color: #ecf0f1;
  padding: 8px 20px;
  line-height: 1.5;
  text-align: center;
  border-top: 2px solid #FFD700;
  pointer-events: none;
  z-index: 6;
}}
#note-overlay .ov-meta {{
  font-size: .75rem; color: var(--accent); margin-bottom: 2px;
}}
#note-overlay .ov-text {{
  font-size: .88rem; color: #ecf0f1;
}}
#fs-note-overlay {{
  display: none;
  background: rgba(44,62,80,.88);
  color: #ecf0f1;
  padding: 8px 20px;
  font-size: .88rem; line-height: 1.5;
  text-align: center;
  border-top: 2px solid #FFD700;
  width: 100%;
  margin-top: 6px;
}}

/* responsive: hide sidebar toggle on mobile */
#toggle-sidebar {{
  display: none;
  position: fixed; top: 10px; left: 10px; z-index: 20;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text); width: 34px; height: 34px; border-radius: 4px;
  cursor: pointer; align-items: center; justify-content: center; font-size: 1.1rem;
}}
@media (max-width: 640px) {{
  #toggle-sidebar {{ display: flex; }}
  #sidebar {{ position: fixed; left: 0; top: 0; height: 100%; transform: translateX(-100%); }}
  #sidebar.open {{ transform: translateX(0); }}
}}
</style>
</head>
<body>

<div id="app">

  <!-- ── sidebar ── -->
  <nav id="sidebar">
    <div id="sidebar-head">
      <h1>Photo Archive</h1>
      <h2 id="show-title">{title}</h2>
    </div>
    <div id="gallery-list">
      <!-- populated by JS -->
    </div>
    <div id="sidebar-foot">
      {total_images} photos · {gallery_count} galleries<br>
      {generated}
    </div>
  </nav>

  <!-- ── main stage ── -->
  <main id="stage">

    <div id="img-wrap">
      <img id="main-img" src="" alt="" draggable="false">
      <button class="arrow-btn" id="btn-prev" title="Previous (←)">&#8249;</button>
      <button class="arrow-btn" id="btn-next" title="Next (→)">&#8250;</button>
      <div id="note-overlay"></div>
    </div>

    <div id="thumb-strip">
      <!-- populated by JS -->
    </div>

    <div id="info-bar">
      <span class="info-gallery" id="info-gallery"></span>
      <span class="info-file"    id="info-file"></span>
      <span class="info-pos"     id="info-pos"></span>
    </div>

    <div id="ctrl-bar">
      <button class="ctrl-btn" id="btn-first"  title="First image">&#8676;</button>
      <button class="ctrl-btn" id="btn-play"   title="Play/Pause slideshow">&#9654; Play</button>
      <button class="ctrl-btn" id="btn-last"   title="Last image">&#8677;</button>
      <span id="speed-label">Delay:</span>
      <select id="speed-sel">
        <option value="2000">2 s</option>
        <option value="4000" selected>4 s</option>
        <option value="6000">6 s</option>
        <option value="10000">10 s</option>
        <option value="15000">15 s</option>
      </select>
      <button class="ctrl-btn" id="btn-notes" title="Toggle notes (N)">&#128221; Notes</button>
      <button class="ctrl-btn" id="btn-shuffle" title="Shuffle gallery">&#8654; Shuffle</button>
      <button class="ctrl-btn" id="btn-fs"      title="Fullscreen (F)">&#x26F6; Full</button>
    </div>

  </main>
</div>

<!-- fullscreen overlay -->
<div id="fs-overlay">
  <button id="fs-close" title="Close (Esc)">&#x2715;</button>
  <button class="fs-arrow" id="fs-prev" title="Previous (←)">&#8249;</button>
  <img id="fs-img" src="" alt="">
  <button class="fs-arrow" id="fs-next" title="Next (→)">&#8250;</button>
  <div id="fs-note-overlay"></div>
  <div id="fs-ctrl">
    <button class="fs-ctrl-btn" id="fs-play">&#9654; Play</button>
    <span style="color:#bdc3c7;font-size:.8rem;">Delay:</span>
    <select id="fs-speed">
      <option value="2000">2 s</option>
      <option value="4000" selected>4 s</option>
      <option value="6000">6 s</option>
      <option value="10000">10 s</option>
      <option value="15000">15 s</option>
    </select>
    <span id="fs-pos"></span>
  </div>
</div>

<button id="toggle-sidebar" title="Toggle sidebar">&#9776;</button>

<script>
/* ── data ─────────────────────────────────────────────────────────────────── */
const DATA = {data_json};

/* ── state ────────────────────────────────────────────────────────────────── */
let galIdx   = 0;   // current gallery index
let imgIdx   = 0;   // current image index within gallery
let playing  = false;
let timer    = null;
let fsOpen   = false;
let notesVisible = true;

/* ── DOM refs ─────────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const galList   = $("gallery-list");
const mainImg   = $("main-img");
const thumbStrip= $("thumb-strip");
const infoGal   = $("info-gallery");
const infoFile  = $("info-file");
const infoPos   = $("info-pos");
const btnPlay   = $("btn-play");
const speedSel  = $("speed-sel");
const fsOverlay = $("fs-overlay");
const fsImg     = $("fs-img");
const sidebar   = $("sidebar");

/* ── build sidebar ────────────────────────────────────────────────────────── */
function buildSidebar() {{
  galList.innerHTML = "";
  DATA.galleries.forEach((g, i) => {{
    const div = document.createElement("div");
    div.className = "gal-item" + (i === galIdx ? " active" : "");
    div.dataset.idx = i;
    div.innerHTML = `<span class="gal-label">${{g.label}}</span>
                     <span class="gal-count">${{g.images.length}}</span>`;
    div.addEventListener("click", () => switchGallery(i));
    galList.appendChild(div);
  }});
}}

/* ── build thumbnail strip ────────────────────────────────────────────────── */
function buildThumbs() {{
  thumbStrip.innerHTML = "";
  const gal = DATA.galleries[galIdx];
  gal.images.forEach((item, i) => {{
    const img = document.createElement("img");
    img.className = "thumb" + (i === imgIdx ? " active" : "");
    img.src = resolveImg(item.src);
    img.alt = item.src;
    img.loading = "lazy";
    img.addEventListener("click", () => goTo(i));
    thumbStrip.appendChild(img);
  }});
}}

/* ── resolve image path ───────────────────────────────────────────────────── */
function resolveImg(relPath) {{
  // When opened from media_root we need to reference siblings
  // The HTML lives one level up from media_root by default;
  // adjust MEDIA_PREFIX if you move slideshow.html elsewhere.
  return MEDIA_PREFIX + relPath;
}}

const MEDIA_PREFIX = "{media_prefix}";

/* ── display an image ─────────────────────────────────────────────────────── */
function showImage(idx, animate=true) {{
  const gal = DATA.galleries[galIdx];
  if (!gal) return;
  idx = ((idx % gal.images.length) + gal.images.length) % gal.images.length;
  imgIdx = idx;

  const item  = gal.images[imgIdx];
  const src   = resolveImg(item.src);
  const fname = item.src.split("/").pop();
  const note  = item.note || "";

  // Cross-image fade: opacity 1 → 0 → swap → 0 → 1. The timeout matches the
  // CSS transition duration (.5s) so the image is fully invisible at the
  // moment of swap.
  const FADE_MS = 500;
  if (animate) {{
    mainImg.classList.add("fade");
    if (fsOpen) fsImg.classList.add("fade");
    setTimeout(() => {{
      mainImg.src = src;
      mainImg.onload  = () => mainImg.classList.remove("fade");
      mainImg.onerror = () => mainImg.classList.remove("fade");
      if (fsOpen) {{
        fsImg.src = src;
        fsImg.onload  = () => fsImg.classList.remove("fade");
        fsImg.onerror = () => fsImg.classList.remove("fade");
      }}
    }}, FADE_MS);
  }} else {{
    mainImg.src = src;
    if (fsOpen) fsImg.src = src;
  }}

  // fullscreen position indicator (image src is handled above)
  if (fsOpen) {{
    updateFsPos();
  }}

  // main note overlay — always show with gallery/file/note combined
  const noteEl = $("note-overlay");
  noteEl.innerHTML = notesVisible
    ? `<div class="ov-meta">${{gal.label}} &nbsp;·&nbsp; ${{fname}} &nbsp;·&nbsp; ${{imgIdx+1}} / ${{gal.images.length}}</div>`
      + (note ? `<div class="ov-text">${{note}}</div>` : "")
    : "";
  noteEl.style.display = notesVisible ? "block" : "none";

  // fullscreen note overlay — below image. Use innerHTML so notes can
  // contain simple HTML (e.g. <br>) like the main overlay does.
  const fsNoteEl = $("fs-note-overlay");
  if (fsNoteEl) {{
    fsNoteEl.innerHTML = note;
    fsNoteEl.style.display = (note && notesVisible) ? "block" : "none";
  }}

  // update thumbs
  thumbStrip.querySelectorAll(".thumb").forEach((t, i) => {{
    t.classList.toggle("active", i === imgIdx);
  }});
  // scroll active thumb into view
  const activeTh = thumbStrip.children[imgIdx];
  if (activeTh) activeTh.scrollIntoView({{behavior:"smooth", block:"nearest", inline:"center"}});

  // info bar (hidden but keep for compatibility)
  infoGal.textContent  = gal.label;
  infoFile.textContent = fname;
  infoPos.textContent  = `${{imgIdx+1}} / ${{gal.images.length}}`;
}}

/* ── navigation ───────────────────────────────────────────────────────────── */
function goTo(i)    {{ showImage(i); }}
function goNext()   {{ showImage(imgIdx + 1); }}
function goPrev()   {{ showImage(imgIdx - 1); }}
function goFirst()  {{ showImage(0); }}
function goLast()   {{ showImage(DATA.galleries[galIdx].images.length - 1); }}

function switchGallery(i) {{
  galIdx = i;
  imgIdx = 0;
  buildSidebar();
  buildThumbs();
  showImage(0, false);
  // scroll sidebar item into view
  const active = galList.querySelector(".gal-item.active");
  if (active) active.scrollIntoView({{behavior:"smooth", block:"nearest"}});
}}

/* ── autoplay ─────────────────────────────────────────────────────────────── */
/* One autoplay state, two button views. The fullscreen play button and the
   main play button are simply mirrors of the same `playing` flag — there's
   no separate fs timer that could drift or double-fire alongside the main
   one. Same idea for the two speed dropdowns: they're kept in sync, and
   scheduleNext() reads whichever is canonical (speedSel). */
function syncPlayButtons() {{
  const fsPlay = $("fs-play");
  if (playing) {{
    btnPlay.textContent = "⏸ Pause";
    btnPlay.classList.add("active");
    if (fsPlay) {{ fsPlay.textContent = "⏸ Pause"; fsPlay.classList.add("active"); }}
  }} else {{
    btnPlay.textContent = "▶ Play";
    btnPlay.classList.remove("active");
    if (fsPlay) {{ fsPlay.textContent = "▶ Play"; fsPlay.classList.remove("active"); }}
  }}
}}
function startPlay() {{
  playing = true;
  syncPlayButtons();
  scheduleNext();
}}
function stopPlay() {{
  playing = false;
  clearTimeout(timer);
  syncPlayButtons();
}}
function togglePlay() {{ playing ? stopPlay() : startPlay(); }}
function scheduleNext() {{
  clearTimeout(timer);
  const delay = parseInt(speedSel.value, 10);
  timer = setTimeout(() => {{
    if (!playing) return;
    const gal = DATA.galleries[galIdx];
    const nextIdx = imgIdx + 1;
    if (nextIdx >= gal.images.length) {{
      // advance to next gallery
      const nextGal = (galIdx + 1) % DATA.galleries.length;
      switchGallery(nextGal);
    }} else {{
      showImage(nextIdx);
    }}
    scheduleNext();
  }}, delay);
}}

/* ── shuffle current gallery ──────────────────────────────────────────────── */
function shuffleGallery() {{
  const gal = DATA.galleries[galIdx];
  for (let i = gal.images.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [gal.images[i], gal.images[j]] = [gal.images[j], gal.images[i]];
  }}
  buildThumbs();
  showImage(0);
}}

/* ── fullscreen overlay ───────────────────────────────────────────────────── */
function updateFsPos() {{
  const gal = DATA.galleries[galIdx];
  $("fs-pos").textContent = gal ? `${{imgIdx+1}} / ${{gal.images.length}}` : "";
}}
function openFs() {{
  fsOpen = true;
  const item = DATA.galleries[galIdx].images[imgIdx];
  fsImg.src = resolveImg(item.src);
  const note = item.note || "";
  const fsNoteEl = $("fs-note-overlay");
  if (fsNoteEl) {{
    fsNoteEl.innerHTML = note;
    fsNoteEl.style.display = (note && notesVisible) ? "block" : "none";
  }}
  // Make sure the fullscreen UI mirrors the canonical autoplay state.
  const fsSpeed = $("fs-speed");
  if (fsSpeed) fsSpeed.value = speedSel.value;
  syncPlayButtons();
  fsOverlay.classList.add("visible");
  updateFsPos();
  showFsCtrl();
}}
function closeFs() {{
  fsOpen = false;
  fsOverlay.classList.remove("visible");
  // Autoplay is unified — closing fullscreen does NOT stop the slideshow.
  // If the user wants to stop, they press the (now-mirrored) Play/Pause button.
}}

/* ── keyboard ─────────────────────────────────────────────────────────────── */
document.addEventListener("keydown", e => {{
  if (e.target.tagName === "SELECT") return;
  switch (e.key) {{
    case "ArrowRight": case "ArrowDown":  goNext();       break;
    case "ArrowLeft":  case "ArrowUp":    goPrev();       break;
    case " ":          togglePlay();  e.preventDefault(); break;
    case "f": case "F": fsOpen ? closeFs() : openFs();   break;
    case "n": case "N": toggleNotes();                    break;
    case "Escape":     closeFs();                         break;
    case "Home":       goFirst();                         break;
    case "End":        goLast();                          break;
  }}
}});

/* ── mouse click on stage image → fullscreen ─────────────────────────────── */
mainImg.addEventListener("dblclick", openFs);

/* ── button wiring ────────────────────────────────────────────────────────── */
$("btn-prev").addEventListener("click", goPrev);
$("btn-next").addEventListener("click", goNext);
$("btn-first").addEventListener("click", goFirst);
$("btn-last").addEventListener("click", goLast);
$("btn-play").addEventListener("click", togglePlay);
$("btn-notes").addEventListener("click", toggleNotes);

function toggleNotes() {{
  notesVisible = !notesVisible;
  $("btn-notes").classList.toggle("active", notesVisible);
  // re-render overlays by re-showing current image
  showImage(imgIdx, false);
}}
$("btn-shuffle").addEventListener("click", shuffleGallery);
$("btn-fs").addEventListener("click", openFs);
$("fs-close").addEventListener("click", closeFs);
$("fs-play").addEventListener("click", togglePlay);   // mirrors the main play button
$("fs-prev").addEventListener("click", () => {{ goPrev(); }});
$("fs-next").addEventListener("click", () => {{ goNext(); }});
$("toggle-sidebar").addEventListener("click", () => sidebar.classList.toggle("open"));

/* Keep the two speed dropdowns in sync. Changing the delay in either view
   updates the other so the autoplay rate is consistent no matter where the
   user looked last. */
const fsSpeedSel = $("fs-speed");
if (fsSpeedSel) {{
  speedSel.addEventListener("change", () => {{
    fsSpeedSel.value = speedSel.value;
    if (playing) scheduleNext();  // apply new rate immediately
  }});
  fsSpeedSel.addEventListener("change", () => {{
    speedSel.value = fsSpeedSel.value;
    if (playing) scheduleNext();
  }});
}}

/* ── touch swipe ──────────────────────────────────────────────────────────── */
let touchX = null;
$("img-wrap").addEventListener("touchstart", e => {{ touchX = e.touches[0].clientX; }});
$("img-wrap").addEventListener("touchend",   e => {{
  if (touchX === null) return;
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 40) {{ dx < 0 ? goNext() : goPrev(); }}
  touchX = null;
}});

/* ── fullscreen control bar auto-hide ─────────────────────────────────────── */
let fsHideTimer = null;
function showFsCtrl() {{
  $("fs-ctrl").classList.remove("hidden");
  clearTimeout(fsHideTimer);
  fsHideTimer = setTimeout(() => $("fs-ctrl").classList.add("hidden"), 2500);
}}
fsOverlay.addEventListener("mousemove", showFsCtrl);
fsOverlay.addEventListener("touchstart", showFsCtrl);
$("fs-ctrl").addEventListener("mouseenter", () => clearTimeout(fsHideTimer));
$("fs-ctrl").addEventListener("mouseleave", () => {{
  fsHideTimer = setTimeout(() => $("fs-ctrl").classList.add("hidden"), 1200);
}});
buildSidebar();
buildThumbs();
showImage(0, false);
$("btn-notes").classList.add("active");
</script>
</body>
</html>
"""


def translate_photo_config(data: dict) -> dict:
    """
    Convert photo_config.json format (used by photos_exposition.py) into the
    slideshow's internal config format.  Called automatically when the input
    file contains a 'site_info' key.

    Image paths are stored relative to a media_root so the generated
    slideshow.html stays portable when the folder is moved or shared.

    Two strategies, picked automatically:

    1. **Website-rooted paths** (preferred).  When the config carries an
       ``output_directory`` (because photos_exposition.py wrote it) and the
       per-gallery photo copies actually exist under
       ``<output_directory>/photos/<gallery_id>/<filename>``, image src
       values are stored as ``photos/<gallery_id>/<filename>`` with
       media_root set to ``output_directory``.  Result: dropping
       slideshow.html into the website folder yields a fully self-contained
       site — the entire ``website/`` directory can be moved, zipped, or
       hosted as a single unit.

    2. **Source-directory paths** (fallback).  When the website copies
       aren't there yet (e.g. you ran ``build`` before
       ``photos_exposition.py``), paths point at the original
       ``source_directory`` for each gallery, anchored on the common
       ancestor of all source dirs.
    """
    site   = data.get("site_info", {})
    title  = site.get("title", "Photo Slideshow")

    # First pass: collect (src_dir, id, filename, note, label) tuples so we
    # can decide which path strategy to use, then build paths accordingly.
    raw_galleries = []
    for g in data.get("galleries", []):
        gid         = g.get("id", "")
        src_dir_raw = g.get("source_directory", "")
        src_dir     = Path(src_dir_raw).resolve() if src_dir_raw else Path(".").resolve()
        photos      = g.get("photos",  [])
        notes       = g.get("notes",   {})
        label       = g.get("name", gid or "Gallery")

        entries = [(filename, notes.get(filename, "")) for filename in photos]
        if entries:
            raw_galleries.append({
                "label":   label,
                "id":      gid,
                "src_dir": src_dir,
                "entries": entries,
            })

    # ── Try strategy 1: website-rooted paths ────────────────────────────
    output_dir_raw = data.get("output_directory")
    website_root   = Path(output_dir_raw).resolve() if output_dir_raw else None

    use_website_paths = bool(website_root and raw_galleries)
    if use_website_paths:
        for rg in raw_galleries:
            if not rg["id"]:
                use_website_paths = False
                break
            for filename, _ in rg["entries"]:
                copy_path = website_root / "photos" / rg["id"] / filename
                if not copy_path.exists():
                    use_website_paths = False
                    break
            if not use_website_paths:
                break

    if use_website_paths:
        galleries = [
            {
                "label":  rg["label"],
                "images": [
                    {"src": f"photos/{rg['id']}/{filename}", "note": note}
                    for filename, note in rg["entries"]
                ],
            }
            for rg in raw_galleries
        ]
        return {
            "title":      title,
            "media_root": str(website_root).replace("\\", "/"),
            "generated":  "",
            "galleries":  galleries,
            "total":      sum(len(g["images"]) for g in galleries),
        }

    # ── Strategy 2: source-directory paths (fallback) ───────────────────
    all_src_dirs = [rg["src_dir"] for rg in raw_galleries]
    abs_paths = False
    if all_src_dirs:
        try:
            media_root = Path(os.path.commonpath([str(p) for p in all_src_dirs]))
        except ValueError:
            media_root = Path("/")
            abs_paths = True
    else:
        media_root = Path(".").resolve()

    galleries = []
    for rg in raw_galleries:
        images = []
        for filename, note in rg["entries"]:
            full_path = rg["src_dir"] / filename
            if abs_paths:
                src = str(full_path).replace("\\", "/")
            else:
                try:
                    src = str(full_path.relative_to(media_root)).replace("\\", "/")
                except ValueError:
                    src = str(full_path).replace("\\", "/")
            images.append({"src": src, "note": note})
        galleries.append({"label": rg["label"], "images": images})

    result = {
        "title":      title,
        "media_root": str(media_root).replace("\\", "/"),
        "generated":  "",
        "galleries":  galleries,
        "total":      sum(len(g["images"]) for g in galleries),
    }
    if abs_paths:
        result["_abs_paths"] = True
    return result


def build_html(config: dict, output_path: Path, media_dir_override: Path | None = None):
    """Generate the standalone HTML slideshow."""
    title       = html_mod.escape(config.get("title", "Photo Slideshow"))
    galleries   = config.get("galleries", [])
    total       = config.get("total", sum(len(g["images"]) for g in galleries))
    generated   = config.get("generated", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Figure out the relative path prefix from the HTML file to the media root.
    # Default: the HTML file sits one directory above the media folder, which
    # means we reference images as  media/<relpath>.
    media_root = media_dir_override or Path(config.get("media_root", "."))
    html_dir   = output_path.parent.resolve()

    if config.get("_abs_paths"):
        media_prefix = ""
    else:
        try:
            rel = os.path.relpath(media_root.resolve(), html_dir)
            media_prefix = rel.replace("\\", "/") + "/"
            if media_prefix == "./":
                media_prefix = ""
        except ValueError:
            media_prefix = str(media_root.resolve()).replace("\\", "/") + "/"

    data_json = json.dumps(
        {
            "title":     config.get("title", "Photo Slideshow"),
            "galleries": galleries,
        },
        ensure_ascii=False,
        indent=None,
    )

    html = HTML_TEMPLATE.format(
        title         = title,
        total_images  = f"{total:,}",
        gallery_count = len(galleries),
        generated     = generated,
        media_prefix  = media_prefix,
        data_json     = data_json,
    )

    output_path.write_text(html, encoding="utf-8")
    print(f"Slideshow : {output_path}")
    print(f"  Open in your browser – no web server needed.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def add_common_args(p, include_output=True):
    p.add_argument("--media-dir", default="./media",
                   help="Root folder containing gallery sub-folders (default: ./media)")
    p.add_argument("--title", default="Rose Family Photos",
                   help="Slideshow title")
    p.add_argument("--sort", choices=["name", "date", "random"], default="name",
                   help="Image sort order within each gallery (default: name)")
    p.add_argument("--no-recursive", dest="recursive", action="store_false",
                   help="Do NOT descend into sub-directories")
    p.set_defaults(recursive=True)
    if include_output:
        p.add_argument("--output", default=None,
                       help="Output file path")


def main():
    parser = argparse.ArgumentParser(
        description="GRASP Photo Slideshow Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Scan media dir → photo_config.json")
    add_common_args(p_scan)
    p_scan.set_defaults(output="photo_config.json")

    # build
    p_build = sub.add_parser("build", help="photo_config.json → slideshow.html")
    p_build.add_argument("--config", default="photo_config.json",
                         help="Config JSON produced by scan (default: photo_config.json)")
    p_build.add_argument("--output", default=None,
                         help="Output HTML file (default: <media_root>/../website/slideshow.html, "
                              "falling back to ./slideshow.html)")

    # all
    p_all = sub.add_parser("all", help="Scan then build in one step")
    add_common_args(p_all)
    p_all.add_argument("--config-out", default="photo_config.json",
                       help="Where to write the interim config (default: photo_config.json)")

    args = parser.parse_args()

    if args.cmd == "scan":
        cmd_scan(args)

    elif args.cmd == "build":
        cfg_path = Path(args.config)
        if not cfg_path.is_file():
            sys.exit(f"ERROR: config not found: {cfg_path}")
        config = json.loads(cfg_path.read_text())
        if "site_info" in config:
            print("Detected photo_config.json format — translating...")
            config = translate_photo_config(config)
        html_out = resolve_html_output(args.output, config.get("media_root"))
        build_html(config, html_out)

    elif args.cmd == "all":
        # Decide HTML output before scan rewrites args.output for the JSON step.
        html_out = resolve_html_output(args.output, args.media_dir)
        args.output = args.config_out      # scan writes the JSON here
        config = cmd_scan(args)
        build_html(config, html_out, media_dir_override=Path(args.media_dir))
        print(f"\nDone. Open {html_out} in any browser.")


def resolve_html_output(explicit: str | None, media_root_hint) -> Path:
    """
    Decide where slideshow.html should land.

    Priority:
      1. --output if the user passed one (explicit wins, always).
      2. <media_root>/../website/slideshow.html — pairs with the typical
         project_gallery/user_files + project_gallery/website layout.
      3. ./slideshow.html as a last-resort fallback.

    The parent directory is created if needed.
    """
    if explicit:
        out = Path(explicit)
    else:
        out = None
        if media_root_hint:
            media_root = Path(media_root_hint).resolve()
            candidate = media_root.parent / "website" / "slideshow.html"
            if candidate.parent.exists() or media_root.parent.exists():
                out = candidate
        if out is None:
            out = Path("slideshow.html").resolve()

    out.parent.mkdir(parents=True, exist_ok=True)
    return out


if __name__ == "__main__":
    main()
