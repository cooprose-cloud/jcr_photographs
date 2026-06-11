#!/usr/bin/env python3
"""
csv_to_config.py
----------------
Builds user_files/photo_config.json from two CSV files:

  site_settings.csv  — one row per setting (field, value)
  photos.csv         — one row per photo

This avoids hand-editing JSON and eliminates missing-comma / missing-quote errors.

Usage:
    python3 csv_to_config.py
    python3 csv_to_config.py --photos my_photos.csv --site my_site.csv
    python3 csv_to_config.py --output user_files/photo_config.json
    python3 csv_to_config.py --sample   # write sample CSV files and exit

photos.csv columns (header row required):
    gallery_id        short id, no spaces  e.g.  family_reunion
    gallery_name      display name         e.g.  Family Reunion
    gallery_desc      optional description (can be blank)
    source_directory  full path to photo folder
    photo_file        filename only        e.g.  IMG_001.jpg
    note              caption (can be blank)
    in_slideshow      yes or no
    seq               OPTIONAL — integer that sets photo order WITHIN its
                      gallery. Number sparsely (10, 20, 30...) so you can
                      insert photos later without renumbering. If the column
                      is absent or blank for every row, CSV row order is used.
                      Blank rows in a partially-numbered gallery are placed
                      after the numbered ones.
    notes_title       OPTIONAL — heading for the layer-4 "Read more" page
    notes_body        OPTIONAL — body text for the layer-4 "Read more" page
                      Use literal \\n\\n for paragraph breaks, or quote the
                      cell in your spreadsheet and use real newlines.
                      If a sidecar .md file exists next to the photo, it
                      takes precedence over this column.

site_settings.csv columns:
    field             setting name
    value             setting value

See sample files written by --sample for a complete example.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from collections import OrderedDict

# The project root is the folder that contains this script's parent — i.e. the
# directory holding system_files/ and user_files/. Relative paths in the CSVs
# (output_directory, source_directory) are interpreted relative to THIS root,
# not the shell's current directory, and are stored in the config as absolute
# paths. That way the build works no matter what folder the tools are launched
# from. (See the "missing tiles" failure mode: relative paths + wrong cwd.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _absolutize(path_str: str) -> str:
    """Return an absolute version of a path string from the CSVs.

    - Blank stays blank.
    - '~' is expanded.
    - Absolute paths are returned unchanged (just normalized).
    - Relative paths are resolved against PROJECT_ROOT, so 'user_files/pets'
      and 'website' resolve correctly regardless of the current directory.
    """
    s = (path_str or "").strip()
    if not s:
        return s
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return str(p.resolve())

# ── Sample CSV content ────────────────────────────────────────────────────────

SAMPLE_SITE = """\
field,value
title,My Photo Gallery
subtitle,A collection of photographs
overview,Welcome to my gallery. Browse the collections below.
photographer_name,Your Name
date_published,2026
copyright_year,2026
output_directory,./output
thumbnail_width,300
thumbnail_height,300
thumbnail_display_size,280
max_galleries,
slideshow_interval_seconds,5
slideshow_show_captions,yes
"""

SAMPLE_PHOTOS = """\
gallery_id,gallery_name,gallery_desc,source_directory,photo_file,note,in_slideshow,seq,notes_title,notes_body
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_001.jpg,Aunt Clara and Uncle Bob,yes,10,Aunt Clara's Last Reunion,"Clara had been ill for some months by the time this photograph was taken.\\n\\nUncle Bob drove her down from Vermont so she could see everyone one more time."
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_002.jpg,,no,20,,
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_003.jpg,The old farmhouse,no,30,,
vacation_1965,Summer Vacation 1965,,/Users/yourname/Photos/vacation65,scan001.jpg,Niagara Falls,yes,10,,
vacation_1965,Summer Vacation 1965,,/Users/yourname/Photos/vacation65,scan002.jpg,,no,20,,
"""

# ── Readers ───────────────────────────────────────────────────────────────────

def read_site_settings(path: Path) -> dict:
    """Read site_settings.csv into a flat dict."""
    settings = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            field = row.get("field", "").strip()
            value = row.get("value", "").strip()
            if field:
                settings[field] = value
    return settings


def read_photos(path: Path) -> list[dict]:
    """Read photos.csv, returning a list of clean row dicts."""
    rows = []
    required_cols = {"gallery_id", "gallery_name", "source_directory",
                     "photo_file", "in_slideshow"}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("ERROR: photos.csv appears to be empty.")
            sys.exit(1)
        missing = required_cols - set(reader.fieldnames)
        if missing:
            print(f"ERROR: photos.csv is missing required columns: {', '.join(sorted(missing))}")
            sys.exit(1)
        for i, row in enumerate(reader, start=2):   # start=2 because row 1 is header
            gallery_id = row.get("gallery_id", "").strip()
            photo_file = row.get("photo_file", "").strip()
            if not gallery_id or not photo_file:
                print(f"WARNING: row {i} skipped — gallery_id or photo_file is blank")
                continue
            rows.append({
                "gallery_id":        gallery_id,
                "gallery_name":      row.get("gallery_name",      "").strip(),
                "gallery_desc":      row.get("gallery_desc",       "").strip(),
                "source_directory":  row.get("source_directory",  "").strip(),
                "photo_file":        photo_file,
                "note":              row.get("note",              "").strip(),
                "in_slideshow":      row.get("in_slideshow", "no").strip().lower() == "yes",
                "seq":               row.get("seq",               "").strip(),
                "notes_title":       row.get("notes_title",       "").strip(),
                "notes_body":        row.get("notes_body",        "").strip(),
            })
    return rows


# ── Builder ───────────────────────────────────────────────────────────────────

def _apply_sequencing(rows_by_gallery: "OrderedDict[str, list[dict]]"):
    """Sort each gallery's rows by the integer 'seq' column, in place.

    Numbered rows come first in ascending order; rows with a blank or
    non-numeric seq keep their CSV order and are placed after the numbered
    ones. Duplicate or invalid values fall back to CSV order and a warning
    is printed.
    """
    for gid, grows in rows_by_gallery.items():
        parsed = []
        seen_seq = {}
        blanks = 0
        for row in grows:
            raw = row.get("seq", "").strip()
            if raw == "":
                blanks += 1
                seqval = None
            else:
                try:
                    seqval = int(raw)
                except ValueError:
                    print(f"WARNING: gallery '{gid}': seq value {raw!r} for "
                          f"'{row['photo_file']}' is not an integer — ignored")
                    seqval = None
                else:
                    if seqval in seen_seq:
                        print(f"WARNING: gallery '{gid}': duplicate seq {seqval} "
                              f"('{seen_seq[seqval]}' and '{row['photo_file']}') "
                              f"— order between them falls back to CSV order")
                    else:
                        seen_seq[seqval] = row["photo_file"]
            parsed.append((seqval, row["_csv_order"], row))

        if blanks and blanks != len(grows):
            print(f"WARNING: gallery '{gid}': {blanks} photo(s) have a blank seq "
                  f"— they will be ordered after the numbered photos")

        # Numbered rows first (by seq), then blanks; CSV order breaks ties.
        parsed.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0, t[1]))
        rows_by_gallery[gid] = [t[2] for t in parsed]


def build_config(settings: dict, rows: list[dict]) -> dict:
    """Assemble the photo_config.json structure."""

    def intval(key, default):
        try:
            return int(settings.get(key, default))
        except ValueError:
            print(f"WARNING: '{key}' in site_settings.csv is not a number — using {default}")
            return default

    max_galleries = settings.get("max_galleries", "").strip()

    config = {
        "output_directory": _absolutize(settings.get("output_directory", "./output")),
        "thumbnail_size": [
            intval("thumbnail_width",  300),
            intval("thumbnail_height", 300),
        ],
        "thumbnail_display_size": intval("thumbnail_display_size", 280),
        "max_galleries": int(max_galleries) if max_galleries else None,
        "site_info": {
            "title":              settings.get("title",              "My Photo Gallery"),
            "subtitle":           settings.get("subtitle",           ""),
            "overview":           settings.get("overview",           ""),
            "photographer_name":  settings.get("photographer_name",  ""),
            "date_published":     settings.get("date_published",     ""),
            "copyright_year":     settings.get("copyright_year",     ""),
        },
        "slideshow_config": {
            "interval_seconds": intval("slideshow_interval_seconds", 5),
            "show_captions":    settings.get("slideshow_show_captions", "yes").lower() == "yes",
        },
        "slideshow_photos": [],
        "galleries": [],
    }

    # Galleries appear in the order first encountered in the CSV
    gallery_order = list(OrderedDict.fromkeys(r["gallery_id"] for r in rows))

    # Group rows by gallery, preserving CSV order within each group
    rows_by_gallery = OrderedDict((gid, []) for gid in gallery_order)
    for idx, row in enumerate(rows):
        row["_csv_order"] = idx
        rows_by_gallery[row["gallery_id"]].append(row)

    # Optional per-gallery ordering via the 'seq' column. Only applied when at
    # least one row supplies a value; otherwise CSV row order is preserved.
    if any(r.get("seq", "").strip() for r in rows):
        _apply_sequencing(rows_by_gallery)

    gallery_meta  = {}   # id → {name, desc, source_directory}
    gallery_photos = {}  # id → [photo_file, ...]
    gallery_notes  = {}  # id → {photo_file: note}
    gallery_xnotes = {}  # id → {photo_file: {"title": ..., "body": ...}}

    for gid in gallery_order:
        grows = rows_by_gallery[gid]
        first = grows[0]
        gallery_meta[gid] = {
            "name":             first["gallery_name"],
            "description":      first["gallery_desc"],
            "source_directory": _absolutize(first["source_directory"]),
        }
        gallery_photos[gid] = []
        gallery_notes[gid]  = {}
        gallery_xnotes[gid] = {}

        for row in grows:
            pf = row["photo_file"]
            if pf not in gallery_photos[gid]:
                gallery_photos[gid].append(pf)
            gallery_notes[gid][pf] = row["note"]

            # Extended notes — only stored if notes_body is non-blank
            xbody  = row.get("notes_body",  "")
            xtitle = row.get("notes_title", "")
            if xbody:
                gallery_xnotes[gid][pf] = {
                    "title": xtitle,
                    "body":  xbody,
                }

            if row["in_slideshow"]:
                config["slideshow_photos"].append({
                    "gallery_id": gid,
                    "photo_file": pf,
                })

    for gid in gallery_order:
        meta = gallery_meta[gid]
        config["galleries"].append({
            "id":               gid,
            "name":             meta["name"],
            "description":      meta["description"],
            "source_directory": meta["source_directory"],
            "photos":           gallery_photos[gid],
            "notes":            gallery_notes[gid],
            "extended_notes":   gallery_xnotes[gid],
        })

    return config


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build photo_config.json from site_settings.csv and photos.csv")
    parser.add_argument(
        "--photos", "-p",
        default="user_files/photos.csv",
        help="Path to photos CSV (default: user_files/photos.csv)")
    parser.add_argument(
        "--site", "-s",
        default="user_files/site_settings.csv",
        help="Path to site settings CSV (default: user_files/site_settings.csv)")
    parser.add_argument(
        "--output", "-o",
        default="user_files/photo_config.json",
        help="Output path for config JSON (default: user_files/photo_config.json)")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Write sample CSV files to user_files/ and exit")
    args = parser.parse_args()

    # ── Write sample files ────────────────────────────────────────────────────
    if args.sample:
        out_dir = Path("user_files")
        out_dir.mkdir(exist_ok=True)
        site_path   = out_dir / "site_settings.csv"
        photos_path = out_dir / "photos.csv"
        site_path.write_text(SAMPLE_SITE,   encoding="utf-8")
        photos_path.write_text(SAMPLE_PHOTOS, encoding="utf-8")
        print(f"Sample files written:")
        print(f"  {site_path}")
        print(f"  {photos_path}")
        print(f"\nEdit them, then run:")
        print(f"  python3 csv_to_config.py")
        return

    # ── Read inputs ───────────────────────────────────────────────────────────
    site_path   = Path(args.site)
    photos_path = Path(args.photos)
    output_path = Path(args.output)

    for p in (site_path, photos_path):
        if not p.exists():
            print(f"ERROR: file not found: {p}")
            print(f"  Run  python3 csv_to_config.py --sample  to create sample files.")
            sys.exit(1)

    print(f"Reading site settings : {site_path}")
    settings = read_site_settings(site_path)

    print(f"Reading photos        : {photos_path}")
    rows = read_photos(photos_path)
    print(f"  {len(rows)} photo row(s) found")

    # ── Build and write ───────────────────────────────────────────────────────
    config = build_config(settings, rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    gcount = len(config["galleries"])
    pcount = sum(len(g["photos"]) for g in config["galleries"])
    scount = len(config["slideshow_photos"])
    print(f"\nWritten: {output_path}")
    print(f"  {gcount} gallery(s), {pcount} photo(s), {scount} slideshow pick(s)")
    print(f"\nNext step — validate:")
    print(f"  python3 validate_photo_config.py")


if __name__ == "__main__":
    main()
