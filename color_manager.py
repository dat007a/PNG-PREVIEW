import os
import tkinter as tk
from tkinter import Frame, Label, Checkbutton, IntVar, PhotoImage, ttk
from utils import parse_color_from_filename
from PIL import Image, ImageTk

class ColorManager:
    def __init__(self):
        self.color_vars = []
        self.colors = []
        self.color_images = []  # Store references to avoid garbage collection
        self.selected_color_count = 0
        self.max_colors = 2  # Maximum color images that can be selected
        
    def load_colors(self):
        """Load color images from COLOR MAP directory"""
        self.colors = []
        
        # First check the COLOR MAP directory
        if os.path.exists('COLOR MAP'):
            for filename in os.listdir('COLOR MAP'):
                if filename.lower().endswith('.png') and 'rgb' in filename.lower():
                    self.colors.append(os.path.join('COLOR MAP', filename))
        
        # Fallback to the current directory
        if not self.colors:
            for filename in os.listdir():
                if filename.lower().endswith('.png') and filename.lower().startswith('icon_rgb'):
                    self.colors.append(filename)
        
        if not self.colors:
            print("Warning: No color images found")

    def display_colors(self, parent_frame, selection_list):
        """Display color options in a scrollable frame with thumbnails"""
        # Create a canvas with scrollbar for the colors
        canvas_frame = Frame(parent_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add a canvas
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add title
        title = Label(scrollable_frame, text="Select up to 2 color schemes", font=("Arial", 12, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=10)
        
        # Add explanation
        explanation = Label(scrollable_frame, 
                          text="Color format: icon_rgb00a69c_rgbfc1a84.png\n- rgb00a69c → Line 1 color\n- rgbfc1a84 → Line 2 + Line 3 color",
                          justify=tk.LEFT)
        explanation.grid(row=1, column=0, columnspan=3, sticky="w", pady=5)
        
        # Display each color option
        for i, file_path in enumerate(self.colors):
            row = (i // 7) + 2  # Start from row 2 (after explanation)
            col = i % 7
            
            try:
                # Get the filename without path
                filename = os.path.basename(file_path)
                
                # Load and resize the image
                img = Image.open(file_path)
                img = img.resize((100, 100), Image.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.color_images.append(photo_img)  # Keep reference
                
                # Create frame for each color
                color_frame = Frame(scrollable_frame)
                color_frame.grid(row=row, column=col, padx=10, pady=10)
                
                # Display image
                img_label = Label(color_frame, image=photo_img)
                img_label.pack()
                
                # Extract colors from filename
                colors = parse_color_from_filename(filename)
                color_text = f"Colors: {', '.join(colors)}"
                
                # Display color codes
                if colors:
                    color_info = Label(color_frame, text=color_text, wraplength=150)
                    color_info.pack()
                
                # Add checkbox
                var = IntVar()
                chk = Checkbutton(
                    color_frame, 
                    text="Select", 
                    variable=var,
                    command=lambda v=var, f=file_path: self.on_color_selected(v, f)
                )
                chk.pack()
                
                self.color_vars.append((var, file_path, chk))
                selection_list.append(var)
                
            except Exception as e:
                print(f"Error loading color image {file_path}: {e}")
    
    def on_color_selected(self, var, file_path):
        """Handle color selection and enforce limit"""
        if var.get() == 1:  # Color selected
            self.selected_color_count += 1
            if self.selected_color_count > self.max_colors:
                self.enforce_limit()
        else:  # Color deselected
            self.selected_color_count -= 1
    
    def enforce_limit(self):
        """Ensure no more than max_colors are selected"""
        # Count selected items
        selected_count = sum(var.get() for var, _, _ in self.color_vars)
        
        if selected_count > self.max_colors:
            # Deselect the first selected checkbox
            for var, _, _ in self.color_vars:
                if var.get() == 1:
                    var.set(0)
                    self.selected_color_count -= 1
                    break
    
    def get_selected_colors(self):
        """Return list of RGB colors extracted from selected filenames"""
        selected_files = [file for var, file, _ in self.color_vars if var.get() == 1][:self.max_colors]
        all_colors = []
        
        # Process first selected file
        if selected_files:
            colors = parse_color_from_filename(os.path.basename(selected_files[0]))
            
            # First color from first file for Line 1
            if colors:
                all_colors.append(colors[0])
            
            # Second color from first file for Line 2 (if available)
            if len(colors) > 1:
                all_colors.append(colors[1])
            else:
                all_colors.append("#000000")  # Default black
        
        # Process second selected file (only first color used for Line 3)
        if len(selected_files) > 1:
            colors = parse_color_from_filename(os.path.basename(selected_files[1]))
            
            # First color from second file for Line 3
            if colors:
                all_colors.append(colors[0])
            else:
                all_colors.append("#000000")  # Default black
        else:
            # If no second file, use default or second color from first file
            if len(all_colors) > 1:
                all_colors.append(all_colors[1])
            else:
                all_colors.append("#000000")
        
        # Ensure we return exactly 3 colors
        while len(all_colors) < 3:
            all_colors.append("#000000")
            
        return all_colors[:3]
    
    def reset_selection(self):
        """Reset all color selections"""
        for var, _, _ in self.color_vars:
            var.set(0)
        self.selected_color_count = 0
