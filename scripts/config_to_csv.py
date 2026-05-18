#!/usr/bin/env python3
"""
config_to_csv.py
----------------
Reads user_files/photo_config.json and exports two CSV files:

  user_files/site_settings.csv  — one row per site setting
  user_files/photos.csv         — one row per photo

This is the reverse of csv_to_config.py. Use it to bootstrap your
CSV workflow from an existing config, or to re-sync your CSVs after
hand-editing photo_config.json.

Usage:
    python3 config_to_csv.py
    python3 config_to_csv.py --config user_files/photo_config.json
    python3 config_to_csv.py --output-dir user_files
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_site_settings(config: dict, path: Path):
    site = config.get("site_info", {})
    thumb = config.get("thumbnail_size", [300, 300])
    slide = config.get("slideshow_config", {})
    max_g = config.get("max_galleries", "")

    rows = [
        ("title",                        site.get("title", "")),
        ("subtitle",                     site.get("subtitle", "")),
        ("overview",                     site.get("overview", "")),
        ("photographer_name",            site.get("photographer_name", "")),
        ("date_published",               site.get("date_published", "")),
        ("copyright_year",               site.get("copyright_year", "")),
        ("output_directory",             config.get("output_directory", "./output")),
        ("support_files_directory",      config.get("support_files_directory", "")),
        ("thumbnail_width",              thumb[0] if len(thumb) > 0 else 300),
        ("thumbnail_height",             thumb[1] if len(thumb) > 1 else 300),
        ("thumbnail_display_size",       config.get("thumbnail_display_size", 280)),
        ("max_galleries",                "" if max_g is None else max_g),
        ("slideshow_interval_seconds",   slide.get("interval_seconds", 5)),
        ("slideshow_show_captions",      "yes" if slide.get("show_captions", True) else "no"),
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["field", "value"])
        writer.writerows(rows)

    print(f"Written: {path}  ({len(rows)} settings)")


def write_photos(config: dict, path: Path):
    galleries = config.get("galleries", [])

    # Build an ordered map of slideshow picks so we can record each pick's
    # 1-based position in slideshow_photos. This survives the round-trip
    # back into JSON even if the photos.csv rows aren't reordered.
    slideshow_order = {}   # (gallery_id, photo_file) -> 1-based position
    for i, entry in enumerate(config.get("slideshow_photos", []), start=1):
        key = (entry.get("gallery_id", ""), entry.get("photo_file", ""))
        slideshow_order.setdefault(key, i)

    rows = []
    for gallery in galleries:
        gid   = gallery.get("id", "")
        gname = gallery.get("name", "")
        gdesc = gallery.get("description", "")
        gsrc  = gallery.get("source_directory", "")
        notes = gallery.get("notes", {})

        for photo_file in gallery.get("photos", []):
            note  = notes.get(photo_file, "")
            order = slideshow_order.get((gid, photo_file))
            in_slideshow = "yes" if order is not None else "no"
            rows.append({
                "gallery_id":       gid,
                "gallery_name":     gname,
                "gallery_desc":     gdesc,
                "source_directory": gsrc,
                "photo_file":       photo_file,
                "note":             note,
                "in_slideshow":     in_slideshow,
                "slideshow_order":  order if order is not None else "",
            })

    fieldnames = ["gallery_id", "gallery_name", "gallery_desc",
                  "source_directory", "photo_file", "note",
                  "in_slideshow", "slideshow_order"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    gcount = len(galleries)
    print(f"Written: {path}  ({gcount} gallery(s), {len(rows)} photo(s))")


def main():
    parser = argparse.ArgumentParser(
        description="Export photo_config.json to site_settings.csv and photos.csv")
    parser.add_argument(
        "--config", "-c",
        default="user_files/photo_config.json",
        help="Path to photo_config.json (default: user_files/photo_config.json)")
    parser.add_argument(
        "--output-dir", "-o",
        default="user_files",
        help="Directory to write CSV files into (default: user_files)")
    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir  = Path(args.output_dir)

    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {config_path}")
    config = load_config(config_path)

    write_site_settings(config, output_dir / "site_settings.csv")
    write_photos(config,        output_dir / "photos.csv")

    print("\nDone. Next steps:")
    print("  Edit the CSVs in your spreadsheet app, then run:")
    print("  python3 csv_to_config.py")


if __name__ == "__main__":
    main()
