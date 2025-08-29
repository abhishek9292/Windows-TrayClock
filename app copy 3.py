import tkinter as tk
from tkinter import ttk, messagebox, font
import time
import ctypes
import json
import os
import sys
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem
import threading

# Windows API constants
WS_EX_TRANSPARENT = 0x20
WS_EX_LAYERED = 0x80000
GWL_EXSTYLE = -20

class DesktopClock:
    def __init__(self):
        self.config_file = "clock_config.json"
        self.load_config()
        
        # Main clock window
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "black")
        
        # Create label
        self.label = tk.Label(
            self.root, 
            font=(self.config["font_family"], self.config["font_size"], "bold"),
            fg="white", 
            bg="black"
        )
        self.label.pack()
        
        # Settings window (initially hidden)
        self.settings_window = None
        
        # System tray
        self.tray_icon = None
        self.running = True
        
        # Initialize clock
        self.setup_clock()
        self.update_position()
        self.update_time()
        
        # Setup system tray
        self.setup_tray()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
    
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "position": "topleft",
            "custom_x": 50,
            "custom_y": 50,
            "font_family": "Segoe UI",
            "font_size": 12,
            "datetime_format": "%H:%M:%S\n%d-%m-%Y",
            "visible": True
        }
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            # Ensure all keys exist
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
        except json.JSONDecodeError:
            self.config = default_config
            self.save_config()
        except FileNotFoundError:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_clock(self):
        """Setup clock window properties"""
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.FindWindowW(None, self.root.title())
        if hwnd:
            self.make_window_clickthrough(hwnd)
    
    def make_window_clickthrough(self, hwnd):
        """Make window click-through"""
        styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                            styles | WS_EX_TRANSPARENT | WS_EX_LAYERED)
    
    def update_time(self):
        """Update clock display"""
        if self.running:
            try:
                current_time = time.strftime(self.config["datetime_format"])
                self.label.config(text=current_time)
            except ValueError:
                # Fallback if format is invalid
                current_time = time.strftime("%H:%M:%S\n%d-%m-%Y")
                self.label.config(text=current_time)
            
            self.root.after(1000, self.update_time)
    
    def update_position(self):
        """Update window position based on config"""
        self.root.update_idletasks()
        
        if self.config["position"] == "custom":
            x, y = self.config["custom_x"], self.config["custom_y"]
        else:
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Get window dimensions
            window_width = self.root.winfo_reqwidth()
            window_height = self.root.winfo_reqheight()
            
            positions = {
                "topleft": (10, 10),
                "topright": (screen_width - window_width - 10, 10),
                "bottomleft": (10, screen_height - window_height - 40),
                "bottomright": (screen_width - window_width - 10, screen_height - window_height - 40),
                "center": ((screen_width - window_width) // 2, (screen_height - window_height) // 2)
            }
            
            x, y = positions.get(self.config["position"], (50, 50))
        
        self.root.geometry(f"+{x}+{y}")
    
    def create_tray_image(self):
        """Create system tray icon"""
        # Create a simple clock icon
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        
        # Draw clock face
        draw.ellipse([8, 8, 56, 56], outline='black', width=3)
        
        # Draw clock hands (simplified)
        draw.line([32, 32, 32, 20], fill='black', width=2)  # Hour hand
        draw.line([32, 32, 42, 32], fill='black', width=2)  # Minute hand
        
        # Draw center dot
        draw.ellipse([30, 30, 34, 34], fill='black')
        
        return image
    
    def setup_tray(self):
        """Setup system tray icon"""
        image = self.create_tray_image()
        
        menu = pystray.Menu(
            MenuItem('Settings', self.show_settings),
            MenuItem('Show Clock' if not self.config["visible"] else 'Hide Clock', self.toggle_visibility),
            pystray.Menu.SEPARATOR,
            MenuItem('Exit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("desktop_clock", image, "Desktop Clock", menu)
        
        # Start tray in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def show_settings(self, icon=None, item=None):
        """Show settings dialog"""
        if self.settings_window is not None:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_set()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Clock Settings")
        self.settings_window.geometry("400x550")
        self.settings_window.resizable(False, False)
        
        # Position settings
        pos_frame = ttk.LabelFrame(self.settings_window, text="Position", padding=10)
        pos_frame.pack(fill='x', padx=10, pady=5)
        
        self.position_var = tk.StringVar(value=self.config["position"])
        
        positions = [
            ("Top Left", "topleft"),
            ("Top Right", "topright"),
            ("Bottom Left", "bottomleft"),
            ("Bottom Right", "bottomright"),
            ("Center", "center"),
            ("Custom", "custom")
        ]
        
        for text, value in positions:
            ttk.Radiobutton(pos_frame, text=text, variable=self.position_var, 
                           value=value, command=self.on_position_change).pack(anchor='w')
        
        # Custom position frame
        self.custom_frame = ttk.Frame(pos_frame)
        self.custom_frame.pack(fill='x', pady=5)
        
        ttk.Label(self.custom_frame, text="X:").grid(row=0, column=0, sticky='w')
        self.custom_x_var = tk.StringVar(value=str(self.config["custom_x"]))
        ttk.Entry(self.custom_frame, textvariable=self.custom_x_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.custom_frame, text="Y:").grid(row=0, column=2, sticky='w', padx=(20,0))
        self.custom_y_var = tk.StringVar(value=str(self.config["custom_y"]))
        ttk.Entry(self.custom_frame, textvariable=self.custom_y_var, width=10).grid(row=0, column=3, padx=5)
        
        self.on_position_change()
        
        # Font settings
        font_frame = ttk.LabelFrame(self.settings_window, text="Font", padding=10)
        font_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(font_frame, text="Font Family:").grid(row=0, column=0, sticky='w')
        self.font_family_var = tk.StringVar(value=self.config["font_family"])
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_family_var, 
                                 values=list(font.families()), width=20)
        font_combo.grid(row=0, column=1, padx=5, sticky='w')
        
        ttk.Label(font_frame, text="Font Size:").grid(row=1, column=0, sticky='w', pady=(5,0))
        self.font_size_var = tk.StringVar(value=str(self.config["font_size"]))
        ttk.Entry(font_frame, textvariable=self.font_size_var, width=10).grid(row=1, column=1, padx=5, pady=(5,0), sticky='w')
        
        # DateTime format
        format_frame = ttk.LabelFrame(self.settings_window, text="Date/Time Format", padding=10)
        format_frame.pack(fill='x', padx=10, pady=5)
        
        self.format_var = tk.StringVar(value=self.config["datetime_format"])
        format_entry = tk.Text(format_frame, height=3, width=40)
        format_entry.insert('1.0', self.config["datetime_format"])
        format_entry.pack(fill='x')
        
        # Common format examples
        examples_frame = ttk.Frame(format_frame)
        examples_frame.pack(fill='x', pady=5)
        
        examples = [
            ("24h + Date", "%H:%M:%S\n%d-%m-%Y"),
            ("12h + Date", "%I:%M:%S %p\n%B %d, %Y"),
            ("Time only", "%H:%M:%S"),
            ("Date only", "%A\n%B %d, %Y")
        ]
        
        for i, (name, fmt) in enumerate(examples):
            ttk.Button(examples_frame, text=name, width=12,
                      command=lambda f=fmt: self.set_format(format_entry, f)).grid(row=i//2, column=i%2, padx=2, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(self.settings_window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply", 
                  command=lambda: self.apply_settings(format_entry)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.close_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="OK", 
                  command=lambda: self.apply_and_close(format_entry)).pack(side='left', padx=5)
        
        # Handle window close (minimize to tray instead of closing)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.minimize_settings_to_tray)
        
        # Center the settings window
        self.settings_window.transient(self.root)
    
    def on_position_change(self):
        """Handle position radio button change"""
        if hasattr(self, 'custom_frame'):
            if self.position_var.get() == "custom":
                for widget in self.custom_frame.winfo_children():
                    widget.configure(state='normal')
            else:
                for widget in self.custom_frame.winfo_children():
                    if isinstance(widget, ttk.Entry):
                        widget.configure(state='disabled')
    
    def set_format(self, text_widget, format_string):
        """Set format in text widget"""
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', format_string)
    
    def apply_settings(self, format_entry):
        """Apply settings from dialog"""
        try:
            # Update config
            self.config["position"] = self.position_var.get()
            self.config["custom_x"] = int(self.custom_x_var.get())
            self.config["custom_y"] = int(self.custom_y_var.get())
            self.config["font_family"] = self.font_family_var.get()
            self.config["font_size"] = int(self.font_size_var.get())
            self.config["datetime_format"] = format_entry.get('1.0', tk.END).strip()
            
            # Apply changes
            self.label.configure(font=(self.config["font_family"], self.config["font_size"], "bold"))
            self.update_position()
            self.save_config()
            
            messagebox.showinfo("Settings", "Settings applied successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def apply_and_close(self, format_entry):
        """Apply settings and close dialog"""
        self.apply_settings(format_entry)
        self.close_settings()
    
    def minimize_settings_to_tray(self):
        """Minimize settings dialog to tray instead of closing"""
        if self.settings_window:
            self.settings_window.withdraw()
    
    def close_settings(self):
        """Actually close settings dialog (used by Cancel button)"""
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
    
    def toggle_visibility(self, icon=None, item=None):
        """Toggle clock visibility only (not settings window)"""
        self.config["visible"] = not self.config["visible"]
        
        if self.config["visible"]:
            self.root.deiconify()
        else:
            self.root.withdraw()
        
        self.save_config()
        
        # Update tray menu text
        if self.tray_icon:
            menu = pystray.Menu(
                MenuItem('Settings', self.show_settings),
                MenuItem('Show Clock' if not self.config["visible"] else 'Hide Clock', self.toggle_visibility),
                pystray.Menu.SEPARATOR,
                MenuItem('Exit', self.quit_app)
            )
            self.tray_icon.menu = menu
    
    def hide_window(self):
        """Hide clock window instead of closing"""
        self.config["visible"] = False
        self.root.withdraw()
        self.save_config()
        
        # Update tray menu
        if self.tray_icon:
            menu = pystray.Menu(
                MenuItem('Settings', self.show_settings),
                MenuItem('Show Clock', self.toggle_visibility),
                pystray.Menu.SEPARATOR,
                MenuItem('Exit', self.quit_app)
            )
            self.tray_icon.menu = menu
    
    def quit_app(self, icon=None, item=None):
        """Completely exit application"""
        self.running = False
        self.save_config()
        
        # Close settings window if open
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
        self.root.destroy()
        sys.exit()
    
    def run(self):
        """Start the application"""
        if not self.config["visible"]:
            self.root.withdraw()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

if __name__ == "__main__":
    # Check for required dependencies
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        print("Required packages missing. Install with:")
        print("pip install pystray pillow")
        sys.exit(1)
    
    app = DesktopClock()
    app.run()