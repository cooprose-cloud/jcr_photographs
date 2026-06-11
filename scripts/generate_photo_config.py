#!/usr/bin/env python3
"""
Photos at an Exposition — Configuration Generator
Walks the user through building a complete photo_config.json file
by scanning their gallery directories and prompting for site details.

Usage:
    python3 generate_photo_config.py                  # interactive wizard
    python3 generate_photo_config.py --user-dir PATH  # pre-set user directory
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import date
from typing import List, Dict, Any

# ── Constants ──────────────────────────────────────────────────────────r

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
DEFAULT_CONFIG_FILE = 'photo_config.json'
MAX_SLIDESHOW_PHOTOS = 8
SEP = '─' * 60


# ── Helpers ────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = '') -> str:
    """Prompt the user for input, showing a default value."""
    if default:
        result = input(f"  {prompt} [{default}]: ").strip()
        return result if result else default
    else:
        while True:
            result = input(f"  {prompt}: ").strip()
            if result:
                return result
            print("    (required — please enter a value)")


def ask_yn(prompt: str, default: bool = True) -> bool:
    """Prompt for a yes/no answer."""
    hint = 'Y/n' if default else 'y/N'
    answer = input(f"  {prompt} [{hint}]: ").strip().lower()
    if not answer:
        return default
    return answer.startswith('y')


def ask_int(prompt: str, default: int, min_val: int = 1) -> int:
    """Prompt for an integer."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if val >= min_val:
                return val
        except ValueError:
            pass
        print(f"    Please enter a whole number >= {min_val}.")


def get_image_files(directory: Path) -> List[str]:
    """Return sorted list of image filenames in a directory."""
    if not directory.exists():
        return []
    return sorted(
        f.name for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def get_notes_file(directory: Path) -> Dict[str, str]:
    """
    Look for an optional notes file in a gallery directory.
    Format (one entry per line):  filename.jpg | Caption text here
    Returns dict: {filename: caption}
    """
    notes = {}
    for candidate in ('notes.txt', 'captions.txt', 'notes.csv'):
        notes_path = directory / candidate
        if notes_path.exists():
            print(f"    Found notes file: {candidate}")
            with open(notes_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '|' in line:
                        parts = line.split('|', 1)
                        fname   = parts[0].strip()
                        caption = parts[1].strip()
                        if fname:
                            notes[fname] = caption
            print(f"    Loaded {len(notes)} caption(s)")
            break
    return notes


# ── Main sections ──────────────────────────────────────────────────────

def collect_site_info() -> Dict[str, str]:
    print(f"\n{SEP}")
    print("  SITE INFORMATION")
    print(SEP)
    year = str(date.today().year)
    return {
        'title':             ask("Website title",            "Photographs by J. Cooper Rose"),
        'subtitle':          ask("Subtitle",                 "A Photographic Journey"),
        'photographer_name': ask("Photographer name",        "J. Cooper Rose"),
        'overview':          ask("Overview / welcome text",  "Welcome to my photographic collection."),
        'date_published':    ask("Date published",           date.today().strftime("%B %Y")),
        'copyright_year':    ask("Copyright year",           year),
    }


def collect_directories(user_dir: Path) -> Dict[str, str]:
    """Collect output and support-files paths."""
    print(f"\n{SEP}")
    print("  DIRECTORIES")
    print(SEP)
    print(f"  User (source) directory: {user_dir}")

    default_output   = str(user_dir.parent / 'website')
    default_support  = str(user_dir / 'support_files')

    output_dir  = ask("Output directory (generated website)", default_output)
    support_dir = ask("Support files directory (css/logo/js)", default_support)

    # Store absolute paths even if the user typed a relative one at the prompt.
    return {
        'output_directory':         str(Path(output_dir).expanduser().resolve()),
        'support_files_directory':  str(Path(support_dir).expanduser().resolve()),
    }


def collect_galleries(user_dir: Path) -> List[Dict[str, Any]]:
    """
    Scan user_dir for gallery subfolders.
    Each immediate subdirectory that is not 'support_files' or 'slideshow'
    is treated as a potential gallery.
    """
    print(f"\n{SEP}")
    print("  GALLERIES")
    print(SEP)

    SKIP_DIRS = {'support_files', 'slideshow', 'css', 'js', '__pycache__'}

    # Find candidate gallery directories
    candidates = sorted(
        d for d in user_dir.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith('.')
        and not d.name.lower().endswith('_original')  # skip full-res backup folders
    )

    if not candidates:
        print("  No subdirectories found. You can add galleries manually.")
        return []

    print(f"  Found {len(candidates)} potential gallery folder(s):")
    for d in candidates:
        n = len(get_image_files(d))
        print(f"    {d.name}  ({n} image{'s' if n != 1 else ''})")

    galleries = []
    for d in candidates:
        photos = get_image_files(d)
        if not photos:
            print(f"\n  Skipping '{d.name}' — no images found.")
            continue

        print(f"\n  Gallery folder: {d.name}  ({len(photos)} photos)")
        include = ask_yn(f"Include '{d.name}' as a gallery?", default=True)
        if not include:
            continue

        gid  = ask("  Gallery ID (no spaces)", d.name.lower().replace(' ', '_'))
        name = ask("  Display name",           d.name.replace('_', ' ').title())
        desc = ask("  Description",            f"Photos from {name}")
        notes = get_notes_file(d)
        # Merge any existing notes file entries; blank out the rest
        blank_notes = {photo: notes.get(photo, '') for photo in photos}

        gallery: Dict[str, Any] = {
            'id':               gid,
            'name':             name,
            'description':      desc,
            'source_directory': str(d),
            'photos':           photos,
            'notes':            blank_notes,
        }

        galleries.append(gallery)
        print(f"    Added '{name}' with {len(photos)} photo(s).")

    return galleries


def collect_slideshow(galleries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Pick one photo per gallery for the home-page slideshow."""
    print(f"\n{SEP}")
    print("  SLIDESHOW")
    print(SEP)
    print("  The slideshow on the home page shows one photo from each gallery.")
    print(f"  (Maximum {MAX_SLIDESHOW_PHOTOS} photos)")

    slideshow = []
    for gallery in galleries[:MAX_SLIDESHOW_PHOTOS]:
        gid    = gallery['id']
        photos = gallery['photos']
        print(f"\n  Gallery: {gallery['name']}")
        print(f"  First photo (default): {photos[0]}")

        if len(photos) == 1 or not ask_yn("  Choose a different slideshow photo?", default=False):
            chosen = photos[0]
        else:
            print("  Available photos:")
            for i, p in enumerate(photos):
                print(f"    {i + 1}. {p}")
            idx = ask_int("  Enter photo number", default=1, min_val=1)
            chosen = photos[min(idx - 1, len(photos) - 1)]

        slideshow.append({'gallery_id': gid, 'photo_file': chosen})
        print(f"  Selected: {chosen}")

    return slideshow


def collect_options() -> Dict[str, Any]:
    print(f"\n{SEP}")
    print("  OPTIONS")
    print(SEP)
    thumb_w = ask_int("Thumbnail width  (px)", default=300)
    thumb_h = ask_int("Thumbnail height (px)", default=300)
    display_size = ask_int("Thumbnail display size on page (px)", default=280)
    ss_secs = ask_int("Slideshow interval (seconds)", default=5)
    captions = ask_yn("Show gallery name captions on slideshow?", default=True)
    return {
        'thumbnail_size':         [thumb_w, thumb_h],
        'thumbnail_display_size': display_size,
        'slideshow_config':  {
            'interval_seconds': ss_secs,
            'show_captions':    captions,
        }
    }


def write_config(config: Dict[str, Any], output_file: str):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


# ── Form-file mode ─────────────────────────────────────────────────────

def generate_form(user_dir: Path):
    """
    Scan user_dir for gallery folders and write a pre-filled photo_config.json
    directly into user_dir.  Every photo in every gallery gets a blank notes
    entry ("") ready for the user to fill in.  Site-info fields are pre-filled
    with sensible defaults — the user edits them directly in the JSON file.
    """
    SKIP_DIRS = {'support_files', 'slideshow', 'css', 'js', '__pycache__'}

    print(f"\n  Scanning: {user_dir}")

    candidates = sorted(
        d for d in user_dir.iterdir()
        if d.is_dir() and d.name.lower() not in {s.lower() for s in SKIP_DIRS}
        and not d.name.startswith('.')
        and not d.name.lower().endswith('_original')  # skip full-res backup folders
    )

    galleries = []
    slideshow_photos = []

    for d in candidates:
        photos = get_image_files(d)
        if not photos:
            print(f"  Skipping '{d.name}' — no images found.")
            continue

        gid  = d.name.lower().replace(' ', '_')
        name = d.name.replace('_', ' ').title()
        desc = f"Photos from {name}"

        # Every photo gets a blank note entry
        notes = {photo: "" for photo in photos}

        galleries.append({
            'id':               gid,
            'name':             name,
            'description':      desc,
            'source_directory': str(d),
            'photos':           photos,
            'notes':            notes,
        })

        # Default slideshow pick: first photo in the gallery
        slideshow_photos.append({
            'gallery_id':  gid,
            'photo_file':  photos[0],
        })

        print(f"  Added gallery '{name}' — {len(photos)} photo(s).")

    if not galleries:
        print("\n  No galleries found. Nothing written.")
        return

    year = str(date.today().year)

    config: Dict[str, Any] = {
        'site_info': {
            'title':             "Photographs by J. Cooper Rose",
            'subtitle':          "A Photographic Journey",
            'photographer_name': "J. Cooper Rose",
            'overview':          "Welcome to my photographic collection.",
            'date_published':    date.today().strftime("%B %Y"),
            'copyright_year':    year,
        },
        'output_directory':         str(user_dir.parent / 'website'),
        'support_files_directory':  str(user_dir / 'support_files'),
        'thumbnail_size':           [300, 300],
        'thumbnail_display_size':   280,
        'slideshow_config': {
            'interval_seconds': 5,
            'show_captions':    True,
        },
        'galleries':        galleries,
        'slideshow_photos': slideshow_photos,
    }

    output_path = (user_dir / DEFAULT_CONFIG_FILE).resolve()
    write_config(config, str(output_path))

    print(f"\n{'=' * 60}")
    print(f"  Form file written: {output_path}")
    print(f"{'=' * 60}")
    print(f"  Galleries : {len(galleries)}")
    total = sum(len(g['photos']) for g in galleries)
    print(f"  Photos    : {total}")
    print()
    print("  Edit photo_config.json in your user_files folder:")
    print("    - Fill in site_info fields (title, overview, etc.)")
    print("    - Add note text for any photo (replace the \"\" entries)")
    print("    - Reorder photos lists to set index page sequence")
    print("    - Reorder slideshow_photos to set slideshow sequence")
    print("    - Change slideshow photo_file to pick a different photo")
    print()
    print("  Then generate your website:")
    print(f"    python3 photos_exposition.py {output_path}")
    print()


def print_summary(config: Dict[str, Any], output_file: str):
    print(f"\n{'=' * 60}")
    print(f"  Configuration saved: {output_file}")
    print(f"{'=' * 60}")
    print(f"  Galleries : {len(config['galleries'])}")
    total = sum(len(g['photos']) for g in config['galleries'])
    print(f"  Photos    : {total}")
    print(f"  Slideshow : {len(config['slideshow_photos'])} photo(s)")
    print(f"  Output dir: {config['output_directory']}")
    print()
    print("  Next step — generate your website:")
    print(f"    python3 photos_exposition.py {output_file}")
    print()


# ── Entry point ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Photos at an Exposition — Configuration Generator'
    )
    parser.add_argument(
        '--user-dir', '-u',
        help='Path to your user_files directory (skips the prompt)',
        default=None
    )
    parser.add_argument(
        '--output', '-o',
        help=(f'Config file name or path (default: {DEFAULT_CONFIG_FILE}). '
              'If not absolute, written into the user_files directory.'),
        default=DEFAULT_CONFIG_FILE
    )
    parser.add_argument(
        '--form', '-f',
        help='Generate a pre-filled photo_config.json into user_files (no prompts)',
        action='store_true'
    )
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       Photos at an Exposition — Config Generator        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── Resolve user directory (shared by both modes)
    if args.user_dir:
        user_dir = Path(args.user_dir).expanduser()
    else:
        print(f"\n{SEP}")
        print("  USER DIRECTORY")
        print(SEP)
        print("  This is the folder where your gallery subfolders live.")
        raw = ask("Path to your user_files directory")
        user_dir = Path(raw).expanduser()

    # Resolve to an absolute path so every derived path (gallery
    # source_directory, output_directory, support_files_directory) is stored
    # absolute in the config. The build then works regardless of the current
    # working directory — avoiding the relative-path "missing tiles" failure.
    user_dir = user_dir.resolve()

    if not user_dir.exists():
        print(f"\n  ERROR: Directory not found: {user_dir}")
        sys.exit(1)

    # ── Form mode: scan and write, no questions asked
    if args.form:
        print(f"\n  MODE: Generate form file into {user_dir}")
        generate_form(user_dir)
        return

    # ── Wizard mode (original interactive flow)
    site_info  = collect_site_info()
    dirs       = collect_directories(user_dir)
    galleries  = collect_galleries(user_dir)

    if not galleries:
        print("\n  No galleries configured. Exiting.")
        sys.exit(0)

    slideshow  = collect_slideshow(galleries)
    options    = collect_options()

    # ── Assemble config
    config: Dict[str, Any] = {
        'site_info':                site_info,
        'output_directory':         dirs['output_directory'],
        'support_files_directory':  dirs['support_files_directory'],
        'thumbnail_size':           options['thumbnail_size'],
        'thumbnail_display_size':   options['thumbnail_display_size'],
        'slideshow_config':         options['slideshow_config'],
        'galleries':                galleries,
        'slideshow_photos':         slideshow,
    }

    # ── Write to user_files; --output is relative to user_files unless absolute
    output_arg = Path(args.output).expanduser()
    if output_arg.is_absolute():
        output_path = output_arg.resolve()
    else:
        output_path = (user_dir / output_arg).resolve()

    print(f"\n  Writing config to: {output_path}")
    write_config(config, str(output_path))
    print_summary(config, str(output_path))


if __name__ == '__main__':
    main()
