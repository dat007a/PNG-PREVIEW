import tkinter as tk
from tkinter import ttk, filedialog, Canvas, Button, Frame, Label, Checkbutton, IntVar, StringVar, Scale, HORIZONTAL, messagebox
from font_loader import FontLoader
from color_manager import ColorManager
from image_generator import ImageGenerator
from utils import parse_color_from_filename, load_icon_image, DraggableItem, get_resized_image
from PIL import ImageTk, ImageFont, Image, ImageDraw
from tkinter import filedialog, messagebox
import os
import sys
import platform
import pyautogui
import threading
import time
from pynput import mouse

def find_system_font():
    """
    Find a system font that can be used as a fallback.
    Returns the path to a usable system font or None.
    """
    # Dictionary of common system fonts by platform
    system_fonts = {
        'Windows': [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'verdana.ttf'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'segoeui.ttf'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'calibri.ttf'),
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'tahoma.ttf'),
        ],
        'Darwin': [  # macOS
            '/System/Library/Fonts/SFNS.ttf',
            '/System/Library/Fonts/SFNSText.ttf',
            '/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/Library/Fonts/Verdana.ttf',
        ],
        'Linux': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/Arial.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/ubuntu/Ubuntu-R.ttf',
        ]
    }
    
    # Get the current platform
    current_os = platform.system()
    
    # Check if we have font paths for this platform
    if current_os in system_fonts:
        # Try each font path
        for font_path in system_fonts[current_os]:
            if os.path.exists(font_path):
                return font_path
    
    # If no system font found, return None
    return None

class UIManager:
    def __init__(self, root):
        self.root = root
        self.root.title("CrHashtag Tool")
    
        # Initialize components
        self.font_loader = FontLoader()
        self.color_manager = ColorManager()
        self.image_generator = ImageGenerator()

        # Initialize data structures
        self.paragraphs = []
        self.current_paragraph_index = 0
    
        # Store text images to prevent garbage collection
        self.text_images = {}
    
        # Store font warnings shown to user (to avoid repeated warnings)
        self.font_warnings_shown = set()
    
        # Set up the UI
        self.setup_ui()
    
        # Add the first paragraph by default
        self.add_paragraph()
    
        # If there are existing paragraphs (e.g., from a save file),
        # migrate their effects to the new structure
        if len(self.paragraphs) > 1:
            self.migrate_paragraph_effects()

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb):
        """Convert RGB tuple to hex color"""
        return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

    def darken_color(self, hex_color, factor=2.0):
        """Make a color darker by the given factor"""
        r, g, b = self.hex_to_rgb(hex_color)
    
        # Darken by dividing by factor
        r = max(0, int(r / factor))
        g = max(0, int(g / factor))
        b = max(0, int(b / factor))
    
        return self.rgb_to_hex((r, g, b))

    def lighten_color(self, hex_color, factor=2.0):
        """Make a color lighter by the given factor"""
        r, g, b = self.hex_to_rgb(hex_color)
    
        # Lighten by interpolating toward white (255, 255, 255)
        r = min(255, int(r + (255 - r) * (1 - 1/factor)))
        g = min(255, int(g + (255 - g) * (1 - 1/factor)))
        b = min(255, int(b + (255 - b) * (1 - 1/factor)))
    
        return self.rgb_to_hex((r, g, b))

    def _unbind_mousewheel(self):
        """Unbind mousewheel events"""
        if sys.platform == "win32" or sys.platform == "darwin":
            self.icon_canvas.unbind_all("<MouseWheel>")
        else:  # Linux
            self.icon_canvas.unbind_all("<Button-4>")
            self.icon_canvas.unbind_all("<Button-5>")

    def _on_mousewheel_windows(self, event):
        """Handle Windows mousewheel event"""
        self.icon_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_macos(self, event):
        """Handle macOS mousewheel event"""
        self.icon_canvas.yview_scroll(int(-1 * event.delta), "units")

    def _on_mousewheel_linux_up(self, event):
        """Handle Linux scrolling up event"""
        self.icon_canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(self, event):
        """Handle Linux scrolling down event"""
        self.icon_canvas.yview_scroll(1, "units")

    def _update_canvas_width(self, event, canvas_frame):
        """Update canvas width when parent frame is resized"""
        canvas_width = canvas_frame.winfo_width() - 20  # Account for scrollbar width
        if canvas_width > 0:
            self.icon_canvas.itemconfig(1, width=canvas_width)  # 1 is the id of the first item (our window)
    def _bind_mousewheel(self):
        """Bind mousewheel event for scrolling"""
        # Windows and MacOS have different mousewheel events
        if sys.platform == "win32":
            self.icon_canvas.bind_all("<MouseWheel>", self._on_mousewheel_windows)
        elif sys.platform == "darwin":
            self.icon_canvas.bind_all("<MouseWheel>", self._on_mousewheel_macos)
        else:  # Linux
            self.icon_canvas.bind_all("<Button-4>", self._on_mousewheel_linux_up)
            self.icon_canvas.bind_all("<Button-5>", self._on_mousewheel_linux_down)

    def migrate_paragraph_effects(self):
        """
        Migrate existing paragraphs to the new effects structure.
        This function should be called during initialization.
        """
        for i, paragraph in enumerate(self.paragraphs):
            if 'effects' in paragraph:
                # Check if it's using the old format by looking for direct color values
                if 'shadow_color' in paragraph['effects'] or 'outline_color' in paragraph['effects'] or 'stroke_color' in paragraph['effects']:
                    # Keep the settings, but remove the static colors
                    # They will be calculated dynamically based on each line's text color
                    new_effects = {
                        'shadow': paragraph['effects'].get('shadow', False),
                        'outline': paragraph['effects'].get('outline', False),
                        'stroke': paragraph['effects'].get('stroke', False),
                        'shadow_offset': paragraph['effects'].get('shadow_offset', 3),
                        'outline_width': paragraph['effects'].get('outline_width', 1),
                        'stroke_width': paragraph['effects'].get('stroke_width', 2)
                    }
                    paragraph['effects'] = new_effects

    def update_effect_color_preview(self):
        """Update the color preview in the effects tab"""
        # Clear existing previews
        for widget in self.color_preview_frame.winfo_children():
            widget.destroy()
    
        # Get current paragraph
        paragraph = self.paragraphs[self.current_paragraph_index]
    
        # Create preview for each line
        for i in range(3):
            # Get the color for this line
            color = paragraph['colors'][i] if i < len(paragraph['colors']) else "#000000"
        
            # Convert hex to RGB
            r, g, b = self.hex_to_rgb(color)
        
            # Calculate effect colors
            stroke_color = self.darken_color(color, 2.0)  # 2× darker
            outline_color = self.lighten_color(color, 2.0)  # 2× lighter
            shadow_color = self.lighten_color(color, 3.0)  # 3× lighter
        
            # Create preview frame for this line
            line_frame = Frame(self.color_preview_frame)
            line_frame.pack(fill=tk.X, pady=5)
        
            Label(line_frame, text=f"Line {i+1}:", width=10).pack(side=tk.LEFT)
        
            # Text color
            text_preview = Frame(line_frame, width=30, height=20, bg=color)
            text_preview.pack(side=tk.LEFT, padx=5)
            Label(line_frame, text=f"Text: {color}").pack(side=tk.LEFT, padx=5)
        
            # Stroke color
            stroke_preview = Frame(line_frame, width=30, height=20, bg=stroke_color)
            stroke_preview.pack(side=tk.LEFT, padx=5)
            Label(line_frame, text=f"Stroke: {stroke_color}").pack(side=tk.LEFT, padx=5)
        
            # Outline color
            outline_preview = Frame(line_frame, width=30, height=20, bg=outline_color)
            outline_preview.pack(side=tk.LEFT, padx=5)
            Label(line_frame, text=f"Outline: {outline_color}").pack(side=tk.LEFT, padx=5)
        
            # Shadow color
            shadow_preview = Frame(line_frame, width=30, height=20, bg=shadow_color)
            shadow_preview.pack(side=tk.LEFT, padx=5)
            Label(line_frame, text=f"Shadow: {shadow_color}").pack(side=tk.LEFT, padx=5)

    # Find this function around line 950 in ui_manager_module.py
# Either remove this function entirely, or replace it with the version below that includes line_index parameter

    def render_text_with_font(self, text, font_file, size, color, effects=None, line_index=0):
        """
        Render text with a specific font to an image
    
        Parameters:
        - text: The text to render
        - font_file: The TTF file name
        - size: Font size
        - color: Text color (hex)
        - effects: Dictionary of effects to apply
        - line_index: Index of the line (0, 1, or 2) for line-specific effects
    
        Returns:
        - ImageTk.PhotoImage object
        """
        if not text:
            return None
        
        try:
            # Load the TTF font
            font_path = os.path.join("FONT MAP", font_file)
        
            # Verify font file exists
            if not os.path.exists(font_path):
                print(f"Font file not found: {font_path}")
            
                # Show warning dialog only once per font
                if font_file not in self.font_warnings_shown:
                    messagebox.showwarning(
                        "Font Not Found", 
                        f"The font '{font_file}' could not be found in the FONT MAP directory.\n"
                        "A fallback font will be used instead."
                    )
                    # Mark as shown to avoid repeated warnings
                    self.font_warnings_shown.add(font_file)
                
                raise FileNotFoundError(f"Font file not found: {font_path}")
            
            # Get font and handle potential errors
            try:
                font = ImageFont.truetype(font_path, size)
            except Exception as e:
                print(f"Failed to load font {font_path}: {e}")
                # Try system font as fallback if available
                try:
                    # Try to find a system font as fallback
                    system_font_path = find_system_font()
                
                    if system_font_path:
                        font = ImageFont.truetype(system_font_path, size)
                        print(f"Using system font as fallback: {system_font_path}")
                    else:
                        # Last resort: use default font
                        font = ImageFont.load_default()
                        print("Using default font as final fallback")
                except Exception:
                    # Absolute last resort
                    font = ImageFont.load_default()
                    print("Using PIL default font as final fallback")
        
            # Get text dimensions using getbbox() (more reliable than getsize)
            try:
                # Try to use getbbox() for newer PIL versions
                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                # Fall back to getsize() for older PIL versions
                try:
                    text_width, text_height = font.getsize(text)
                except Exception as e:
                    print(f"Error measuring text: {e}")
                    # Estimate dimensions as fallback
                    text_width = len(text) * size // 2
                    text_height = size + 4
        
            # Add padding and space for effects
            padding = 20
            effect_padding = 10 if effects else 0

            # Thêm chiều cao để tránh bị cắt phần descender (g, y, p...)
            descender_fix = int(size * 0.3)  # Khoảng 30% font size

            width = text_width + padding * 2 + effect_padding * 2
            height = text_height + padding * 2 + effect_padding * 2 + descender_fix

        
            # Create a transparent image
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
        
            # Get positions
            x, y = padding + effect_padding, padding + effect_padding
        
            # Apply effects if requested
            if effects:
                # Calculate line-specific effect colors based on the current text color
                effect_colors = {
                    'shadow_color': self.lighten_color(color, 3.0),  # 3× lighter
                    'outline_color': self.lighten_color(color, 2.0), # 2× lighter
                    'stroke_color': self.darken_color(color, 2.0)    # 2× darker
                }
            
                # Shadow effect
                if effects.get('shadow'):
                    shadow_color = effect_colors['shadow_color']
                    offset = effects.get('shadow_offset', 3)
                    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)
            
                # Stroke effect (darker than text)
                if effects.get('stroke'):
                    stroke_color = effect_colors['stroke_color']
                    width = effects.get('stroke_width', 2)
                    for dx in range(-width, width + 1):
                        for dy in range(-width, width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
            
                # Outline effect (brighter than text)
                if effects.get('outline'):
                    outline_color = effect_colors['outline_color']
                    width = effects.get('outline_width', 1)
                    for dx in range(-width, width + 1):
                        for dy in range(-width, width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
            # Draw the main text
            draw.text((x, y), text, font=font, fill=color)
        
            # Convert to PhotoImage for Tkinter
            photo_img = ImageTk.PhotoImage(img)
            return photo_img
        
        except Exception as e:
            print(f"Error rendering text with font {font_file}: {e}")
        
            # Create fallback image with error message
            img = Image.new('RGBA', (400, 50), (255, 255, 255, 200))
            draw = ImageDraw.Draw(img)
            fallback_font = ImageFont.load_default()
            draw.text((10, 10), f"Font Error: {text}", fill="#FF0000", font=fallback_font)
            return ImageTk.PhotoImage(img)
    
    
    def setup_icon_search(self, parent_frame):
        """Set up the icon search area for vertical layout with improved scrolling"""
        # Create a vertical layout for the search panel
        search_frame = Frame(parent_frame)
        search_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        # Search header
        Label(search_frame, text="Icon Search", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
        # Search input area
        search_input_frame = Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=5)
    
        self.icon_search_var = StringVar()
        search_entry = ttk.Entry(search_input_frame, textvariable=self.icon_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<Return>", lambda e: self.search_icons())
    
        Button(search_input_frame, text="Search", command=self.search_icons).pack(side=tk.RIGHT, padx=5)
    
        # Create a frame for search results with vertical scrolling
        results_frame = Frame(search_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
        # Canvas with scrollbar for results - IMPROVED SCROLLING SETUP
        canvas_frame = Frame(results_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
    
        # Create canvas with full height to fill the available space
        self.icon_canvas = tk.Canvas(canvas_frame)
        self.icon_canvas.pack_propagate(False)  # Prevent canvas from resizing according to contents
    
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.icon_canvas.yview)
        self.icon_scrollable_frame = Frame(self.icon_canvas)
    
        # Make scrollable frame fill the width of canvas
        self.icon_scrollable_frame.pack(fill=tk.BOTH, expand=True)
    
        # Configure scrollable frame to update canvas scroll region
        self.icon_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        )
    
        # Create window within canvas
        self.icon_canvas.create_window((0, 0), window=self.icon_scrollable_frame, anchor="nw", width=canvas_frame.winfo_width()-20)
        self.icon_canvas.configure(yscrollcommand=scrollbar.set)
    
        # Pack canvas and scrollbar
        self.icon_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Bind mousewheel events to the canvas for better scrolling
        self.icon_canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.icon_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())
    
        # Bind resize event to update canvas width
        parent_frame.bind("<Configure>", lambda e: self._update_canvas_width(e, canvas_frame))
    
        # Store references to icon images
        self.icon_images = []
    
        # Initial message
        self.no_results_label = Label(self.icon_scrollable_frame, text="Search for icons to display results")
        self.no_results_label.pack(pady=10)


    def search_icons(self):
        """Enhanced search for icons in the ICONS directory with improved matching"""
        # Clear previous results
        for widget in self.icon_scrollable_frame.winfo_children():
            widget.destroy()
    
        self.icon_images = []  # Clear stored image references
    
        # Get search terms
        search_text = self.icon_search_var.get().strip().lower()
        if not search_text:
            self.no_results_label = Label(self.icon_scrollable_frame, text="Please enter search terms")
            self.no_results_label.pack(pady=10)
            return
    
        search_terms = search_text.split()
    
        # Check if ICONS directory exists
        if not os.path.exists('ICONS'):
            os.makedirs('ICONS')
            self.no_results_label = Label(self.icon_scrollable_frame, 
                                 text="ICONS directory created. Please add icon files.")
            self.no_results_label.pack(pady=10)
            return
    
        # Find matching icons with improved scoring
        icon_files = []
        for filename in os.listdir('ICONS'):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                # Extract filename without extension for matching
                file_base = os.path.splitext(filename)[0].lower()
                file_words = set(file_base.replace('_', ' ').replace('-', ' ').split())
            
                # Initialize match metrics
                match_score = 0
                matching_terms = []
                match_positions = []
            
                # Score calculation factors
                exact_phrase_bonus = 50  # Bonus for matching the exact phrase
                word_match_score = 10    # Score for each matching word
                consecutive_bonus = 5    # Bonus for consecutive matches
                start_bonus = 3          # Bonus if match is at the start
            
                # Check for exact phrase match (highest priority)
                if search_text in file_base:
                    match_score += exact_phrase_bonus
                    match_positions.append(file_base.index(search_text))
                
                # Check individual word matches and their positions
                for term in search_terms:
                    if term in file_base:
                        match_score += word_match_score
                        matching_terms.append(term)
                        match_positions.append(file_base.index(term))
                    elif term in file_words:  # Match whole word
                        match_score += word_match_score + 2
                        matching_terms.append(term)
            
                # Check for partial word matches (if no exact matches)
                if not matching_terms:
                    for term in search_terms:
                        # Find similar words with character overlap > 60%
                        for word in file_words:
                            if len(term) >= 3 and len(word) >= 3:
                                # Simple character overlap calculation
                                overlap = sum(1 for c in term if c in word) / max(len(term), len(word))
                                if overlap > 0.6:  # Over 60% character match
                                    match_score += word_match_score * overlap
                                    matching_terms.append(f"{term}~{word}")
            
                # Bonus for consecutive terms
                if len(match_positions) > 1:
                    match_positions.sort()
                    for i in range(len(match_positions)-1):
                        if match_positions[i+1] - match_positions[i] < 2 + len(search_terms[i]):
                            match_score += consecutive_bonus
            
                # Bonus if match is at the start of filename
                if match_positions and min(match_positions) < 3:
                    match_score += start_bonus
                
                # Only add if there's at least one match or similarity
                if match_score > 0:
                    icon_files.append((filename, match_score, matching_terms))
    
        # Sort by score (highest first)
        icon_files.sort(key=lambda x: x[1], reverse=True)
    
        if not icon_files:
            self.no_results_label = Label(self.icon_scrollable_frame, text="No matching icons found")
            self.no_results_label.pack(pady=10)
            return
    
        # Display ALL results with improved UI
        self.display_icon_results(icon_files)

    def display_icon_results(self, icon_files):
        """Display icon search results with improved visual cues for match quality"""
        # Clear existing results
        for widget in self.icon_scrollable_frame.winfo_children():
            widget.destroy()
    
        # Create a frame for the results
        results_frame = Frame(self.icon_scrollable_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)
    
        # Create filter options
        filter_frame = Frame(results_frame, pady=5)
        filter_frame.pack(fill=tk.X, pady=5)
    
        Label(filter_frame, text=f"Found {len(icon_files)} icons", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
    
        # Add sort options
        sort_options = ["Relevance (default)", "Filename A-Z", "Filename Z-A"]
        sort_var = StringVar(value=sort_options[0])
        sort_dropdown = ttk.Combobox(filter_frame, textvariable=sort_var, values=sort_options, width=18, state="readonly")
        sort_dropdown.pack(side=tk.RIGHT, padx=5)
        Label(filter_frame, text="Sort by:").pack(side=tk.RIGHT, padx=2)
    
        # Add event handling for sort dropdown
        def on_sort_change(event):
            sort_option = sort_var.get()
        
            sorted_icons = icon_files.copy()
            if sort_option == "Filename A-Z":
                sorted_icons.sort(key=lambda x: x[0].lower())
            elif sort_option == "Filename Z-A":
                sorted_icons.sort(key=lambda x: x[0].lower(), reverse=True)
            # Default is already sorted by relevance
        
            # Re-display the results with the new sort order
            for widget in results_container.winfo_children():
                widget.destroy()
            
            display_items(sorted_icons)
        
        sort_dropdown.bind("<<ComboboxSelected>>", on_sort_change)
    
        # Create a scrollable container for the results
        results_container = Frame(results_frame)
        results_container.pack(fill=tk.BOTH, expand=True, pady=5)
    
        def display_items(items):
            # Display each icon with improved visuals
            for i, (filename, score, matching_terms) in enumerate(items):
                # Determine the background color based on relevance score
                bg_color = "#f0f8ff"  # Default light blue
                if score > 30:  # High relevance
                    bg_color = "#e6f2ff"
                elif score < 15:  # Low relevance
                    bg_color = "#f7f7f7"
                
                # Create cell frame with score-based background
                cell_frame = Frame(results_container, borderwidth=1, relief="solid", padx=5, pady=5, bg=bg_color)
                cell_frame.pack(fill=tk.X, padx=5, pady=5)
        
                try:
                    # Create a horizontal layout within each cell for the icon and buttons
                    icon_layout = Frame(cell_frame, bg=bg_color)
                    icon_layout.pack(fill=tk.X)
            
                    # Left side - icon and filename
                    icon_info = Frame(icon_layout, bg=bg_color)
                    icon_info.pack(side=tk.LEFT)
            
                    # Load and resize the icon
                    img_path = os.path.join('ICONS', filename)
                    img = Image.open(img_path)
                    img = img.resize((50, 50), Image.LANCZOS)
                    photo_img = ImageTk.PhotoImage(img)
            
                    # Store reference to prevent garbage collection
                    self.icon_images.append(photo_img)
                
                    # Display the image
                    img_label = Label(icon_info, image=photo_img, bg=bg_color)
                    img_label.pack(side=tk.LEFT, padx=5)
            
                    # Display the filename and match information
                    name_frame = Frame(icon_info, bg=bg_color)
                    name_frame.pack(side=tk.LEFT, padx=5)
            
                    # Truncate filename if needed
                    display_name = filename
                    if len(display_name) > 25:
                        display_name = display_name[:22] + "..."
            
                    # Show score for debugging (can be removed in production)
                    score_display = f" (Score: {score})" if score > 0 else ""
                    name_label = Label(name_frame, text=display_name + score_display, 
                                       anchor="w", bg=bg_color, font=("Arial", 9, "bold"))
                    name_label.pack(anchor=tk.W)
            
                    # Display matching terms with better formatting
                    if matching_terms:
                        # Format matching terms with ~ for fuzzy matches
                        formatted_terms = []
                        for term in matching_terms:
                            if "~" in term:  # Fuzzy match
                                search, match = term.split("~")
                                formatted_terms.append(f"{search}≈{match}")
                            else:
                                formatted_terms.append(term)
                            
                        match_text = "Matched: " + ", ".join(formatted_terms)
                        # Use a different text color based on score
                        fg_color = "#006600" if score > 30 else "#666666"
                        match_label = Label(name_frame, text=match_text, font=("Arial", 8), 
                                          fg=fg_color, bg=bg_color)
                        match_label.pack(anchor=tk.W)
            
                    # Right side - selection buttons
                    button_frame = Frame(icon_layout, bg=bg_color)
                    button_frame.pack(side=tk.RIGHT)
            
                    # Use ttk buttons for better look
                    Button(button_frame, text="Big Icon", 
                          command=lambda f=img_path: self.select_icon(f, 'big_icon')).pack(side=tk.LEFT, padx=2)
                    Button(button_frame, text="Small Icon", 
                          command=lambda f=img_path: self.select_icon(f, 'small_icon')).pack(side=tk.LEFT, padx=2)
            
                    # Add a quick preview button that shows larger preview on hover
                    preview_btn = Button(button_frame, text="👁️", width=2)
                    preview_btn.pack(side=tk.LEFT, padx=2)
                
                    # Create tooltip/preview functionality
                    preview_window = None
                
                    def show_preview(event):
                        nonlocal preview_window
                        # Create a toplevel window for preview
                        x, y = event.x_root, event.y_root
                        preview_window = tk.Toplevel(self.root)
                        preview_window.wm_overrideredirect(True)
                        preview_window.wm_geometry(f"+{x+10}+{y+10}")
                    
                        # Load larger preview
                        preview_img = Image.open(img_path)
                        max_size = (200, 200)
                        preview_img.thumbnail(max_size, Image.LANCZOS)
                        photo = ImageTk.PhotoImage(preview_img)
                    
                        # Store reference to prevent garbage collection
                        self.icon_images.append(photo)
                    
                        # Display preview
                        label = Label(preview_window, image=photo, borderwidth=2, relief="solid")
                        label.image = photo
                        label.pack()
                
                    def hide_preview(event):
                        nonlocal preview_window
                        if preview_window:
                            preview_window.destroy()
                            preview_window = None
                
                    preview_btn.bind("<Enter>", show_preview)
                    preview_btn.bind("<Leave>", hide_preview)
            
                except Exception as e:
                    print(f"Error loading icon {filename}: {e}")
                    Label(cell_frame, text=f"Error: {filename}", bg=bg_color).pack(pady=5)
    
        # Initial display
        display_items(icon_files)
    
        # Explicitly update the canvas scroll region after all items are added
        self.icon_canvas.update_idletasks()
        self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        self.icon_canvas.yview_moveto(0)  # Scroll to top after loading results
        
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling for the icon canvas"""
        self.icon_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def select_icon(self, file_path, icon_type):
        """Select an icon from search results"""
        # Save current paragraph data
        self.save_paragraph_data()
    
        # Load the icon
        icon = load_icon_image(file_path)
        if icon:
            self.paragraphs[self.current_paragraph_index]['icons'][icon_type] = icon
        
            # Update preview
            self.update_preview()


    def export_all_images(self):
        """Xuất ảnh PNG cho tất cả các paragraph đang active"""
        self.save_all_paragraphs_data()

        active_paragraphs = [
            p for p in self.paragraphs 
            if p.get('active') and any(line.strip() for line in p.get('text_lines', []))
        ]

        if not active_paragraphs:
            messagebox.showinfo("Không có nội dung", "Không có paragraph nào đang bật (active).")
            return

        if not os.path.exists("OUTPUT"):
            os.makedirs("OUTPUT")

        for idx, paragraph in enumerate(active_paragraphs):
            filename = os.path.join("OUTPUT", f"CrHashtag_P{idx+1}.png")
            self.image_generator.generate_image([paragraph], filename)

        messagebox.showinfo("Export hoàn tất", f"Đã xuất {len(active_paragraphs)} ảnh vào thư mục OUTPUT.")

    
    def update_preview(self):
        """Update the preview canvas with current paragraph data and line-specific effects"""
        # Clear canvas and references to images
        self.preview_canvas.delete("all")
    
        # Draw alignment grid
        grid_spacing = 50  # or 100 as you prefer
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        # Vertical lines
        for x in range(0, canvas_width, grid_spacing):
            self.preview_canvas.create_line(x, 0, x, canvas_height, fill="#dddddd")

        # Horizontal lines
        for y in range(0, canvas_height, grid_spacing):
            self.preview_canvas.create_line(0, y, canvas_width, y, fill="#dddddd")

        self.text_images = {}
    
        # Add border
        self.preview_canvas.create_rectangle(2, 2, 798, 798, outline="#cccccc", width=2)
    
        if not self.paragraphs:
            return
        
        # Save current paragraph data first
        self.save_paragraph_data()
    
        paragraph = self.paragraphs[self.current_paragraph_index]
    
        # Get selected fonts
        selected_fonts = paragraph['fonts']
    
        # Check if we need fonts but none are selected - show a reminder on the canvas
        non_empty_lines = [i for i, text in enumerate(paragraph['text_lines']) if text.strip()]
        if non_empty_lines and not selected_fonts:
            reminder_img = Image.new('RGBA', (400, 60), (255, 255, 230, 220))
            draw = ImageDraw.Draw(reminder_img)
            fallback_font = ImageFont.load_default()
            draw.text((20, 10), "Please select fonts in the Fonts tab", fill="#CC0000", font=fallback_font)
            draw.text((20, 30), "to display your text lines properly.", fill="#CC0000", font=fallback_font)
        
            reminder_photo = ImageTk.PhotoImage(reminder_img)
            self.text_images['font_reminder'] = reminder_photo
            self.preview_canvas.create_image(100, 50, image=reminder_photo, anchor='nw')
    
        # Track draggable items
        draggable_items = {}
    
        # Draw text lines using PIL to render with actual fonts
        for i, text in enumerate(paragraph['text_lines']):
            if not text:
                continue
            
            # Get specific font for this line
            font_file = None
            if i < len(selected_fonts):
                font_file = selected_fonts[i]
            elif selected_fonts:
                font_file = selected_fonts[0]
            else:
                # Display a warning if no font is selected but there's text to display
                warning_img = Image.new('RGBA', (300, 30), (255, 240, 240, 220))
                draw = ImageDraw.Draw(warning_img)
                fallback_font = ImageFont.load_default()
                draw.text((10, 10), f"No font selected for Line {i+1}", fill="#FF0000", font=fallback_font)
                warning_photo = ImageTk.PhotoImage(warning_img)
                self.text_images[f'warning{i}'] = warning_photo
            
                # Display warning at line position
                x, y = paragraph['positions'][f'text{i}']
                self.preview_canvas.create_image(x, y, image=warning_photo, anchor='nw', tags=f"text{i}")
                continue
            
            # Get font size and position
            font_size = paragraph['font_sizes'][f'text{i}']
            x, y = paragraph['positions'][f'text{i}']
        
            # Get color
            color = paragraph['colors'][i] if i < len(paragraph['colors']) else "#000000"
        
            # Render text with font as image - pass the line index for line-specific effects
            text_img = self.render_text_with_font(
                text, 
                font_file, 
                font_size, 
                color,
                paragraph['effects'] if any([
                    paragraph['effects'].get('shadow', False),
                    paragraph['effects'].get('outline', False),
                    paragraph['effects'].get('stroke', False)
                ]) else None,
                i  # Pass the line index
            )
        
            if text_img:
                # Store reference to prevent garbage collection
                self.text_images[f'text{i}'] = text_img
            
                # Display image on canvas
                item_id = self.preview_canvas.create_image(
                    x, y, image=text_img, anchor='nw', tags=f"text{i}"
                )
            
                # Make draggable
                draggable_items[f"text{i}"] = DraggableItem(
                    self.preview_canvas, 
                    item_id, 
                    f"text{i}", 
                    lambda t, x, y: self.update_element_position(t, x, y)
                )
            
                # Add drag bindings
                self.preview_canvas.tag_bind(
                    f"text{i}", "<ButtonPress-1>", 
                    lambda event, item=draggable_items[f"text{i}"]: item.on_drag_start(event)
                )
                self.preview_canvas.tag_bind(
                    f"text{i}", "<B1-Motion>",
                    lambda event, item=draggable_items[f"text{i}"]: item.on_drag_motion(event)
                )
                self.preview_canvas.tag_bind(
                    f"text{i}", "<ButtonRelease-1>",
                    lambda event, item=draggable_items[f"text{i}"]: item.on_drag_end(event)
                )
        
        # Draw small icon
        small_icon = paragraph['icons'].get('small_icon')
        if small_icon:
            # Get position and size
            x, y = paragraph['positions']['small_icon']
            size = paragraph['icon_sizes']['small_icon']
        
            # Resize for preview
            small_icon_resized = get_resized_image(small_icon, size[0], size[1])
            self.paragraphs[self.current_paragraph_index]['icons']['small_icon_resized'] = small_icon_resized
            print("[PREVIEW] Small icon resized to:", small_icon_resized.size, "at", x, y)

        
            if small_icon_resized:
                # Convert to PhotoImage
                small_icon_photo = ImageTk.PhotoImage(small_icon_resized)
            
                # Store reference to prevent garbage collection
                self.text_images['small_icon_photo'] = small_icon_photo
            
                # Create image on canvas
                item_id = self.preview_canvas.create_image(
                    x, y, image=small_icon_photo, anchor='nw', tags="small_icon"
                )
            
                # Make draggable
                draggable_items["small_icon"] = DraggableItem(
                    self.preview_canvas, 
                    item_id, 
                    "small_icon", 
                    lambda t, x, y: self.update_element_position(t, x, y)
                )
            
                # Add drag bindings
                self.preview_canvas.tag_bind(
                    "small_icon", "<ButtonPress-1>", 
                    lambda event, item=draggable_items["small_icon"]: item.on_drag_start(event)
                )
                self.preview_canvas.tag_bind(
                    "small_icon", "<B1-Motion>",
                    lambda event, item=draggable_items["small_icon"]: item.on_drag_motion(event)
                )
                self.preview_canvas.tag_bind(
                    "small_icon", "<ButtonRelease-1>",
                    lambda event, item=draggable_items["small_icon"]: item.on_drag_end(event)
                )
    
        # Draw big icon
        big_icon = paragraph['icons'].get('big_icon')
        if big_icon:
            # Get position and size
            x, y = paragraph['positions']['big_icon']
            size = paragraph['icon_sizes']['big_icon']
        
            # Resize for preview
            big_icon_resized = get_resized_image(big_icon, size[0], size[1])
            self.paragraphs[self.current_paragraph_index]['icons']['big_icon_resized'] = big_icon_resized
            print("[PREVIEW] Big icon resized to:", big_icon_resized.size, "at", x, y)

        
            if big_icon_resized:
                # Convert to PhotoImage
                big_icon_photo = ImageTk.PhotoImage(big_icon_resized)
            
                # Store reference to prevent garbage collection
                self.text_images['big_icon_photo'] = big_icon_photo
            
                # Create image on canvas
                item_id = self.preview_canvas.create_image(
                    x, y, image=big_icon_photo, anchor='nw', tags="big_icon"
                )
            
                # Make draggable
                draggable_items["big_icon"] = DraggableItem(
                    self.preview_canvas, 
                    item_id, 
                    "big_icon", 
                    lambda t, x, y: self.update_element_position(t, x, y)
                )
            
                # Add drag bindings
                self.preview_canvas.tag_bind(
                    "big_icon", "<ButtonPress-1>", 
                    lambda event, item=draggable_items["big_icon"]: item.on_drag_start(event)
                )
                self.preview_canvas.tag_bind(
                    "big_icon", "<B1-Motion>",
                    lambda event, item=draggable_items["big_icon"]: item.on_drag_motion(event)
                )
                self.preview_canvas.tag_bind(
                    "big_icon", "<ButtonRelease-1>",
                    lambda event, item=draggable_items["big_icon"]: item.on_drag_end(event)
                )
    
    def setup_ui(self):
        """Set up the main user interface"""
        # Create main frame
        main_frame = Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create control frame at the top
        control_frame = Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add paragraph controls
        Button(control_frame, text="Add Paragraph", command=self.add_paragraph).pack(side=tk.LEFT, padx=5)
        Button(control_frame, text="Reset All", command=self.reset_all).pack(side=tk.LEFT, padx=5)
        Button(control_frame, text="Import Text File", command=self.import_text_file).pack(side=tk.LEFT, padx=5)

        # Paragraph selector
        self.paragraph_selector_label = Label(control_frame, text="Current Paragraph:")
        self.paragraph_selector_label.pack(side=tk.LEFT, padx=5)
        
        self.paragraph_selector = ttk.Combobox(control_frame, width=30, state="readonly")
        self.paragraph_selector.pack(side=tk.LEFT, padx=5)
        self.paragraph_selector.bind("<<ComboboxSelected>>", self.on_paragraph_selected)
        
        # Delete button
        self.delete_btn = Button(control_frame, text="Delete Paragraph", command=self.delete_current_paragraph)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Create the notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create tabs
        self.text_tab = ttk.Frame(self.notebook)
        self.font_tab = ttk.Frame(self.notebook)
        self.color_tab = ttk.Frame(self.notebook)
        self.effects_tab = ttk.Frame(self.notebook)
        self.layout_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.text_tab, text='Text')
        self.notebook.add(self.font_tab, text='Fonts')
        self.notebook.add(self.color_tab, text='Colors')
        self.notebook.add(self.effects_tab, text='Effects')
        self.notebook.add(self.layout_tab, text='Layout')
        
        # Setup each tab
        self.setup_text_tab()
        self.setup_effects_tab()
        self.setup_layout_tab()
        
        # Load fonts and colors
        self.font_loader.load_fonts()
        self.setup_fonts_tab()  # Custom method to create 2-column layout
        
        self.color_manager.load_colors()
        self.color_manager.display_colors(self.color_tab, [])
        self.setup_color_picker_section()

        
        # Create bottom button frame
        bottom_frame = Frame(main_frame)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Add generate button
        Button(bottom_frame, text="Generate PNG", command=self.generate_image).pack(side=tk.RIGHT, padx=5)
    
    def setup_text_tab(self):
        """Set up the text input tab"""
        # Create frame for text inputs
        text_frame = Frame(self.text_tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Add explanatory text
        Label(text_frame, text="Enter text for each line:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Create text inputs
        self.text_inputs = []
        for i in range(3):
            line_frame = Frame(text_frame)
            line_frame.pack(fill=tk.X, pady=5)
            
            Label(line_frame, text=f"Line {i+1}:", width=10).pack(side=tk.LEFT)
            entry = ttk.Entry(line_frame, width=80)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.text_inputs.append(entry)
    
    def setup_effects_tab(self):
        """Set up the effects tab with line-specific color effects"""
        effects_frame = Frame(self.effects_tab)
        effects_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
        # Add title
        Label(effects_frame, text="Text Effects", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
        # Add explanation
        Label(effects_frame, text="Each effect will automatically calculate colors based on the selected text color for each line.", 
              justify=tk.LEFT, wraplength=600).pack(anchor=tk.W, pady=(0, 10))
    
        # Create effect options
        self.effect_vars = {
            'shadow': IntVar(),
            'outline': IntVar(),
            'stroke': IntVar()
        }
    
        # Shadow effect
        shadow_frame = Frame(effects_frame)
        shadow_frame.pack(fill=tk.X, pady=5)
    
        Checkbutton(shadow_frame, text="Drop Shadow (3× lighter than text color)", 
                   variable=self.effect_vars['shadow']).pack(side=tk.LEFT)
    
        Label(shadow_frame, text="Offset:").pack(side=tk.LEFT, padx=(20, 5))
        self.shadow_offset = Scale(shadow_frame, from_=1, to=10, orient=HORIZONTAL, length=100)
        self.shadow_offset.set(3)
        self.shadow_offset.pack(side=tk.LEFT)
    
        # Outline effect
        outline_frame = Frame(effects_frame)
        outline_frame.pack(fill=tk.X, pady=5)
    
        Checkbutton(outline_frame, text="Outline (2× lighter than text color)", 
                   variable=self.effect_vars['outline']).pack(side=tk.LEFT)
    
        Label(outline_frame, text="Width:").pack(side=tk.LEFT, padx=(20, 5))
        self.outline_width = Scale(outline_frame, from_=1, to=5, orient=HORIZONTAL, length=100)
        self.outline_width.set(1)
        self.outline_width.pack(side=tk.LEFT)
    
        # Stroke effect
        stroke_frame = Frame(effects_frame)
        stroke_frame.pack(fill=tk.X, pady=5)
    
        Checkbutton(stroke_frame, text="Stroke (2× darker than text color)", 
                   variable=self.effect_vars['stroke']).pack(side=tk.LEFT)
    
        Label(stroke_frame, text="Width:").pack(side=tk.LEFT, padx=(20, 5))
        self.stroke_width = Scale(stroke_frame, from_=1, to=5, orient=HORIZONTAL, length=100)
        self.stroke_width.set(2)
        self.stroke_width.pack(side=tk.LEFT)
    
        # Effects preview section
        preview_frame = Frame(effects_frame)
        preview_frame.pack(fill=tk.X, pady=10)
    
        Label(preview_frame, text="Preview of effect calculations:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
        # Create a frame to display color previews for each line
        self.color_preview_frame = Frame(preview_frame)
        self.color_preview_frame.pack(fill=tk.X, pady=5)
    
        # Preview button
        Button(effects_frame, text="Apply Effects & Update Preview", command=self.update_preview).pack(pady=20)
    
    def setup_fonts_tab(self):
        """Set up fonts tab with 3 columns"""
        fonts_frame = Frame(self.font_tab)
        fonts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add title
        Label(fonts_frame, text="Available Fonts", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)

        # Create a frame to hold grid layout
        grid_frame = Frame(fonts_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        all_fonts = self.font_loader.fonts
        num_columns = 3

        for i, font_name in enumerate(all_fonts):
            row = i // num_columns
            col = i % num_columns

            cell_frame = Frame(grid_frame)
            cell_frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")

            self.create_font_item(cell_frame, font_name, i)

        # Add instructions
        instruction = Label(fonts_frame, text="Select up to 3 fonts", font=("Arial", 10))
        instruction.pack(side=tk.BOTTOM, pady=10)

    def setup_color_picker_section(self):
        """Add color picker widgets for manual color selection"""
        picker_frame = Frame(self.color_tab)
        picker_frame.pack(fill=tk.X, padx=20, pady=10)

        Label(picker_frame, text="🎨 Chọn màu thủ công (theo dòng):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.manual_colors = ["#000000", "#000000", "#000000"]  # default black

        self.color_pickers = []
        for i in range(3):
            line_frame = Frame(picker_frame)
            line_frame.pack(fill=tk.X, pady=5)

            Label(line_frame, text=f"Line {i+1}:", width=10).pack(side=tk.LEFT)

            color_var = StringVar(value=self.manual_colors[i])
            color_entry = ttk.Entry(line_frame, textvariable=color_var, width=10)
            color_entry.pack(side=tk.LEFT, padx=5)

            def open_picker(idx=i, var=color_var):
                from tkinter import colorchooser
                color_code = colorchooser.askcolor(title=f"Chọn màu cho dòng {idx+1}")
                if color_code and color_code[1]:
                    var.set(color_code[1])
                    self.manual_colors[idx] = color_code[1]

            Button(line_frame, text="Pick", command=open_picker).pack(side=tk.LEFT, padx=5)
            Button(line_frame, text="🧲 Eyedrop", command=lambda idx=i, var=color_var: self.pick_color_from_screen(var, idx)).pack(side=tk.LEFT, padx=5)
            self.color_pickers.append(color_var)

    def pick_color_from_screen(self, var, idx):
        """Eyedropper bằng cách click trái chuột ở bất kỳ đâu trên màn hình"""
        def grab_color():
            try:
                self.root.iconify()  # Thu nhỏ cửa sổ để không che vùng chọn
                messagebox.showinfo("Eyedropper", "Rê chuột đến màu cần lấy và CLICK TRÁI.\nẤn ESC nếu muốn hủy.")

                def on_click(x, y, button, pressed):
                    if pressed and button == mouse.Button.left:
                        pixel_color = pyautogui.screenshot().getpixel((x, y))
                        hex_color = '#%02x%02x%02x' % pixel_color
                        var.set(hex_color)  # Cập nhật màu vào color picker
                        self.manual_colors[idx] = hex_color
                    
                        # Xóa giá trị trong color picker để có thể quay lại nhập màu thủ công
                        self.color_pickers[idx].set("#000000")  # Reset lại màu cho phép nhập thủ công

                        print(f"[Eyedropper] Chọn màu tại ({x}, {y}): {hex_color}")
                        listener.stop()

                    elif pressed and button == mouse.Button.right:
                        print("[Eyedropper] Đã hủy bằng chuột phải.")
                        listener.stop()

                with mouse.Listener(on_click=on_click) as listener:
                    listener.join()

            except Exception as e:
                print("Eyedropper error:", e)
                messagebox.showerror("Eyedropper Error", str(e))
            finally:
                self.root.deiconify()
                self.root.config(cursor="")

            # Đặt lại con trỏ và cho phép nhập màu thủ công
            self.color_pickers[idx].set("#000000")  # Set lại để bạn có thể nhập lại màu thủ công nếu muốn

        threading.Thread(target=grab_color).start()


    
    def create_font_item(self, parent, font_name, index):
        """Create a font selection item with preview"""
        try:
            # Create frame for font item
            font_frame = Frame(parent)
            font_frame.pack(fill=tk.X, pady=2)
            
            # Create and save preview image
            font_path = os.path.join('FONT MAP', font_name)
            preview_img = self.font_loader.create_font_preview(font_path)
            
            # Preview image
            if preview_img:
                preview_label = Label(font_frame, image=preview_img)
                preview_label.image = preview_img  # Keep reference
                preview_label.pack(side=tk.LEFT, padx=5)
            
            # Truncate long font names
            display_name = font_name
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            
            # Font name label with tooltip
            name_label = Label(font_frame, text=display_name, width=25, anchor="w")
            name_label.pack(side=tk.LEFT, padx=5)
            self.create_tooltip(name_label, font_name)
            
            # Checkbox
            var = IntVar()
            chk = Checkbutton(
                font_frame, 
                variable=var,
                command=lambda v=var, f=font_name: self.font_loader.on_font_selected(v, f)
            )
            chk.pack(side=tk.LEFT, padx=5)
            
            self.font_loader.font_vars.append((var, font_name, chk))
            
        except Exception as e:
            print(f"Error creating font item {font_name}: {e}")
    
    def setup_layout_tab(self):
        """Set up the layout tab with preview canvas and icon search side-by-side"""
        layout_frame = Frame(self.layout_tab)
        layout_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create horizontal split for left panel (icon search) and right panel (preview)
        split_frame = Frame(layout_frame)
        split_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for icon search (Increase width by 80px)
        left_panel = Frame(split_frame, borderwidth=1, relief="solid", width=330)  # Increase width to 330px
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)
        left_panel.pack_propagate(False)  # Prevent the frame from shrinking

        # Set up the icon search in the left panel
        self.setup_icon_search(left_panel)

        # Right panel for preview and controls
        right_panel = Frame(split_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add top control panel before the canvas
        top_controls_frame = Frame(right_panel)
        top_controls_frame.pack(fill=tk.X, pady=5)

        # Icon selection in first row
        icon_frame = Frame(top_controls_frame)
        icon_frame.pack(side=tk.LEFT, padx=10)
    
        Button(icon_frame, text="Choose Big Icon", command=self.load_big_icon).pack(side=tk.LEFT, padx=5)
        Button(icon_frame, text="Choose Small Icon", command=self.load_small_icon).pack(side=tk.LEFT, padx=5)

        # Reset and Generate buttons in first row
        action_frame = Frame(top_controls_frame)
        action_frame.pack(side=tk.RIGHT, padx=10)

        Button(action_frame, text="Reset Positions", command=self.reset_positions).pack(side=tk.LEFT, padx=5)
        Button(action_frame, text="Generate Image", command=self.generate_image).pack(side=tk.LEFT, padx=5)
        Button(action_frame, text="Export All PNGs", command=self.export_all_images).pack(side=tk.LEFT, padx=5)
        Button(action_frame, text="Ghi nhớ vị trí", command=self.save_paragraph_data_message).pack(side=tk.LEFT, padx=5)

        # Add second row for scaling controls
        scaling_frame = Frame(right_panel)
        scaling_frame.pack(fill=tk.X, pady=5)

        # Text scaling in second row
        text_scale_frame = Frame(scaling_frame)
        text_scale_frame.pack(side=tk.LEFT, padx=10)

        Label(text_scale_frame, text="Text Scaling:").pack(side=tk.LEFT)

        for i in range(3):
            sub_frame = Frame(text_scale_frame)
            sub_frame.pack(side=tk.LEFT, padx=10)
            Label(sub_frame, text=f"Line {i+1}").pack(side=tk.TOP)
            Button(sub_frame, text="+", width=2, 
                   command=lambda idx=i: self.scale_text_line(idx, 1.1)).pack(side=tk.LEFT, padx=2)
            Button(sub_frame, text="-", width=2, 
                   command=lambda idx=i: self.scale_text_line(idx, 0.9)).pack(side=tk.LEFT, padx=2)

        # Icon scaling in second row
        icon_scale_frame = Frame(scaling_frame)
        icon_scale_frame.pack(side=tk.RIGHT, padx=10)

        Label(icon_scale_frame, text="Icon Scaling:").pack(side=tk.LEFT)

        big_icon_frame = Frame(icon_scale_frame)
        big_icon_frame.pack(side=tk.LEFT, padx=10)
        Label(big_icon_frame, text="Big").pack(side=tk.TOP)
        Button(big_icon_frame, text="+", width=2, 
               command=lambda: self.scale_icon('big_icon', 1.2)).pack(side=tk.LEFT, padx=2)
        Button(big_icon_frame, text="-", width=2, 
               command=lambda: self.scale_icon('big_icon', 0.8)).pack(side=tk.LEFT, padx=2)

        small_icon_frame = Frame(icon_scale_frame)
        small_icon_frame.pack(side=tk.LEFT, padx=10)
        Label(small_icon_frame, text="Small").pack(side=tk.TOP)
        Button(small_icon_frame, text="+", width=2, 
               command=lambda: self.scale_icon('small_icon', 1.2)).pack(side=tk.LEFT, padx=2)
        Button(small_icon_frame, text="-", width=2, 
               command=lambda: self.scale_icon('small_icon', 0.8)).pack(side=tk.LEFT, padx=2)

        # Instructions
        Label(right_panel, text="Drag items to position them. Use the controls above to resize elements.", 
              font=("Arial", 10)).pack(pady=5)

        # Create preview canvas - 1200x1200 canvas
        self.preview_canvas = Canvas(right_panel, width=1200, height=1200, bg="white")
        self.preview_canvas.pack()

        # Add border to canvas
        self.preview_canvas.create_rectangle(2, 2, 1198, 1198, outline="#cccccc", width=2)


    def setup_icon_search(self, parent_frame):
        """Set up the icon search area for vertical layout"""
        # Create a vertical layout for the search panel
        search_frame = Frame(parent_frame)
        search_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        # Search header
        Label(search_frame, text="Icon Search", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
    
        # Search input area
        search_input_frame = Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=5)
    
        self.icon_search_var = StringVar()
        search_entry = ttk.Entry(search_input_frame, textvariable=self.icon_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<Return>", lambda e: self.search_icons())
    
        Button(search_input_frame, text="Search", command=self.search_icons).pack(side=tk.RIGHT, padx=5)
    
        # Create a frame for search results with vertical scrolling
        results_frame = Frame(search_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
        # Canvas with scrollbar for results
        canvas_frame = Frame(results_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.icon_canvas = tk.Canvas(canvas_frame, height=500)
        self.icon_canvas.pack_propagate(False)  # Prevent canvas from resizing based on content
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.icon_canvas.yview)
        self.icon_scrollable_frame = Frame(self.icon_canvas)
    
        self.icon_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        )
    
        self.icon_canvas.create_window((0, 0), window=self.icon_scrollable_frame, anchor="nw")
        self.icon_canvas.configure(yscrollcommand=scrollbar.set)
    
        self.icon_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # Store references to icon images
        self.icon_images = []
    
        # Initial message
        self.no_results_label = Label(self.icon_scrollable_frame, text="Search for icons to display results")
        self.no_results_label.pack(pady=10)

    def search_icons(self):
        """Search for icons in the ICONS directory"""
        # Clear previous results
        for widget in self.icon_scrollable_frame.winfo_children():
            widget.destroy()
    
        self.icon_images = []  # Clear stored image references
    
        # Get search terms
        search_text = self.icon_search_var.get().strip().lower()
        if not search_text:
            self.no_results_label = Label(self.icon_scrollable_frame, text="Please enter search terms")
            self.no_results_label.pack(pady=10)
            return
    
        search_terms = search_text.split()
    
        # Check if ICONS directory exists
        if not os.path.exists('ICONS'):
            os.makedirs('ICONS')
            self.no_results_label = Label(self.icon_scrollable_frame, 
                                     text="ICONS directory created. Please add icon files.")
            self.no_results_label.pack(pady=10)
            return
    
        # Find matching icons
        icon_files = []
        for filename in os.listdir('ICONS'):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                name_parts = filename.lower().split('_')
            
                # Extract filename without extension for matching
                file_base = os.path.splitext(filename)[0].lower()
            
                # Exact match (all terms in correct order)
                exact_match = all(term in file_base for term in search_terms)
            
                # Partial match (individual terms)
                partial_matches = []
                for term in search_terms:
                    if term in file_base:
                        partial_matches.append(term)
            
                # Only add if there's at least one match
                if partial_matches:
                    # Store tuple of (filename, match_score, matching_terms)
                    # Exact matches get priority, then number of matching terms
                    score = 1000 if exact_match else len(partial_matches)
                    icon_files.append((filename, score, partial_matches))
        
        # Sort by score (highest first)
        icon_files.sort(key=lambda x: x[1], reverse=True)
    
        if not icon_files:
            self.no_results_label = Label(self.icon_scrollable_frame, text="No matching icons found")
            self.no_results_label.pack(pady=10)
            return
    
        # Display results in a grid layout
        self.display_icon_results(icon_files)

    def display_icon_results(self, icon_files):
        """Display icon search results in a vertical layout"""
        # Clear existing results
        for widget in self.icon_scrollable_frame.winfo_children():
            widget.destroy()
    
        # Create a frame for the results
        results_frame = Frame(self.icon_scrollable_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)
    
        # Add header
        Label(results_frame, text=f"Found {len(icon_files)} icons", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
    
        # Display each icon vertically
        for i, (filename, score, matching_terms) in enumerate(icon_files):
            # Create cell frame
            cell_frame = Frame(results_frame, borderwidth=1, relief="solid", padx=5, pady=5)
            cell_frame.pack(fill=tk.X, padx=5, pady=5)
        
            try:
                # Create a horizontal layout within each cell for the icon and buttons
                icon_layout = Frame(cell_frame)
                icon_layout.pack(fill=tk.X)
            
                # Left side - icon and filename
                icon_info = Frame(icon_layout)
                icon_info.pack(side=tk.LEFT)
            
                # Load and resize the icon
                img_path = os.path.join('ICONS', filename)
                img = Image.open(img_path)
                img = img.resize((50, 50), Image.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
            
                # Store reference to prevent garbage collection
                self.icon_images.append(photo_img)
                
                # Display the image
                img_label = Label(icon_info, image=photo_img)
                img_label.pack(side=tk.LEFT, padx=5)
            
                # Display the filename
                name_frame = Frame(icon_info)
                name_frame.pack(side=tk.LEFT, padx=5)
            
                # Truncate filename if needed
                display_name = filename
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."
            
                name_label = Label(name_frame, text=display_name, anchor="w")
                name_label.pack(anchor=tk.W)
            
                # Display matching terms if not an exact match
                if len(matching_terms) < len(filename.split('_')):
                    match_label = Label(name_frame, text=f"Matched: {', '.join(matching_terms)}", 
                                       font=("Arial", 8), fg="#666666")
                    match_label.pack(anchor=tk.W)
            
                # Right side - selection buttons
                button_frame = Frame(icon_layout)
                button_frame.pack(side=tk.RIGHT)
            
                Button(button_frame, text="Big Icon", 
                      command=lambda f=img_path: self.select_icon(f, 'big_icon')).pack(side=tk.LEFT, padx=2)
                Button(button_frame, text="Small Icon", 
                      command=lambda f=img_path: self.select_icon(f, 'small_icon')).pack(side=tk.LEFT, padx=2)
            
            except Exception as e:
                print(f"Error loading icon {filename}: {e}")
                Label(cell_frame, text=f"Error: {filename}").pack(pady=5)

    def select_icon(self, file_path, icon_type):
        """Select an icon from search results"""
        # Save current paragraph data
        self.save_paragraph_data()
    
        # Load the icon
        icon = load_icon_image(file_path)
        if icon:
            self.paragraphs[self.current_paragraph_index]['icons'][icon_type] = icon
        
            # Update preview
            self.update_preview()

    
    def scale_text_line(self, line_index, factor):
        """Scale a specific text line"""
        # Save current paragraph data
        self.save_paragraph_data()
        
        paragraph = self.paragraphs[self.current_paragraph_index]
        
        # Scale specific text line
        key = f'text{line_index}'
        paragraph['font_sizes'][key] = max(10, int(paragraph['font_sizes'][key] * factor))
        
        # Update preview
        self.update_preview()
    
    def scale_icon(self, icon_type, factor):
        """Scale a specific icon"""
        # Save current paragraph data
        self.save_paragraph_data()
        
        paragraph = self.paragraphs[self.current_paragraph_index]
        
        # Scale specific icon
        size = paragraph['icon_sizes'][icon_type]
        paragraph['icon_sizes'][icon_type] = (
            max(10, int(size[0] * factor)),
            max(10, int(size[1] * factor))
        )
        
        # Update preview
        self.update_preview()
    
    def update_element_position(self, element_type, x, y):
        """Update the position of an element after dragging"""
        paragraph = self.paragraphs[self.current_paragraph_index]
        paragraph['positions'][element_type] = (x, y)
    
    def reset_positions(self):
        """Reset element positions to default"""
        if not self.paragraphs:
            return
            
        paragraph = self.paragraphs[self.current_paragraph_index]
        
        # Reset to default positions - updated for 800x800 canvas
        paragraph['positions'] = {
            'text0': (150, 150),
            'text1': (150, 250),
            'text2': (150, 350),
            'small_icon': (600, 600),
            'big_icon': (100, 600)
        }
        
        # Update preview
        self.update_preview()
    
    def add_paragraph(self):
        """Add a new paragraph with updated effects structure"""
        # Create a new paragraph data structure
        new_paragraph = {
            'active': True,
            'text_lines': ['', '', ''],
            'fonts': [],
            'colors': ['#000000', '#000000', '#000000'],
            'positions': {
                'text0': (150, 150),
                'text1': (150, 250),
                'text2': (150, 350),
                'small_icon': (600, 600),
                'big_icon': (100, 600)
            },
            'font_sizes': {
                'text0': 50,
                'text1': 50,
                'text2': 50
            },
            'icon_sizes': {
                'small_icon': (70, 70),
                'big_icon': (150, 150)
            },
            'icons': {
                'small_icon': None,
                'big_icon': None
            },
            'effects': {
                'shadow': False,
                'outline': False,
                'stroke': False,
                'shadow_offset': 3,
                'outline_width': 1,
                'stroke_width': 2
                # Note: No longer storing fixed colors here
                # Instead, they'll be calculated dynamically from each line's color
            }
        }
    
        # Add to paragraphs list
        self.paragraphs.append(new_paragraph)
        self.current_paragraph_index = len(self.paragraphs) - 1
    
        # Update the paragraph selector
        self.update_paragraph_selector()
    
        # Load the paragraph data into the UI
        self.load_paragraph_data()
    
        # Update the preview
        self.update_preview()
    
    def update_paragraph_selector(self):
        """Update the paragraph selector dropdown"""
        # Create paragraph labels
        paragraph_labels = []
        for i, paragraph in enumerate(self.paragraphs):
            # Use first text line as label, or default
            label = f"Paragraph {i+1}"
            if paragraph['text_lines'][0]:
                label += f": {paragraph['text_lines'][0][:20]}"
                if len(paragraph['text_lines'][0]) > 20:
                    label += "..."
            paragraph_labels.append(label)
        
        # Update the combobox
        self.paragraph_selector['values'] = paragraph_labels
        self.paragraph_selector.current(self.current_paragraph_index)
    
    def on_paragraph_selected(self, event):
        """Handle paragraph selection change"""
        # Save current paragraph data
        self.save_paragraph_data()
        
        # Update current index
        self.current_paragraph_index = self.paragraph_selector.current()
        
        # Load selected paragraph data
        self.load_paragraph_data()
        
        # Update preview
        self.update_preview()
    
    def save_paragraph_data(self):
        """Save UI data to current paragraph with updated effects"""
        if not self.paragraphs:
            return
        
        paragraph = self.paragraphs[self.current_paragraph_index]

        # Save text
        for i, entry in enumerate(self.text_inputs):
            paragraph['text_lines'][i] = entry.get()

        # Save fonts
        paragraph['fonts'] = self.font_loader.get_selected_fonts()

        # Save colors from manual pickers if selected
        picker_colors = [var.get() for var in self.color_pickers]

        # Check if manual colors are selected
        if all(color == "#000000" for color in picker_colors):  # Default is still black
            paragraph['colors'] = self.color_manager.get_selected_colors()  # If no manual colors, use ColorManager
        else:
            paragraph['colors'] = picker_colors  # If manual colors exist, prioritize them
        
        # Save effects - only the settings, not the colors
        paragraph['effects']['shadow'] = bool(self.effect_vars['shadow'].get())
        paragraph['effects']['outline'] = bool(self.effect_vars['outline'].get())
        paragraph['effects']['stroke'] = bool(self.effect_vars['stroke'].get())
        paragraph['effects']['shadow_offset'] = self.shadow_offset.get()
        paragraph['effects']['outline_width'] = self.outline_width.get()
        paragraph['effects']['stroke_width'] = self.stroke_width.get()
    
        # Update the effect color preview
        if hasattr(self, 'color_preview_frame'):
            self.update_effect_color_preview()

    def save_paragraph_data_message(self):
        """Lưu vị trí hiện tại và thông báo"""
        self.save_paragraph_data()
        messagebox.showinfo("Ghi nhớ vị trí", "Vị trí các dòng đã được ghi nhớ thành công.")

    def load_paragraph_data(self):
        """Load current paragraph data into UI with updated effects handling"""
        if not self.paragraphs:
            return
        
        paragraph = self.paragraphs[self.current_paragraph_index]
    
        # Load text
        for i, entry in enumerate(self.text_inputs):
            entry.delete(0, tk.END)
            if i < len(paragraph['text_lines']):
                entry.insert(0, paragraph['text_lines'][i])
    
        # Reset and load fonts
        self.font_loader.reset_selection()
        for font in paragraph['fonts']:
            for var, font_name, _ in self.font_loader.font_vars:
                if font_name == font:
                    var.set(1)
                    break
    
        # Reset and load colors
        self.color_manager.reset_selection()
        # Load into color pickers
        for i in range(3):
            if i < len(paragraph['colors']):
                self.color_pickers[i].set(paragraph['colors'][i])
    
        # Load effects - only settings, not colors
        self.effect_vars['shadow'].set(1 if paragraph['effects']['shadow'] else 0)
        self.effect_vars['outline'].set(1 if paragraph['effects']['outline'] else 0)
        self.effect_vars['stroke'].set(1 if paragraph['effects']['stroke'] else 0)
    
        self.shadow_offset.set(paragraph['effects']['shadow_offset'])
        self.outline_width.set(paragraph['effects']['outline_width'])
        self.stroke_width.set(paragraph['effects']['stroke_width'])
    
        # Update the effect color preview
        if hasattr(self, 'color_preview_frame'):
            self.update_effect_color_preview()
    
        # Update preview
        self.update_preview()
    
    def delete_current_paragraph(self):
        """Delete the current paragraph"""
        if len(self.paragraphs) <= 1:
            messagebox.showinfo("Cannot Delete", "You must have at least one paragraph.")
            return
            
        # Delete current paragraph
        del self.paragraphs[self.current_paragraph_index]
        
        # Adjust index if needed
        if self.current_paragraph_index >= len(self.paragraphs):
            self.current_paragraph_index = len(self.paragraphs) - 1
        
        # Update selector and load data
        self.update_paragraph_selector()
        self.load_paragraph_data()
        
        # Update preview
        self.update_preview()
    
    def reset_all(self):
        """Reset the entire project"""
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all paragraphs?"):
            # Clear paragraphs
            self.paragraphs = []
            
            # Add default paragraph
            self.add_paragraph()
    
    def load_big_icon(self):
        """Load the big icon image"""
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if path:
            # Save current paragraph data
            self.save_paragraph_data()
            
            # Load the icon
            icon = load_icon_image(path)
            if icon:
                self.paragraphs[self.current_paragraph_index]['icons']['big_icon'] = icon
                
                # Update preview
                self.update_preview()
    
    def load_small_icon(self):
        """Load the small icon image"""
        path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if path:
            # Save current paragraph data
            self.save_paragraph_data()
            
            # Load the icon
            icon = load_icon_image(path)
            if icon:
                self.paragraphs[self.current_paragraph_index]['icons']['small_icon'] = icon
                
                # Update preview
                self.update_preview()
    
    def validate_font_selection(self):
        """Validate that we have fonts selected for all text lines that have content"""
        paragraph = self.paragraphs[self.current_paragraph_index]
        selected_fonts = paragraph['fonts']
        non_empty_lines = [i for i, text in enumerate(paragraph['text_lines']) if text.strip()]
        
        # No text lines with content, no need for fonts
        if not non_empty_lines:
            return True
            
        # No fonts selected but we have text content
        if not selected_fonts:
            messagebox.showwarning(
                "Font Selection Required", 
                "Please select at least one font to display the text lines."
            )
            # Switch to fonts tab
            self.notebook.select(self.font_tab)
            return False
            
        return True
    
    def generate_image(self):
        """Generate the final PNG image"""
        self.save_all_paragraphs_data()

        if not self.validate_font_selection():
            return

        active_paragraphs = [self.paragraphs[self.current_paragraph_index]]

        if active_paragraphs:
            self.image_generator.save_image_dialog(active_paragraphs)
        else:
            messagebox.showinfo("No Content", "No active paragraphs to generate.")

    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, background="#ffffcc", relief="solid", borderwidth=1)
            label.pack()
            
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    def import_text_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if path:
            paragraphs = self.load_paragraphs_from_text(path)
            if paragraphs:
                self.paragraphs = paragraphs
                self.current_paragraph_index = 0
                self.update_paragraph_selector()
                self.load_paragraph_data()
                self.update_preview()

    def load_paragraphs_from_text(self, file_path):
        paragraphs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            while len(lines) % 3 != 0:
                lines.append("")

            for i in range(0, len(lines), 3):
                paragraph = {
                    'active': True,
                    'text_lines': lines[i:i+3],
                    'fonts': [],
                    'colors': ['#000000', '#000000', '#000000'],
                    'positions': {
                        'text0': (150, 150),
                        'text1': (150, 250),
                        'text2': (150, 350),
                        'small_icon': (600, 600),
                        'big_icon': (100, 600)
                    },
                    'font_sizes': {
                        'text0': 150,
                        'text1': 160,
                        'text2': 140
                    },
                    'icon_sizes': {
                        'small_icon': (150, 150),
                        'big_icon': (300, 300)
                    },
                    'icons': {
                        'small_icon': None,
                        'big_icon': None
                    },
                    'effects': {
                        'shadow': False,
                        'outline': False,
                        'stroke': False,
                        'shadow_color': '#888888',
                        'shadow_offset': 3,
                        'outline_color': '#FFFFFF',
                        'outline_width': 1,
                        'stroke_color': '#222222',
                        'stroke_width': 2
                    }
                }
                paragraphs.append(paragraph)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to load text file: {e}")
        return paragraphs
    
    def save_all_paragraphs_data(self):
        """Lưu toàn bộ dữ liệu của tất cả các paragraph"""
        current_index_backup = self.current_paragraph_index
        for i in range(len(self.paragraphs)):
            self.current_paragraph_index = i
            self.load_paragraph_data()  # ✅ Tải dữ liệu từ UI (canvas) đúng đoạn
            self.save_paragraph_data()  # ✅ Sau đó lưu lại chính xác
        self.current_paragraph_index = current_index_backup


