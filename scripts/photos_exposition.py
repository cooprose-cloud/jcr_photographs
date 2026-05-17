#!/usr/bin/env python3
"""
Photos at an Exposition - Website Generator for Photographers
Generates a three-layer website structure:
1. Home page with slideshow and gallery links
2. Gallery index pages with thumbnails
3. Individual photo pages
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
from PIL import Image
import argparse


class PhotoExpositionGenerator:
    def __init__(self, config_file: str):
        """Initialize the generator with configuration."""
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.output_dir = Path(self.config['output_directory'])
        self.photos_dir = self.output_dir / 'photos'
        self.thumbs_dir = self.output_dir / 'thumbnails'
        self.css_dir = self.output_dir / 'css'
        self.js_dir = self.output_dir / 'js'
        
    def generate_website(self):
        """Generate the complete website."""
        print("Starting website generation...")
        
        # Create directory structure
        self._create_directories()
        
        # Copy and process photos
        self._process_photos()
        
        # Generate CSS and JavaScript
        self._generate_css()
        self._generate_javascript()
        
        # Generate pages
        self._generate_home_page()
        self._generate_gallery_pages()
        self._generate_photo_pages()
        
        print(f"\nWebsite generated successfully in: {self.output_dir}")
        print(f"Open {self.output_dir / 'index.html'} in your browser to view.")
        
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
            source_dir = Path(gallery['source_directory'])
            
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
    display: none;
    width: 100%;
    height: 100%;
    position: relative;
    animation: fadeIn 1s;
    background: #000;
}

.slideshow-slide.active {
    display: flex;
    align-items: center;
    justify-content: center;
}

.slideshow-slide img {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;
    display: block;
}

.slide-caption {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 15px 20px;
    font-size: 1.1em;
    text-align: center;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
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
    padding: 8px 10px 10px 10px;
    font-size: 0.9rem;
    color: var(--text-color);
    text-align: center;
    line-height: 1.3;
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
        <div class="overview-box">
            <p>{site_info['overview']}</p>
        </div>
        
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
                'gallery': gallery_id
            })
        
        return photos
    
    def _generate_slideshow_html(self, photos: List[Dict[str, str]]) -> str:
        """Generate HTML for slideshow slides."""
        slides = []
        # Create a map of gallery IDs to names for captions
        gallery_names = {g['id']: g['name'] for g in self.config['galleries']}
        
        for photo in photos:
            gallery_id = photo['gallery']
            caption = gallery_names.get(gallery_id, gallery_id)
            slides.append(f'            <div class="slideshow-slide">')
            slides.append(f'            <img src="{photo["path"]}" alt="Photo from {caption}">')
            slides.append(f'            <div class="slide-caption">{caption}</div>')
            slides.append(f'            </div>')
        return '\n'.join(slides)
    
    def _generate_gallery_buttons(self) -> str:
        """Generate HTML for gallery navigation buttons."""
        buttons = []
        for gallery in self.config['galleries']:
            buttons.append(f'                <a href="{gallery["id"]}.html" class="gallery-button">{gallery["name"]}</a>')
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
        <a href="index.html" class="back-link">← Back to Home</a>
        
        {f'<div class="overview-box"><p>{description}</p></div>' if description else ''}
        
        <div class="gallery-grid">
{self._generate_gallery_thumbnails(gallery)}
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

        for i, photo_file in enumerate(photos):
            prev_index = i - 1 if i > 0 else len(photos) - 1
            next_index = i + 1 if i < len(photos) - 1 else 0
            note_text = notes.get(photo_file, '').strip()
            caption_html = f'\n            <div class="photo-caption">{note_text}</div>' if note_text else ''
            
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
        <a href="{gallery_id}.html" class="back-link">← Back to Gallery</a>

        <div class="photo-viewer">
            <div class="photo-main" id="photo">
                <img src="photos/{gallery_id}/{photo_file}" alt="{photo_file}">
            </div>
{caption_html}
            <div class="photo-nav">
                <a href="{gallery_id}_{prev_index}.html">← Previous</a>
                <a href="{gallery_id}.html">Gallery Index</a>
                <a href="{gallery_id}_{next_index}.html">Next →</a>
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


def main():
    parser = argparse.ArgumentParser(description='Photos at an Exposition - Website Generator')
    parser.add_argument('config', help='Path to configuration JSON file')
    args = parser.parse_args()
    
    generator = PhotoExpositionGenerator(args.config)
    generator.generate_website()


if __name__ == '__main__':
    main()
