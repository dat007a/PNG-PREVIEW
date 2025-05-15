import re
import os
from PIL import Image, ImageTk, ImageFont, ImageDraw
import tkinter as tk

def parse_color_from_filename(filename):
    """Extract RGB color codes from filenames like icon_rgb00a69c_rgbfc1a84.png"""
    matches = re.findall(r"rgb([0-9a-fA-F]{6})", filename)
    return ["#" + m for m in matches]

def load_icon_image(path):
    """Load an icon image from path and convert to RGBA"""
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        print(f"Error loading icon: {e}")
        return None

def get_resized_image(image, width, height):
    """Resize an image while maintaining aspect ratio."""
    aspect = image.width / image.height
    if width / height > aspect:
        new_width = int(height * aspect)
        new_height = height
    else:
        new_width = width
        new_height = int(width / aspect)
    return image.resize((new_width, new_height), Image.LANCZOS)

    if not image:
        return None
    
    aspect = image.width / image.height
    if width / height > aspect:
        new_width = int(height * aspect)
        new_height = height
    else:
        new_width = width
        new_height = int(width / aspect)
    
    return image.resize((new_width, new_height), Image.LANCZOS)

def get_truncated_text(canvas, text, font, max_width):
    """Truncate text to fit within max_width"""
    if not text:
        return ""
    
    text_width = canvas.create_text(0, 0, text=text, font=font, anchor='nw')
    bbox = canvas.bbox(text_width)
    canvas.delete(text_width)
    
    if bbox and bbox[2] - bbox[0] > max_width:
        while text and bbox and bbox[2] - bbox[0] > max_width:
            text = text[:-1]
            text_width = canvas.create_text(0, 0, text=text + "...", font=font, anchor='nw')
            bbox = canvas.bbox(text_width)
            canvas.delete(text_width)
        return text + "..."
    return text

def create_shadow_effect(draw, x, y, text, font, color="#888888", offset=3):
    """Create a drop shadow effect for text (brighter than text)"""
    draw.text((x + offset, y + offset), text, fill=color, font=font)
    
def create_outline_effect(draw, x, y, text, font, color="#FFFFFF", width=1):
    """Create an outline effect for text (brighter than text)"""
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx != 0 or dy != 0:  # Skip the center
                draw.text((x + dx, y + dy), text, fill=color, font=font)
                
def create_stroke_effect(draw, x, y, text, font, color="#222222", width=2):
    """Create a stroke effect for text (darker than text)"""
    for dx in range(-width, width + 1, 1):
        for dy in range(-width, width + 1, 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, fill=color, font=font)

def sanitize_filename(text):
    """Remove invalid characters from filename"""
    return re.sub(r'[\\/*?:"<>|]', "", text)

class DraggableItem:
    """A class to handle draggable items on a canvas"""
    def __init__(self, canvas, item_id, item_type, update_callback=None):
        self.canvas = canvas
        self.item_id = item_id
        self.item_type = item_type  # 'text0', 'text1', 'text2', 'small_icon', 'big_icon'
        self.update_callback = update_callback
        self._drag_data = {"x": 0, "y": 0, "item": None}
        
    def on_drag_start(self, event):
        """Record the item and its location"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["item"] = self.item_id
        
    def on_drag_motion(self, event):
        """Handle dragging of the item"""
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        
        self.canvas.move(self.item_id, dx, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        
    def on_drag_end(self, event):
        """End drag operation and update item position"""
        # Get new coordinates
        coords = self.canvas.coords(self.item_id)
        
        # Different handling based on item type
        if self.item_type.startswith('text'):
            # For text items, coords returns [x, y]
            x, y = coords[:2]
        else:
            # For image items, coords returns [x, y]
            x, y = coords[:2]
            
        # Update position via callback
        if self.update_callback:
            self.update_callback(self.item_type, x, y)
