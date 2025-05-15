import os
import tkinter as tk
from tkinter import ttk, Frame, Label, Checkbutton, IntVar, StringVar
from PIL import ImageTk, Image, ImageFont, ImageDraw

class FontLoader:
    def __init__(self):
        self.fonts = []
        self.font_vars = []
        self.preview_images = []  # Store font preview images
        self.selected_font_count = 0
        self.max_fonts = 3  # Maximum fonts per paragraph
        
    def load_fonts(self):
        """Load all TTF fonts from the FONT MAP directory"""
        self.fonts = []
        if os.path.exists('FONT MAP'):
            for filename in os.listdir('FONT MAP'):
                if filename.lower().endswith('.ttf'):
                    self.fonts.append(filename)
        else:
            print("Warning: FONT MAP directory not found")
            
    def create_font_preview(self, font_path, size=24):
        """Create a preview image for a font"""
        try:
            img = Image.new('RGBA', (150, 50), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(font_path, size)
            draw.text((5, 5), "Abc-123", fill=(0, 0, 0), font=font)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error creating font preview: {e}")
            img = Image.new('RGBA', (150, 50), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((5, 5), "Error", fill=(255, 0, 0))
            return ImageTk.PhotoImage(img)
    
    def display_fonts(self, parent_frame, selection_list):
        """This method is no longer used - UI manager now handles font display"""
        pass  # The UI manager now handles font display directly
    
    def on_font_selected(self, var, font_name):
        """Handle font selection and enforce limits"""
        if var.get() == 1:  # Font selected
            self.selected_font_count += 1
            if self.selected_font_count > self.max_fonts:
                self.enforce_limit()
        else:  # Font deselected
            self.selected_font_count -= 1
    
    def enforce_limit(self):
        """Ensure no more than max_fonts fonts are selected"""
        selected_count = 0
        for var, _, _ in self.font_vars:
            if var.get() == 1:
                selected_count += 1
                
        if selected_count > self.max_fonts:
            # Deselect the first selected font
            for var, _, _ in self.font_vars:
                if var.get() == 1:
                    var.set(0)
                    self.selected_font_count -= 1
                    break
    
    def get_selected_fonts(self):
        """Return list of selected font filenames"""
        return [font for var, font, _ in self.font_vars if var.get() == 1]
    
    def reset_selection(self):
        """Reset all font selections"""
        for var, _, _ in self.font_vars:
            var.set(0)
        self.selected_font_count = 0
