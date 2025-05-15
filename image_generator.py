from PIL import Image, ImageDraw, ImageFont
import os
import datetime
from utils import get_resized_image, create_shadow_effect, create_outline_effect, create_stroke_effect, sanitize_filename

# Color utility functions - moved outside the class to be standalone functions
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color"""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

def darken_color(hex_color, factor=2.0):
    """Make a color darker by the given factor"""
    r, g, b = hex_to_rgb(hex_color)
    
    # Darken by dividing by factor
    r = max(0, int(r / factor))
    g = max(0, int(g / factor))
    b = max(0, int(b / factor))
    
    return rgb_to_hex((r, g, b))

def lighten_color(hex_color, factor=2.0):
    """Make a color lighter by the given factor"""
    r, g, b = hex_to_rgb(hex_color)
    
    # Lighten by interpolating toward white (255, 255, 255)
    r = min(255, int(r + (255 - r) * (1 - 1/factor)))
    g = min(255, int(g + (255 - g) * (1 - 1/factor)))
    b = min(255, int(b + (255 - b) * (1 - 1/factor)))
    
    return rgb_to_hex((r, g, b))

# Draw text with optional effects (shadow, stroke, outline)
def draw_text_with_effects(draw, x, y, text, font, color, effects, line_index=0):
    """Draw text with line-specific effects (shadow, stroke, outline)"""
    if not effects:
        # If no effects, just draw the text
        draw.text((x, y), text, fill=color, font=font)
        return
    
    # Calculate line-specific effect colors based on the text color
    effect_colors = {
        'shadow_color': lighten_color(color, 3.0),  # 3× lighter
        'outline_color': lighten_color(color, 2.0), # 2× lighter
        'stroke_color': darken_color(color, 2.0)    # 2× darker
    }
    
    # Apply shadow effect if enabled
    if effects.get('shadow', False):
        shadow_color = effect_colors['shadow_color']
        shadow_offset = effects.get('shadow_offset', 3)
        draw.text((x + shadow_offset, y + shadow_offset), text, fill=shadow_color, font=font)
    
    # Apply stroke effect if enabled
    if effects.get('stroke', False):
        stroke_color = effect_colors['stroke_color']
        stroke_width = effects.get('stroke_width', 2)
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, fill=stroke_color, font=font)
    
    # Apply outline effect if enabled
    if effects.get('outline', False):
        outline_color = effect_colors['outline_color']
        outline_width = effects.get('outline_width', 1)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    
    # Draw the main text
    draw.text((x, y), text, fill=color, font=font)

class ImageGenerator:
    def __init__(self):
        self.output_size = (1200,1200)

    def generate_image(self, paragraphs, output_path=None):
        img = Image.new("RGBA", self.output_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        for paragraph in paragraphs:
            if not paragraph.get('active', False):
                continue

            text_lines = paragraph.get('text_lines', [])
            fonts = paragraph.get('fonts', [])
            colors = paragraph.get('colors', [])
            positions = paragraph.get('positions', {})
            font_sizes = paragraph.get('font_sizes', {})
            effects = paragraph.get('effects', {})
            icons = paragraph.get('icons', {})
            print("[EXPORT DEBUG] ICON DICT:", icons)

            for i, line_key in enumerate(['text0', 'text1', 'text2']):
                if i >= len(text_lines) or not text_lines[i]:
                    continue

                text = text_lines[i]
                font_name = fonts[i] if i < len(fonts) else (fonts[0] if fonts else "Arial.ttf")
                font_path = os.path.join("FONT MAP", font_name)
                font_size = font_sizes.get(line_key, 32)

                try:
                    font = ImageFont.truetype(font_path, font_size)
                except Exception:
                    font = ImageFont.load_default()

                color = colors[i] if i < len(colors) else "#000000"
                output_x, output_y = positions.get(line_key, (150, 150 + i * 100))

                # Pass the line index to the draw_text_with_effects function
                draw_text_with_effects(draw, output_x, output_y, text, font, color, effects, i)

            # Use icons that were already resized in preview
            small_icon = icons.get('small_icon_resized')
            if small_icon:
                pos = positions.get('small_icon', (600, 600))
                img.paste(small_icon, (int(pos[0]), int(pos[1])), small_icon)

            big_icon = icons.get('big_icon_resized')
            if big_icon:
                pos = positions.get('big_icon', (100, 600))
                img.paste(big_icon, (int(pos[0]), int(pos[1])), big_icon)

        if not output_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            text_label = ""
            if paragraphs and paragraphs[0].get('text_lines') and paragraphs[0]['text_lines'][0]:
                text_label = "_" + sanitize_filename(paragraphs[0]['text_lines'][0][:20])
            if not os.path.exists("OUTPUT"):
                os.makedirs("OUTPUT")
            output_path = os.path.join("OUTPUT", f"CrHashtag_{timestamp}{text_label}.png")

        img.save(output_path)
        print(f"Image saved to: {output_path}")
        return output_path

    def save_image_dialog(self, paragraphs):
        """Show save dialog and save the image to the selected location"""
        try:
            from tkinter import filedialog, messagebox
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            initial_filename = f"CrHashtag_{timestamp}.png"

            output_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png")],
                initialfile=initial_filename
            )

            if output_path:
                path = self.generate_image(paragraphs, output_path)
                messagebox.showinfo("Image Saved", f"Image saved successfully to:\n{path}")
                return path
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Error saving image: {e}")
            print(f"Error saving image: {e}")
            return None
