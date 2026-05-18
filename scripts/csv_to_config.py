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
    slideshow_order   1-based position in the home-page slideshow
                      (blank for rows where in_slideshow is "no")

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
support_files_directory,
thumbnail_width,300
thumbnail_height,300
thumbnail_display_size,280
max_galleries,
slideshow_interval_seconds,5
slideshow_show_captions,yes
"""

SAMPLE_PHOTOS = """\
gallery_id,gallery_name,gallery_desc,source_directory,photo_file,note,in_slideshow,slideshow_order
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_001.jpg,Aunt Clara and Uncle Bob,yes,1
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_002.jpg,,no,
family_reunion,Family Reunion,Photos from the 1962 reunion,/Users/yourname/Photos/reunion,IMG_003.jpg,The old farmhouse,no,
vacation_1965,Summer Vacation 1965,,/Users/yourname/Photos/vacation65,scan001.jpg,Niagara Falls,yes,2
vacation_1965,Summer Vacation 1965,,/Users/yourname/Photos/vacation65,scan002.jpg,,no,
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
                # Optional slideshow_order column (added in Fix B). Missing
                # values are passed through as empty string and treated as
                # "no explicit order" by build_config.
                "slideshow_order":   row.get("slideshow_order", "").strip(),
            })
    return rows


# ── Builder ───────────────────────────────────────────────────────────────────

def build_config(settings: dict, rows: list[dict]) -> dict:
    """Assemble the photo_config.json structure."""

    def intval(key, default):
        try:
            return int(settings.get(key, default))
        except ValueError:
            print(f"WARNING: '{key}' in site_settings.csv is not a number — using {default}")
            return default

    max_galleries     = settings.get("max_galleries", "").strip()
    support_files_dir = settings.get("support_files_directory", "").strip()

    # Build the config dict incrementally so the top-level keys land in the
    # same order generate_photo_config.py emits them. This makes a clean
    # round-trip through CSV byte-equivalent, which keeps `diff` quiet and
    # version-control history meaningful.
    config = {}

    # site_info — field order matches generate_photo_config.py output
    # (title, subtitle, photographer_name, overview, date_published,
    # copyright_year). Picking a fixed order here also keeps diffs clean.
    config["site_info"] = {
        "title":              settings.get("title",              "My Photo Gallery"),
        "subtitle":           settings.get("subtitle",           ""),
        "photographer_name":  settings.get("photographer_name",  ""),
        "overview":           settings.get("overview",           ""),
        "date_published":     settings.get("date_published",     ""),
        "copyright_year":     settings.get("copyright_year",     ""),
    }

    config["output_directory"] = settings.get("output_directory", "./output")

    # Fix A: preserve support_files_directory when it has a value. Grouped
    # with output_directory because both are filesystem path settings.
    if support_files_dir:
        config["support_files_directory"] = support_files_dir

    config["thumbnail_size"] = [
        intval("thumbnail_width",  300),
        intval("thumbnail_height", 300),
    ]
    config["thumbnail_display_size"] = intval("thumbnail_display_size", 280)

    # Fix C: only emit max_galleries when the user actually set it.
    if max_galleries:
        try:
            config["max_galleries"] = int(max_galleries)
        except ValueError:
            print(f"WARNING: 'max_galleries' in site_settings.csv is not a number — omitting")

    config["slideshow_config"] = {
        "interval_seconds": intval("slideshow_interval_seconds", 5),
        "show_captions":    settings.get("slideshow_show_captions", "yes").lower() == "yes",
    }

    # galleries and slideshow_photos populate below. Initialize in the
    # order generate_photo_config.py uses (galleries then slideshow_photos)
    # so the round-trip diff stays clean.
    config["galleries"] = []
    config["slideshow_photos"] = []

    # Build galleries in the order first encountered
    gallery_order = list(OrderedDict.fromkeys(r["gallery_id"] for r in rows))
    gallery_meta  = {}   # id → {name, desc, source_directory}
    gallery_photos = {}  # id → [photo_file, ...]
    gallery_notes  = {}  # id → {photo_file: note}
    slideshow_picks = []  # [(slideshow_order, gallery_id, photo_file)]

    for row in rows:
        gid = row["gallery_id"]
        if gid not in gallery_meta:
            gallery_meta[gid] = {
                "name":             row["gallery_name"],
                "description":      row["gallery_desc"],
                "source_directory": row["source_directory"],
            }
            gallery_photos[gid] = []
            gallery_notes[gid]  = {}

        pf = row["photo_file"]
        if pf not in gallery_photos[gid]:
            gallery_photos[gid].append(pf)
        gallery_notes[gid][pf] = row["note"]

        if row["in_slideshow"]:
            # Fix B: respect slideshow_order if the column is present and
            # parseable. Rows with a missing or unparseable order sort to
            # the end in row-encounter order.
            order_raw = row.get("slideshow_order", "")
            try:
                order = int(order_raw) if str(order_raw).strip() else None
            except ValueError:
                order = None
            slideshow_picks.append((order, len(slideshow_picks), gid, pf))

    # Sort: explicit orders first (ascending), then anything without an order
    # in original row-encounter order. The secondary key (insertion index)
    # keeps the sort stable.
    slideshow_picks.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0, t[1]))
    config["slideshow_photos"] = [
        {"gallery_id": gid, "photo_file": pf}
        for _order, _idx, gid, pf in slideshow_picks
    ]

    for gid in gallery_order:
        meta = gallery_meta[gid]
        config["galleries"].append({
            "id":               gid,
            "name":             meta["name"],
            "description":      meta["description"],
            "source_directory": meta["source_directory"],
            "photos":           gallery_photos[gid],
            "notes":            gallery_notes[gid],
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
        # No trailing newline — matches generate_photo_config.py's output
        # so a clean round-trip is byte-equivalent.
        json.dump(config, f, indent=2, ensure_ascii=False)

    gcount = len(config["galleries"])
    pcount = sum(len(g["photos"]) for g in config["galleries"])
    scount = len(config["slideshow_photos"])
    print(f"\nWritten: {output_path}")
    print(f"  {gcount} gallery(s), {pcount} photo(s), {scount} slideshow pick(s)")
    print(f"\nNext step — validate:")
    print(f"  python3 validate_photo_config.py")


if __name__ == "__main__":
    main()
