import tkinter as tk
from ui_manager_module import UIManager
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def main():
    # Set up root window
    root = tk.Tk()
    root.title("CrHashtag Tool")
    
    # Get screen dimensions and set window size
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set window to 90% of screen size
    window_width = int(screen_width * 0.9)
    window_height = int(screen_height * 0.9)
    
    # Center the window
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 2
    
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    # On Windows, try to maximize
    if sys.platform == "win32":
        root.state('zoomed')
    
    # Create folders if they don't exist
    if not os.path.exists("FONT MAP"):
        os.makedirs("FONT MAP")
    if not os.path.exists("COLOR MAP"):
        os.makedirs("COLOR MAP")
    if not os.path.exists("OUTPUT"):
        os.makedirs("OUTPUT")
    if not os.path.exists("ICONS"):   # Add this new line
        os.makedirs("ICONS")          # Add this new line
        
    app = UIManager(root)
    root.mainloop()

if __name__ == '__main__':
    main()
