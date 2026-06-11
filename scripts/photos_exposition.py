#!/usr/bin/env python3
"""
Photos at an Exposition - Website Generator for Photographers
Generates a four-layer website structure:
1. Home page with slideshow and gallery links
2. Gallery index pages with thumbnails
3. Individual photo pages
4. (Optional) Extended-notes "Read more" pages, one per photo that has
   notes_body text in photos.csv OR a sidecar .md file next to the photo.
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
import argparse

# The project root is the folder containing this script's parent (e.g. the
# directory that holds scripts/ or system_files/ alongside user_files/).
# Relative paths in the config (output_directory, source_directory) are
# resolved against THIS root, not the current working directory, so the build
# works no matter where it's launched from — guarding against the relative-path
# "missing tiles" failure mode.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _abs_path(path_str: str) -> Path:
    """Resolve a config path string to an absolute Path.

    '~' is expanded; absolute paths are normalized; relative paths are
    anchored to PROJECT_ROOT rather than the current working directory.
    """
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()

# Optional Markdown rendering — falls back to a simple paragraph splitter
# if the 'markdown' package isn't installed.
try:
    import markdown as _markdown_lib
    _HAS_MARKDOWN = True
except ImportError:
    _HAS_MARKDOWN = False


class PhotoExpositionGenerator:
    def __init__(self, config_file: str):
        """Initialize the generator with configuration."""
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.output_dir = _abs_path(self.config['output_directory'])
        self.photos_dir = self.output_dir / 'photos'
        self.thumbs_dir = self.output_dir / 'thumbnails'
        self.css_dir = self.output_dir / 'css'
        self.js_dir = self.output_dir / 'js'
        self.originals_dir = self.output_dir / 'originals'
        # Long-edge cap (px) for the downloadable print-quality copies.
        self.print_max_px = int(self.config.get('print_max_px', 3000))
        
    def generate_website(self, clean: bool = False):
        """Generate the complete website."""
        print("Starting website generation...")

        # Optionally wipe previously generated content for a from-scratch build
        if clean:
            self._clean_output()

        # Create directory structure
        self._create_directories()
        
        # Copy and process photos
        self._process_photos()

        # Publish print-quality copies for the download button
        self._process_print_originals()

        # Generate CSS and JavaScript
        self._generate_css()
        self._generate_javascript()
        
        # Generate pages
        self._generate_home_page()
        self._generate_gallery_pages()
        self._generate_photo_pages()
        self._generate_extended_notes_pages()
        
        print(f"\nWebsite generated successfully in: {self.output_dir}")
        print(f"Open {self.output_dir / 'index.html'} in your browser to view.")
        
    def _clean_output(self):
        """Remove previously generated content so the build starts from a
        clean slate (no orphaned pages/images from deleted or renamed
        galleries).

        Only the folders and files this generator creates are removed —
        photos/, thumbnails/, css/, js/, and the top-level *.html pages.
        The output directory itself and any unrelated files inside it are
        left untouched, so a misconfigured output_directory can't wipe
        anything unexpected.
        """
        print("\nCleaning previously generated output...")
        if not self.output_dir.exists():
            print("  Output directory does not exist yet — nothing to clean.")
            return

        dirs_removed = 0
        for sub in [self.photos_dir, self.thumbs_dir, self.css_dir,
                    self.js_dir, self.originals_dir]:
            if sub.exists():
                shutil.rmtree(sub)
                dirs_removed += 1

        html_removed = 0
        for html_file in self.output_dir.glob('*.html'):
            html_file.unlink()
            html_removed += 1

        print(f"  Removed {html_removed} HTML page(s) and {dirs_removed} "
              f"generated folder(s).")

    def _create_directories(self):
        """Create necessary directory structure."""
        for directory in [self.output_dir, self.photos_dir, self.thumbs_dir, 
                         self.css_dir, self.js_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create gallery subdirectories
        for gallery in self.config['galleries']:
            (self.photos_dir / gallery['id']).mkdir(exist_ok=True)
            (self.thumbs_dir / gallery['id']).mkdir(exist_ok=True)
    
    def _process_photos(self):
        """Copy photos and generate thumbnails."""
        print("\nProcessing photos...")
        thumb_size = tuple(self.config.get('thumbnail_size', [300, 300]))
        
        for gallery in self.config['galleries']:
            gallery_id = gallery['id']
            source_dir = _abs_path(gallery['source_directory'])
            
            for photo_file in gallery['photos']:
                source_path = source_dir / photo_file
                
                if not source_path.exists():
                    print(f"  Warning: {source_path} not found, skipping...")
                    continue
                
                # Copy original photo
                dest_path = self.photos_dir / gallery_id / photo_file
                shutil.copy2(source_path, dest_path)
                
                # Generate thumbnail
                self._create_thumbnail(source_path, 
                                      self.thumbs_dir / gallery_id / photo_file,
                                      thumb_size)
                
                print(f"  Processed: {gallery_id}/{photo_file}")
    
    def _create_thumbnail(self, source: Path, dest: Path, size: tuple):
        """Create a thumbnail image."""
        try:
            # Raise PIL's pixel limit to handle large photos safely
            Image.MAX_IMAGE_PIXELS = 200_000_000
            with Image.open(source) as img:
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                # Pre-shrink very large images before thumbnailing
                max_pixels = 20_000_000
                if img.width * img.height > max_pixels:
                    scale = (max_pixels / (img.width * img.height)) ** 0.5
                    new_w = int(img.width * scale)
                    new_h = int(img.height * scale)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Create thumbnail maintaining aspect ratio
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(dest, 'JPEG', quality=85)
        except Exception as e:
            print(f"    Error creating thumbnail for {source}: {e}")

    def _process_print_originals(self):
        """Publish print-quality copies of each photo for the download button.

        For every photo we prefer the full-resolution version found in a
        sibling '<source>_original' backup folder (created when display copies
        were installed); if none exists we fall back to the live source image.
        The copy is downscaled so its long edge is at most self.print_max_px
        (never upscaled) and written to originals/<gallery_id>/<photo_file>.
        Existing copies are skipped, so re-running resumes cheaply.
        """
        print(f"\nPublishing print-quality copies (≤{self.print_max_px}px)...")
        Image.MAX_IMAGE_PIXELS = 400_000_000
        self.originals_dir.mkdir(parents=True, exist_ok=True)

        for gallery in self.config['galleries']:
            gallery_id = gallery['id']
            source_dir = _abs_path(gallery['source_directory'])
            backup_dir = source_dir.parent / f"{source_dir.name}_original"
            out_dir = self.originals_dir / gallery_id
            out_dir.mkdir(parents=True, exist_ok=True)

            made = 0
            for photo_file in gallery['photos']:
                dest = out_dir / photo_file
                if dest.exists():
                    continue
                # Prefer the full-resolution backup, else the live source
                candidate = backup_dir / photo_file
                src_path = candidate if candidate.exists() else source_dir / photo_file
                if not src_path.exists():
                    continue
                try:
                    with Image.open(src_path) as img:
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        w, h = img.size
                        if max(w, h) > self.print_max_px:
                            s = self.print_max_px / max(w, h)
                            img = img.resize((max(1, round(w * s)),
                                              max(1, round(h * s))),
                                             Image.Resampling.LANCZOS)
                        if photo_file.lower().endswith('.png'):
                            img.save(dest, 'PNG')
                        else:
                            img.convert('RGB').save(dest, 'JPEG', quality=92)
                        made += 1
                except Exception as e:
                    print(f"    Error preparing print copy for {src_path}: {e}")
            print(f"  {gallery_id}: {made} print copy(ies) prepared "
                  f"(source: {'backup' if backup_dir.exists() else 'live'}).")

    def _generate_css(self):
        """Generate CSS stylesheet."""
        thumb_display = int(self.config.get('thumbnail_display_size', 280))
        # Mobile cells scale down to roughly 70% of desktop, never below 120px
        thumb_display_mobile = max(120, int(thumb_display * 0.7))

        css_content = """
/* Photos at an Exposition - Main Stylesheet */

:root {
    --primary-color: #2c3e50;
    --secondary-color: #34495e;
    --accent-color: #3498db;
    --text-color: #333;
    --light-bg: #ecf0f1;
    --border-color: #bdc3c7;
    --gold: #FFD700;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: #fff;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header Styles */
header {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    padding: 40px 20px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
    font-weight: 300;
    letter-spacing: 2px;
    color: var(--gold);
}

header h2 {
    font-size: 1.3em;
    font-weight: 300;
    opacity: 0.9;
}

/* Overview Box */
.overview-box {
    background-color: var(--light-bg);
    border-left: 4px solid var(--accent-color);
    padding: 30px;
    margin: 40px 0;
    border-radius: 4px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.overview-box p {
    font-size: 1.1em;
    line-height: 1.8;
    color: var(--secondary-color);
}

/* Slideshow Styles */
.slideshow-wrapper {
    margin: 40px auto;
}

.slideshow-container {
    max-width: 1000px;
    height: 600px;
    margin: 0 auto;
    position: relative;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.slideshow-slide {
    /* All slides are layered on top of each other; opacity decides which
       is visible. Both the outgoing and incoming slides transition at the
       same time, giving a true cross-fade.

       Laid out as a vertical stack: a black top strip, the image area, then
       the caption band pinned to the lower border. The caption is its own
       row, so it never overlays the image. */
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #000;
    opacity: 0;
    transition: opacity 1s ease-in-out;
    pointer-events: none;
    padding-top: 40px;   /* always-visible black border at the top */
    box-sizing: border-box;
}

.slideshow-slide.active {
    opacity: 1;
    pointer-events: auto;
}

.slideshow-slide img {
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    object-fit: contain;
    display: block;
}

.slide-caption {
    flex: 0 0 auto;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 14px 20px;
    font-size: 1.1em;
    line-height: 1.4;
    text-align: center;
}

/* Gallery Navigation */
.gallery-nav {
    margin: 30px 0;
    text-align: center;
}

.gallery-nav h3 {
    font-size: 1.5em;
    margin-bottom: 20px;
    color: var(--primary-color);
}

.gallery-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    max-width: 900px;
    margin: 0 auto;
}

.gallery-button {
    flex: 1 1 150px;
    padding: 14px 20px;
    background-color: var(--accent-color);
    color: white;
    text-decoration: none;
    border: 2px solid var(--primary-color);
    border-radius: 6px;
    font-size: 1em;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    text-align: center;
}

.gallery-button:hover {
    background-color: var(--primary-color);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.gallery-button.active {
    background-color: var(--primary-color);
    font-weight: 600;
    box-shadow: inset 0 0 0 2px var(--gold);
    pointer-events: none;
}

.gallery-button.current {
    background-color: var(--primary-color);
    font-weight: 600;
    box-shadow: inset 0 0 0 2px var(--gold);
}

/* Gallery Grid */
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(__THUMB_DISPLAY__px, 1fr));
    gap: 25px;
    margin: 40px 0;
}

.gallery-item {
    position: relative;
    overflow: hidden;
    border-radius: 8px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
}

.gallery-item:hover {
    transform: scale(1.03);
    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
}

.gallery-item img {
    width: 100%;
    height: auto;
    display: block;
}

.thumb-caption {
    padding: 10px 12px 12px 12px;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 1.05rem;
    color: var(--text-color);
    text-align: center;
    line-height: 1.45;
    background: #fff;
}

/* Photo Page */
.photo-viewer {
    max-width: 1700px;
    margin: 0 auto;
    text-align: center;
}

.photo-main {
    background: #000;
    padding: 10px;
    margin-bottom: 20px;
}

.photo-main img {
    max-width: 1600px;
    max-height: 700px;
    width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
    border: 4px solid #FFD700;
    border-radius: 4px;
    box-shadow: 0 0 18px rgba(255, 215, 0, 0.45);
    object-fit: contain;
}

.photo-caption {
    max-width: 1000px;
    margin: 0 auto 20px auto;
    padding: 12px 20px;
    font-size: 1.05rem;
    line-height: 1.5;
    color: var(--text-color);
    text-align: center;
    font-style: italic;
}

.photo-nav {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin: 30px 0;
}

.photo-nav a, .back-link {
    padding: 12px 25px;
    background-color: var(--accent-color);
    color: white;
    text-decoration: none;
    border-radius: 4px;
    transition: background-color 0.3s ease;
}

.photo-nav a:hover, .back-link:hover {
    background-color: var(--primary-color);
}

/* Footer */
footer {
    background-color: var(--primary-color);
    color: white;
    text-align: center;
    padding: 30px 20px;
    margin-top: 60px;
}

footer p {
    margin: 5px 0;
}

footer strong {
    color: var(--gold);
}

/* Zoom — three levels: 1x → 2x → 3x → 1x */
.photo-main {
    cursor: zoom-in;
    position: relative;
}
.photo-main.zoom2 {
    cursor: zoom-in;
    overflow: visible;
    z-index: 100;
}
.photo-main.zoom3 {
    cursor: zoom-out;
    overflow: visible;
    z-index: 100;
}
.photo-main.zoom2.dragging,
.photo-main.zoom3.dragging {
    cursor: grabbing;
}
.photo-main img {
    transition: transform 0.25s ease;
}

/* Photo stage: prev/next arrows sit OUTSIDE the image frame, one on each
   side, with the framed image centered between them. */
.photo-stage {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin-bottom: 20px;
}

.photo-stage .photo-main {
    flex: 1 1 auto;
    min-width: 0;
    margin-bottom: 0;
}

.photo-arrow {
    flex: 0 0 auto;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    line-height: 1;
    color: #fff;
    text-decoration: none;
    background: var(--accent-color);
    border: 2px solid var(--primary-color);
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    transition: background 0.2s ease, transform 0.2s ease;
}

.photo-arrow:hover {
    background: var(--primary-color);
    transform: scale(1.08);
}

@media (max-width: 768px) {
    .photo-stage { gap: 8px; }
    .photo-arrow {
        width: 38px;
        height: 38px;
        font-size: 1.4rem;
    }
}

/* ── Layer 4: Extended Notes ("Read more") Pages ─────────────────────── */
.notes-page {
    max-width: 1100px;
    margin: 0 auto;
}

.notes-header-row {
    display: flex;
    gap: 30px;
    align-items: flex-start;
    margin: 20px 0 30px 0;
}

.notes-thumb {
    flex: 0 0 300px;
    display: block;
    border: 3px solid var(--gold);
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    background: #000;
}

.notes-thumb:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}

.notes-thumb img {
    display: block;
    width: 100%;
    height: auto;
}

.notes-text {
    flex: 1 1 auto;
    min-width: 0;
}

.notes-heading {
    font-size: 1.8em;
    color: var(--primary-color);
    margin-bottom: 18px;
    font-weight: 400;
    line-height: 1.3;
    border-bottom: 2px solid var(--accent-color);
    padding-bottom: 8px;
}

.notes-body {
    font-size: 1.05rem;
    line-height: 1.75;
    color: var(--text-color);
}

.notes-body p {
    margin-bottom: 1em;
}

.notes-body p:last-child {
    margin-bottom: 0;
}

.notes-body ul,
.notes-body ol {
    margin: 0 0 1em 1.5em;
}

.notes-body li {
    margin-bottom: 0.4em;
}

.notes-body a {
    color: var(--accent-color);
    text-decoration: underline;
}

.notes-body a:hover {
    color: var(--primary-color);
}

.notes-body blockquote {
    border-left: 4px solid var(--accent-color);
    padding: 8px 0 8px 18px;
    margin: 1em 0;
    color: var(--secondary-color);
    font-style: italic;
}

.notes-body strong { font-weight: 600; }
.notes-body em     { font-style: italic; }

.notes-nav {
    display: flex;
    justify-content: center;
    margin: 40px 0 20px 0;
}

.notes-return {
    padding: 12px 25px;
    background-color: var(--accent-color);
    color: white;
    text-decoration: none;
    border-radius: 4px;
    transition: background-color 0.3s ease;
}

.notes-return:hover {
    background-color: var(--primary-color);
}

/* Print-text action row */
.notes-actions {
    display: flex;
    justify-content: center;
    margin: 30px 0 0 0;
}

button.gallery-button {
    font: inherit;
    cursor: pointer;
}

/* When printing a Read More page, show only the heading and the notes
   text — hide the site chrome, the thumbnail, and all buttons. */
@media print {
    header,
    footer,
    .notes-thumb,
    .notes-actions,
    .notes-nav,
    .gallery-nav {
        display: none !important;
    }

    body {
        background: #fff;
        color: #000;
    }

    .container {
        max-width: 100%;
        margin: 0;
        padding: 0;
    }

    .notes-page,
    .notes-text {
        max-width: 100%;
        width: 100%;
    }

    .notes-header-row {
        display: block;
        margin: 0;
    }

    .notes-heading {
        color: #000;
        border-bottom: 1px solid #000;
    }

    .notes-body {
        font-size: 12pt;
        line-height: 1.5;
        color: #000;
    }

    .notes-body a {
        color: #000;
        text-decoration: none;
    }
}

/* Responsive Design */
@media (max-width: 768px) {
    header h1 {
        font-size: 1.8em;
    }
    
    header h2 {
        font-size: 1em;
    }
    
    .gallery-buttons {
        flex-direction: column;
    }
    
    .gallery-grid {
        grid-template-columns: repeat(auto-fill, minmax(__THUMB_DISPLAY_MOBILE__px, 1fr));
        gap: 15px;
    }

    .notes-header-row {
        flex-direction: column;
        gap: 18px;
    }

    .notes-thumb {
        flex: 0 0 auto;
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
    }

    .notes-heading {
        font-size: 1.5em;
        text-align: center;
    }
}
"""
        css_content = (css_content
                       .replace('__THUMB_DISPLAY_MOBILE__', str(thumb_display_mobile))
                       .replace('__THUMB_DISPLAY__', str(thumb_display)))
        with open(self.css_dir / 'style.css', 'w') as f:
            f.write(css_content)
    
    def _generate_javascript(self):
        """Generate JavaScript for slideshow."""
        # Get slideshow config from the JSON config file
        slideshow_config = self.config.get('slideshow_config', {
            'interval_seconds': 5,
            'show_captions': True
        })
        
        js_content = f"""
// Photos at an Exposition - Slideshow Script

class Slideshow {{
    constructor(containerId, config = {{}}) {{
        this.container = document.getElementById(containerId);
        this.slides = this.container.querySelectorAll('.slideshow-slide');
        this.currentSlide = 0;
        this.interval = (config.interval_seconds || 5) * 1000;
        this.showCaptions = config.show_captions !== false;
        this.timer = null;
        
        // Hide captions if configured
        if (!this.showCaptions) {{
            this.container.querySelectorAll('.slide-caption').forEach(caption => {{
                caption.style.display = 'none';
            }});
        }}
    }}
    
    start() {{
        this.showSlide(0);
        this.timer = setInterval(() => this.nextSlide(), this.interval);
    }}
    
    showSlide(index) {{
        this.slides.forEach(slide => slide.classList.remove('active'));
        this.slides[index].classList.add('active');
        this.currentSlide = index;
    }}
    
    nextSlide() {{
        const next = (this.currentSlide + 1) % this.slides.length;
        this.showSlide(next);
    }}
    
    stop() {{
        if (this.timer) {{
            clearInterval(this.timer);
        }}
    }}
}}

// Configuration injected from JSON config file
const slideshowConfig = {json.dumps(slideshow_config)};

// Initialize slideshow when page loads
document.addEventListener('DOMContentLoaded', function() {{
    const slideshow = new Slideshow('slideshow', slideshowConfig);
    slideshow.start();
}});
"""
        with open(self.js_dir / 'slideshow.js', 'w') as f:
            f.write(js_content)
    
    def _generate_home_page(self):
        """Generate the home page with slideshow."""
        print("\nGenerating home page...")
        
        site_info = self.config['site_info']
        slideshow_photos = self._get_slideshow_photos()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_info['title']}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>{site_info['title']}</h1>
        <h2>{site_info['subtitle']}</h2>
    </header>
    
    <div class="container">
        <div class="slideshow-wrapper">
            <div class="slideshow-container" id="slideshow">
{self._generate_slideshow_html(slideshow_photos)}
            </div>
        </div>
        
        <div class="gallery-nav">
            <h3>Explore Galleries</h3>
            <div class="gallery-buttons">
{self._generate_gallery_buttons()}
            </div>
        </div>
    </div>
    
    <footer>
        <p><strong>{site_info['photographer_name']}</strong></p>
        <p>Published: {site_info['date_published']}</p>
        <p>&copy; {site_info['copyright_year']} {site_info['photographer_name']}. All rights reserved.</p>
    </footer>
    
    <script src="js/slideshow.js"></script>
</body>
</html>
"""
        
        with open(self.output_dir / 'index.html', 'w') as f:
            f.write(html)
    
    def _get_slideshow_photos(self) -> List[Dict[str, str]]:
        """Get photos for the home page slideshow."""
        slideshow_config = self.config.get('slideshow_photos', [])
        photos = []
        
        for item in slideshow_config:
            gallery_id = item['gallery_id']
            photo_file = item['photo_file']
            photos.append({
                'path': f"photos/{gallery_id}/{photo_file}",
                'gallery': gallery_id,
                'photo_file': photo_file
            })

        return photos
    
    def _generate_slideshow_html(self, photos: List[Dict[str, str]]) -> str:
        """Generate HTML for slideshow slides."""
        slides = []
        # Maps of gallery IDs to names and per-photo notes for captions
        gallery_names = {g['id']: g['name'] for g in self.config['galleries']}
        gallery_notes = {g['id']: g.get('notes', {}) for g in self.config['galleries']}

        for photo in photos:
            gallery_id = photo['gallery']
            gallery_name = gallery_names.get(gallery_id, gallery_id)
            note = gallery_notes.get(gallery_id, {}).get(photo['photo_file'], '').strip()
            caption = f'{gallery_name} - {note}' if note else gallery_name
            slides.append(f'            <div class="slideshow-slide">')
            slides.append(f'            <img src="{photo["path"]}" alt="Photo from {gallery_name}">')
            slides.append(f'            <div class="slide-caption">{caption}</div>')
            slides.append(f'            </div>')
        return '\n'.join(slides)
    
    def _generate_gallery_buttons(self) -> str:
        """Generate HTML for gallery navigation buttons."""
        buttons = []
        for gallery in self.config['galleries']:
            buttons.append(f'                <a href="{gallery["id"]}.html" class="gallery-button">{gallery["name"]}</a>')
        return '\n'.join(buttons)

    def _generate_gallery_nav_row(self, current_id: str, lock_current: bool = True) -> str:
        """Generate a nav row of buttons: a Home button followed by a button
        for every gallery. The button for the current gallery is highlighted.

        lock_current=True  → highlighted and non-clickable ('active'),
                             for use on the gallery's own index page.
        lock_current=False → highlighted but still links to the index
                             ('current'), for use on photo / notes pages
                             where the user may want to jump to the index.
        """
        buttons = ['                <a href="index.html" class="gallery-button">Home</a>']
        for gallery in self.config['galleries']:
            if gallery['id'] == current_id:
                cls = ' active' if lock_current else ' current'
            else:
                cls = ''
            buttons.append(
                f'                <a href="{gallery["id"]}.html" '
                f'class="gallery-button{cls}">{gallery["name"]}</a>'
            )
        return '\n'.join(buttons)
    
    def _generate_gallery_pages(self):
        """Generate gallery index pages."""
        print("\nGenerating gallery pages...")
        
        for gallery in self.config['galleries']:
            self._generate_single_gallery_page(gallery)
    
    def _generate_single_gallery_page(self, gallery: Dict[str, Any]):
        """Generate a single gallery index page."""
        gallery_id = gallery['id']
        gallery_name = gallery['name']
        description = gallery.get('description', '')
        
        print(f"  Creating: {gallery_id}.html")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{gallery_name} - {self.config['site_info']['title']}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>{gallery_name}</h1>
        <h2>{self.config['site_info']['subtitle']}</h2>
    </header>
    
    <div class="container">
        <div class="gallery-nav">
            <div class="gallery-buttons">
{self._generate_gallery_nav_row(gallery_id)}
            </div>
        </div>

        <div class="gallery-grid">
{self._generate_gallery_thumbnails(gallery)}
        </div>

        <div class="gallery-nav">
            <div class="gallery-buttons">
{self._generate_gallery_nav_row(gallery_id)}
            </div>
        </div>
    </div>

    <footer>
        <p><strong>{self.config['site_info']['photographer_name']}</strong></p>
        <p>&copy; {self.config['site_info']['copyright_year']} {self.config['site_info']['photographer_name']}. All rights reserved.</p>
    </footer>
</body>
</html>
"""
        
        with open(self.output_dir / f"{gallery_id}.html", 'w') as f:
            f.write(html)
    
    def _generate_gallery_thumbnails(self, gallery: Dict[str, Any]) -> str:
        """Generate thumbnail grid for a gallery."""
        items = []
        gallery_id = gallery['id']
        notes = gallery.get('notes', {})

        for i, photo_file in enumerate(gallery['photos']):
            note_text = notes.get(photo_file, '').strip()
            items.append(f'            <a href="{gallery_id}_{i}.html" class="gallery-item">')
            items.append(f'                <img src="thumbnails/{gallery_id}/{photo_file}" alt="{photo_file}">')
            if note_text:
                items.append(f'                <div class="thumb-caption">{note_text}</div>')
            items.append(f'            </a>')

        return '\n'.join(items)
    
    def _generate_photo_pages(self):
        """Generate individual photo pages."""
        print("\nGenerating individual photo pages...")
        
        for gallery in self.config['galleries']:
            self._generate_gallery_photo_pages(gallery)
    
    def _generate_gallery_photo_pages(self, gallery: Dict[str, Any]):
        """Generate individual photo pages for a gallery."""
        gallery_id = gallery['id']
        gallery_name = gallery['name']
        photos = gallery['photos']
        notes = gallery.get('notes', {})
        # Merge CSV-supplied extended_notes with any sidecar .md files.
        extended_notes = self._load_extended_notes(gallery)

        for i, photo_file in enumerate(photos):
            prev_index = i - 1 if i > 0 else len(photos) - 1
            next_index = i + 1 if i < len(photos) - 1 else 0
            note_text = notes.get(photo_file, '').strip()
            caption_html = f'\n            <div class="photo-caption">{note_text}</div>' if note_text else ''

            # Actions row above the gallery nav: a Download Image button
            # (always), plus a Read More button when this photo has extended
            # notes content.
            has_extended = bool(extended_notes.get(photo_file, {}).get('body', '').strip())
            read_more_btn = (
                f'\n                    <a href="{gallery_id}_{i}_notes.html" class="gallery-button">Read More</a>'
                if has_extended else ''
            )
            actions_row = (
                f'''            <div class="gallery-nav photo-actions-row">
                <div class="gallery-buttons">
                    <a href="originals/{gallery_id}/{photo_file}" class="gallery-button" download="{photo_file}" title="Save this image to your computer.">Download Image</a>{read_more_btn}
                </div>
            </div>
'''
            )

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{photo_file} - {gallery_name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>{gallery_name}</h1>
        <h2>Photo {i + 1} of {len(photos)}</h2>
    </header>

    <div class="container">
        <div class="photo-viewer">
            <div class="photo-stage">
                <a href="{gallery_id}_{prev_index}.html" class="photo-arrow prev" title="Previous photo" aria-label="Previous photo">&#8249;</a>
                <div class="photo-main" id="photo">
                    <img src="photos/{gallery_id}/{photo_file}" alt="{photo_file}">
                </div>
                <a href="{gallery_id}_{next_index}.html" class="photo-arrow next" title="Next photo" aria-label="Next photo">&#8250;</a>
            </div>
{caption_html}
{actions_row}            <div class="gallery-nav">
                <div class="gallery-buttons">
{self._generate_gallery_nav_row(gallery_id, lock_current=False)}
                </div>
            </div>
        </div>
    </div>

    <footer>
        <p><strong>{self.config['site_info']['photographer_name']}</strong></p>
        <p>&copy; {self.config['site_info']['copyright_year']} {self.config['site_info']['photographer_name']}. All rights reserved.</p>
    </footer>
    <script>
        document.getElementById('photo').scrollIntoView({{behavior: 'smooth', block: 'start'}});
        // Zoom cycle: 1x -> 2x -> 3x -> 1x with drag-to-pan
        const photoMain = document.querySelector('.photo-main');
        const photoImg = photoMain.querySelector('img');
        const ZOOM_LEVELS = [1.0, 2.0, 3.0];
        let zoomIndex = 0;
        let dragMoved = false;
        let startX = 0, startY = 0, translateX = 0, translateY = 0;

        photoMain.addEventListener('mousedown', function(e) {{
            if (e.target.closest('.photo-arrow')) return;
            if (zoomIndex === 0) return;
            dragMoved = false;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
            photoMain.classList.add('dragging');

            function onMouseMove(e) {{
                dragMoved = true;
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                const scale = ZOOM_LEVELS[zoomIndex];
                photoImg.style.transform = 'scale(' + scale + ') translate(' + (translateX / scale) + 'px, ' + (translateY / scale) + 'px)';
            }}

            function onMouseUp() {{
                photoMain.classList.remove('dragging');
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }}

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            e.preventDefault();
        }});

        photoMain.addEventListener('click', function(e) {{
            if (e.target.closest('.photo-arrow')) return;
            if (dragMoved) {{ dragMoved = false; return; }}
            zoomIndex = (zoomIndex + 1) % ZOOM_LEVELS.length;
            translateX = 0;
            translateY = 0;
            photoMain.classList.remove('zoom2', 'zoom3');
            if (zoomIndex === 0) {{
                photoImg.style.transform = '';
            }} else {{
                const scale = ZOOM_LEVELS[zoomIndex];
                photoMain.classList.add('zoom' + (zoomIndex + 1));
                photoImg.style.transform = 'scale(' + scale + ')';
            }}
        }});
    </script>
</body>
</html>
"""
            
            with open(self.output_dir / f"{gallery_id}_{i}.html", 'w') as f:
                f.write(html)
            
            print(f"  Created: {gallery_id}_{i}.html")

    # ── Layer 4: Extended Notes ("Read more") Pages ────────────────────────

    def _load_extended_notes(self, gallery: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Merge CSV-supplied extended_notes with any sidecar .md (or .txt) files
        living next to each photo in the gallery's source_directory.

        Sidecar wins if both exist. A warning is printed in that case.

        Returns dict: {photo_file: {"title": str, "body": str}}
        Photos with no extended notes are simply not in the returned dict.
        """
        merged: Dict[str, Dict[str, str]] = {}
        csv_xnotes = gallery.get('extended_notes', {}) or {}
        source_dir = Path(gallery.get('source_directory', ''))
        gallery_id = gallery.get('id', '')

        # Start with whatever the CSV supplied
        for photo_file, entry in csv_xnotes.items():
            body = (entry.get('body', '') or '').strip()
            if not body:
                continue
            merged[photo_file] = {
                'title': (entry.get('title', '') or '').strip(),
                'body':  body,
                'source': 'csv',
            }

        # Now look for sidecar files; they override CSV
        if source_dir.exists():
            for photo_file in gallery.get('photos', []):
                base = Path(photo_file).stem
                sidecar_md  = source_dir / f"{base}.md"
                sidecar_txt = source_dir / f"{base}.txt"

                sidecar_path = None
                if sidecar_md.exists():
                    sidecar_path = sidecar_md
                elif sidecar_txt.exists():
                    sidecar_path = sidecar_txt

                if sidecar_path is None:
                    continue

                title, body = self._parse_sidecar_markdown(sidecar_path)
                # Treat a placeholder-only sidecar as empty: if nothing
                # remains after removing HTML comments (<!-- ... -->), skip
                # it so no "Read More" page or button is generated until
                # real text is written.
                if not re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL).strip():
                    continue

                # Title fallback: filename with underscores → spaces, no ext
                if not title:
                    title = base.replace('_', ' ')

                if photo_file in merged and merged[photo_file].get('source') == 'csv':
                    print(f"  Note: sidecar {sidecar_path.name} overrides CSV "
                          f"notes for {gallery_id}/{photo_file}")

                merged[photo_file] = {
                    'title':  title,
                    'body':   body,
                    'source': 'sidecar',
                }

        # CSV entries that survived also need a title fallback
        for photo_file, entry in merged.items():
            if not entry.get('title'):
                entry['title'] = Path(photo_file).stem.replace('_', ' ')

        return merged

    def _parse_sidecar_markdown(self, path: Path) -> Tuple[str, str]:
        """
        Parse a sidecar .md or .txt file. Returns (title, body).

        Supports an optional YAML-style frontmatter for the title:
            ---
            title: My Heading
            ---
            Body text...

        If no frontmatter is present, the title is left blank (the caller
        will fall back to the filename) and the entire file is the body.
        """
        try:
            text = path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  Warning: could not read sidecar {path}: {e}")
            return ('', '')

        title = ''
        body = text

        # Frontmatter: --- ... --- at the very start
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if fm_match:
            fm_block = fm_match.group(1)
            body = text[fm_match.end():]
            for line in fm_block.splitlines():
                if ':' in line:
                    key, _, val = line.partition(':')
                    if key.strip().lower() == 'title':
                        title = val.strip().strip('"').strip("'")
                        break

        return (title, body.strip())

    def _render_notes_body(self, body: str) -> str:
        """
        Render a notes body to HTML.

        First normalizes literal '\\n\\n' escape sequences (handy when text
        was authored in a single-line CSV cell) into real paragraph breaks.

        Then either runs the body through the 'markdown' library (if
        installed) or falls back to a simple paragraph splitter that
        handles basic **bold** and *italic*.
        """
        # Decode literal \n sequences that came from a single-line CSV cell
        normalized = body.replace('\\n', '\n')
        # Drop any HTML comments so placeholder prompts never render
        normalized = re.sub(r'<!--.*?-->', '', normalized, flags=re.DOTALL)

        if _HAS_MARKDOWN:
            return _markdown_lib.markdown(
                normalized,
                extensions=['extra', 'sane_lists'],
            )

        # Fallback: split on blank lines, basic emphasis, HTML-escape the rest
        import html as _html
        paragraphs = re.split(r'\n\s*\n', normalized.strip())
        rendered = []
        for para in paragraphs:
            if not para.strip():
                continue
            safe = _html.escape(para.strip())
            # Re-introduce **bold** and *italic* after escaping
            safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
            safe = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', safe)
            # Preserve internal line breaks within a paragraph
            safe = safe.replace('\n', '<br>\n')
            rendered.append(f'<p>{safe}</p>')
        return '\n'.join(rendered)

    def _generate_extended_notes_pages(self):
        """Generate layer-4 'Read more' pages for any photo that has notes."""
        print("\nGenerating extended-notes pages...")
        total = 0
        for gallery in self.config['galleries']:
            count = self._generate_gallery_extended_notes_pages(gallery)
            total += count
        if total == 0:
            print("  (no extended notes found — no layer-4 pages built)")
        else:
            print(f"  {total} extended-note page(s) created.")

    def _generate_gallery_extended_notes_pages(self, gallery: Dict[str, Any]) -> int:
        """Build the layer-4 pages for a single gallery. Returns count built."""
        gallery_id   = gallery['id']
        gallery_name = gallery['name']
        photos       = gallery['photos']
        extended_notes = self._load_extended_notes(gallery)

        if not extended_notes:
            return 0

        count = 0
        for i, photo_file in enumerate(photos):
            entry = extended_notes.get(photo_file)
            if not entry or not entry.get('body', '').strip():
                continue

            heading   = entry['title']
            body_html = self._render_notes_body(entry['body'])

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading} - {gallery_name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>{gallery_name}</h1>
        <h2>{heading}</h2>
    </header>

    <div class="container">
        <div class="notes-page">
            <div class="notes-header-row">
                <a href="{gallery_id}_{i}.html" class="notes-thumb"
                   title="Return to photo">
                    <img src="thumbnails/{gallery_id}/{photo_file}" alt="{photo_file}">
                </a>
                <div class="notes-text">
                    <h2 class="notes-heading">{heading}</h2>
                    <div class="notes-body">
{body_html}
                    </div>
                </div>
            </div>

            <div class="notes-actions">
                <button type="button" class="gallery-button" onclick="window.print()">Print Text</button>
            </div>

            <div class="notes-nav gallery-nav">
                <div class="gallery-buttons">
{self._generate_gallery_nav_row(gallery_id, lock_current=False)}
                </div>
            </div>
        </div>
    </div>

    <footer>
        <p><strong>{self.config['site_info']['photographer_name']}</strong></p>
        <p>&copy; {self.config['site_info']['copyright_year']} {self.config['site_info']['photographer_name']}. All rights reserved.</p>
    </footer>
</body>
</html>
"""
            page_path = self.output_dir / f"{gallery_id}_{i}_notes.html"
            with open(page_path, 'w') as f:
                f.write(html)
            print(f"  Created: {gallery_id}_{i}_notes.html  ({entry.get('source', '?')})")
            count += 1

        return count


def main():
    parser = argparse.ArgumentParser(description='Photos at an Exposition - Website Generator')
    parser.add_argument('config', help='Path to configuration JSON file')
    parser.add_argument('--clean', action='store_true',
                        help='Remove previously generated pages, photos, '
                             'thumbnails, css, and js from the output directory '
                             'before building. Use this for a from-scratch build '
                             'so old galleries leave no orphaned pages behind.')
    args = parser.parse_args()

    generator = PhotoExpositionGenerator(args.config)
    generator.generate_website(clean=args.clean)


if __name__ == '__main__':
    main()
