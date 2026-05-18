#!/usr/bin/env python3
"""
validate_photo_config.py
------------------------
Validates user_files/photo_config.json for syntax errors and common
content problems.  Run this any time you edit the config by hand.

Usage:
    python3 validate_photo_config.py
    python3 validate_photo_config.py --config path/to/photo_config.json
    python3 validate_photo_config.py --no-disk   # skip file-exists checks
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS  = "  ✓"
FAIL  = "  ✗"
WARN  = "  ⚠"

errors   = []
warnings = []

def err(msg: str):
    errors.append(msg)
    print(f"{FAIL} {msg}")

def warn(msg: str):
    warnings.append(msg)
    print(f"{WARN} {msg}")

def ok(msg: str):
    print(f"{PASS} {msg}")


# ── Tier 1 — JSON syntax ──────────────────────────────────────────────────────

def check_syntax(config_path: Path) -> dict | None:
    print("\n── Tier 1: JSON Syntax ─────────────────────────────────────────────")
    raw = config_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
        ok("JSON syntax is valid — no missing commas, quotes, or brackets.")
        return data
    except json.JSONDecodeError as e:
        lines = raw.splitlines()
        bad_line = lines[e.lineno - 1] if e.lineno <= len(lines) else "(end of file)"
        err(f"JSON syntax error on line {e.lineno}, column {e.colno}:")
        print(f"       Line:    {bad_line.strip()}")
        print(f"       Problem: {e.msg}")
        print("\n  Cannot continue to content checks until syntax is fixed.")
        return None


# ── Tier 2 — Content checks ───────────────────────────────────────────────────

def check_top_level(data: dict):
    print("\n── Tier 2: Required Fields ─────────────────────────────────────────")
    required = ["output_directory", "site_info", "slideshow_config",
                "slideshow_photos", "galleries"]
    for field in required:
        if field not in data:
            err(f"Missing required top-level field: '{field}'")
        else:
            ok(f"Found '{field}'")

    site_required = ["title", "photographer_name", "copyright_year"]
    site = data.get("site_info", {})
    for field in site_required:
        if field not in site:
            err(f"Missing required site_info field: '{field}'")
        else:
            ok(f"Found site_info.{field}: {site[field]!r}")


def check_galleries(data: dict, check_disk: bool):
    print("\n── Gallery Checks ──────────────────────────────────────────────────")
    galleries = data.get("galleries", [])
    if not isinstance(galleries, list):
        err("'galleries' must be a list.")
        return

    seen_ids = {}
    for i, gallery in enumerate(galleries):
        gid   = gallery.get("id",   f"(gallery #{i+1} has no id)")
        gname = gallery.get("name", "(no name)")
        label = f"Gallery '{gid}'"

        # Duplicate IDs
        if gid in seen_ids:
            err(f"{label}: duplicate gallery id — also used at position {seen_ids[gid]+1}")
        else:
            seen_ids[gid] = i

        # ID has spaces
        if " " in str(gid):
            err(f"{label}: gallery id contains spaces — use underscores instead")

        # Required fields
        for field in ["id", "name", "source_directory", "photos", "notes"]:
            if field not in gallery:
                err(f"{label}: missing required field '{field}'")

        # source_directory exists on disk
        src = gallery.get("source_directory", "")
        if check_disk and src:
            if not Path(src).is_dir():
                warn(f"{label}: source_directory not found on disk: {src}")
            else:
                ok(f"{label}: source_directory found")

        # photos list
        photos = gallery.get("photos", [])
        notes  = gallery.get("notes",  {})
        if not isinstance(photos, list):
            err(f"{label}: 'photos' must be a list")
            continue

        if len(photos) == 0:
            warn(f"{label}: photos list is empty")

        # Duplicate filenames within a gallery
        seen_files = {}
        for j, photo_file in enumerate(photos):
            if photo_file in seen_files:
                err(f"{label}: duplicate photo filename '{photo_file}' "
                    f"at positions {seen_files[photo_file]+1} and {j+1}")
            else:
                seen_files[photo_file] = j

            # File exists on disk
            if check_disk and src:
                full_path = Path(src) / photo_file
                if not full_path.exists():
                    warn(f"{label}: photo not found on disk: {photo_file}")

        # Notes keys match photo list
        photo_set = set(photos)
        note_set  = set(notes.keys())
        for key in note_set - photo_set:
            warn(f"{label}: notes has entry for '{key}' but it is not in the photos list")

        ok(f"{label}: {len(photos)} photo(s), {sum(1 for v in notes.values() if v)} note(s)")


def check_slideshow(data: dict):
    print("\n── Slideshow Checks ────────────────────────────────────────────────")
    slideshow_photos = data.get("slideshow_photos", [])
    gallery_map = {g["id"]: g for g in data.get("galleries", []) if "id" in g}

    if not slideshow_photos:
        warn("slideshow_photos is empty — the home page slideshow will have no images")
        return

    seen = set()
    for i, item in enumerate(slideshow_photos):
        gid   = item.get("gallery_id",  "")
        photo = item.get("photo_file",  "")
        label = f"slideshow_photos[{i+1}]"

        if not gid:
            err(f"{label}: missing 'gallery_id'")
        elif gid not in gallery_map:
            err(f"{label}: gallery_id '{gid}' does not match any gallery")
        elif photo not in gallery_map[gid].get("photos", []):
            err(f"{label}: photo '{photo}' not found in gallery '{gid}'")
        else:
            key = (gid, photo)
            if key in seen:
                warn(f"{label}: duplicate slideshow entry ({gid} / {photo})")
            seen.add(key)
            ok(f"{label}: {gid} / {photo}")


def check_output_dir(data: dict):
    print("\n── Output Directory ────────────────────────────────────────────────")
    out = data.get("output_directory", "")
    if not out:
        err("output_directory is blank")
    else:
        ok(f"output_directory: {out}")
        if Path(out).exists():
            ok("  Directory already exists — will be overwritten on next build")
        else:
            ok("  Directory does not exist yet — will be created on build")


def check_support_files(data: dict, check_disk: bool):
    """
    Soft check for support_files_directory. Optional field — not an error if
    missing. Useful for spotting accidental round-trip data loss through
    config_to_csv / csv_to_config.
    """
    print("\n── Support Files Directory ─────────────────────────────────────────")
    sfd = data.get("support_files_directory", "")
    if not sfd:
        ok("support_files_directory: not set (optional)")
        return
    ok(f"support_files_directory: {sfd}")
    if check_disk:
        if Path(sfd).is_dir():
            ok("  Directory found on disk")
        else:
            warn(f"  Directory not found on disk: {sfd}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate photo_config.json for syntax and content errors.")
    parser.add_argument(
        "--config", "-c",
        default="user_files/photo_config.json",
        help="Path to config file (default: user_files/photo_config.json)")
    parser.add_argument(
        "--no-disk",
        action="store_true",
        help="Skip checks that require reading the file system")
    args = parser.parse_args()

    config_path = Path(args.config)
    check_disk  = not args.no_disk

    print(f"\nValidating: {config_path.resolve()}")

    if not config_path.exists():
        print(f"\n{FAIL} Config file not found: {config_path}")
        sys.exit(1)

    # Tier 1 — syntax
    data = check_syntax(config_path)
    if data is None:
        print(f"\n{'─'*60}")
        print(f"  Result: FAILED  ({len(errors)} error(s))\n")
        sys.exit(1)

    # Tier 2 — content
    check_top_level(data)
    check_galleries(data, check_disk)
    check_slideshow(data)
    check_output_dir(data)
    check_support_files(data, check_disk)

    # Summary
    print(f"\n{'─'*60}")
    if errors:
        print(f"  Result: FAILED  — {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    elif warnings:
        print(f"  Result: PASSED with {len(warnings)} warning(s) — review warnings above")
    else:
        print(f"  Result: PASSED — no errors or warnings")


if __name__ == "__main__":
    main()
