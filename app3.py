import re
import tkinter as tk
from tkinter import ttk, messagebox, font
import time
import ctypes
import json
import os
import sys
import webbrowser
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem
import threading
import pytz
from datetime import datetime

# Windows API constants
WS_EX_TRANSPARENT = 0x20
WS_EX_LAYERED = 0x80000
GWL_EXSTYLE = -20

class DesktopClock:
    def __init__(self):
        self.config_file = "clock_config.json"
        self.position_x = 50
        self.position_y = 50
        self.lock_file = "App.lock"
        self.load_config()
        
        # Main clock window
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "black")
        
        # Create a frame to hold multiple timezone labels
        self.clock_frame = tk.Frame(self.root, bg="black")
        self.clock_frame.pack()
        
        # Create labels for each timezone
        self.labels = {}
        self.create_timezone_labels()
        
        # Settings window (initially hidden)
        self.settings_window = None
        
        # System tray
        self.tray_icon = None
        self.running = True
        
        # Initialize clock
        self.update_time()  # Update time first to render content
        self.setup_clock()
        
        # Delay position update to ensure window is properly sized
        self.root.after(100, self.update_position)
        
        # Setup system tray
        self.setup_tray()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
    
    def create_timezone_labels(self):
        """Create labels for each timezone"""
        for widget in self.clock_frame.winfo_children():
            widget.destroy()
        
        self.labels = {}
        
        for i, tz_config in enumerate(self.config["timezones"]):
            tz_name = tz_config["name"]
            label = tk.Label(
                self.clock_frame, 
                font=(tz_config["font_family"], tz_config["font_size"], "bold"),
                fg=tz_config.get("color", "white"), 
                bg="black"
            )
            label.grid(row=i, column=0, sticky="w", pady=2)
            self.labels[tz_name] = label
    
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "position": "topleft",
            "custom_x": 50,
            "custom_y": 50,
            "visible": True,
            "position_x": 50,
            "position_y": 50,
            "timezones": [
                {
                    "name": "Local",
                    "timezone": "local",
                    "font_family": "Segoe UI",
                    "font_size": 12,
                    "datetime_format": "%H:%M:%S\n%d-%m-%Y",
                    "color": "white"
                }
            ]
        }
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            # Ensure all keys exist
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
            # Ensure timezones have all required fields
            for tz in self.config["timezones"]:
                for key, value in default_config["timezones"][0].items():
                    if key not in tz:
                        tz[key] = value
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
        """Update clock display for all timezones"""
        if self.running:
            for tz_config in self.config["timezones"]:
                tz_name = tz_config["name"]
                try:
                    if tz_config["timezone"] == "local":
                        # Local time
                        current_time = time.strftime(tz_config["datetime_format"])
                    else:
                        # Specific timezone
                        tz = pytz.timezone(tz_config["timezone"])
                        current_time = datetime.now(tz).strftime(tz_config["datetime_format"])
                    
                    self.labels[tz_name].config(text=current_time)
                except (ValueError, pytz.UnknownTimeZoneError):
                    # Fallback if format or timezone is invalid
                    try:
                        current_time = time.strftime("%H:%M:%S\n%d-%m-%Y")
                        self.labels[tz_name].config(text=current_time)
                    except:
                        # Final fallback
                        current_time = "Error"
                        self.labels[tz_name].config(text=current_time)
            
            self.root.after(1000, self.update_time)
    
    def update_position(self):
        """Update window position based on config"""
        # Force window to update and calculate its size first
        self.root.update_idletasks()
        
        if self.config["position"] == "custom":
            x, y = self.config["custom_x"], self.config["custom_y"]
        else:
            # Get screen dimensions of the primary monitor
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Force the labels to render and get actual window size
            self.clock_frame.update_idletasks()
            self.root.update_idletasks()
            
            # Get actual window dimensions after content is rendered
            window_width = self.root.winfo_reqwidth()
            window_height = self.root.winfo_reqheight()
            
            # If window dimensions are still small, use reasonable defaults
            if window_width <= 1 or window_height <= 1:
                # Estimate window size based on font and text content
                estimated_width = len("00:00:00 AM") * max(tz["font_size"] for tz in self.config["timezones"]) * 0.6
                estimated_height = sum(2 * tz["font_size"] * 1.5 for tz in self.config["timezones"])  # Sum of all timezone heights
                window_width = int(estimated_width)
                window_height = int(estimated_height)
            
            # Add extra margin for taskbar (40px for Windows taskbar)
            taskbar_margin = 40
            side_margin = 10
            
            positions = {
                "topleft": (side_margin, side_margin),
                "topright": (screen_width - window_width - side_margin, side_margin),
                "bottomleft": (side_margin, screen_height - window_height - taskbar_margin),
                "bottomright": (screen_width - window_width - side_margin, screen_height - window_height - taskbar_margin),
                "center": ((screen_width - window_width) // 2, (screen_height - window_height) // 2)
            }
            
            x, y = positions.get(self.config["position"], (50, 50))
        
        self.root.geometry(f"+{x}+{y}")
        self.position_x = x
        self.position_y = y
        # Update again after positioning to ensure proper placement
        self.root.update_idletasks()
    
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
        """Show settings dialog with timezone management"""
        if self.settings_window is not None:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_set()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Clock Settings")
        self.settings_window.geometry("600x600")
        self.settings_window.resizable(False, True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.settings_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="General")
        
        # Position settings
        pos_frame = ttk.LabelFrame(general_frame, text="Position", padding=10)
        pos_frame.pack(fill='x', pady=5)
        
        self.position_var = tk.StringVar(value=self.config["position"])
        
        positions = [
            ("Top Left", "topleft"),
            ("Top Right", "topright"),
            ("Bottom Left", "bottomleft"),
            ("Bottom Right", "bottomright"),
            ("Center", "center"),
            ("Custom", "custom")
        ]
         
        # place in 2 columns
        radio_grid_frame = ttk.Frame(pos_frame)
        radio_grid_frame.pack(fill='x', pady=5)
        for i, (text, value) in enumerate(positions):
            row, col = divmod(i, 3)
            ttk.Radiobutton(
                radio_grid_frame,
                text=text,
                variable=self.position_var,
                value=value,
                command=self.on_position_change
            ).grid(row=row, column=col, sticky="w", padx=5, pady=2)
        
        # Custom position frame
        self.custom_frame = ttk.Frame(pos_frame)
        self.custom_frame.pack(fill='x', pady=5)
        
        ttk.Label(self.custom_frame, text="X:").grid(row=0, column=0, sticky='w')
        self.custom_x_var = tk.StringVar(value=str(self.config["custom_x"]))
        ttk.Entry(self.custom_frame, textvariable=self.custom_x_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.custom_frame, text="Y:").grid(row=0, column=2, sticky='w', padx=(20,0))
        self.custom_y_var = tk.StringVar(value=str(self.config["custom_y"]))
        ttk.Entry(self.custom_frame, textvariable=self.custom_y_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(self.custom_frame, text=f"Pos. (x,y): {self.position_x,self.position_y}").grid(row=0, column=4, sticky='w', padx=(20,0)) 
        self.on_position_change()
        
        # Timezone management tab
        timezone_frame = ttk.Frame(notebook, padding=10)
        notebook.add(timezone_frame, text="Timezones")
        
        # Timezone list with scrollbar
        list_frame = ttk.Frame(timezone_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        # Create a canvas and scrollbar for the timezone list
        canvas = tk.Canvas(list_frame, height=200)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add timezone button
        add_button = ttk.Button(timezone_frame, text="Add Timezone", command=self.add_timezone_dialog)
        add_button.pack(pady=5)
        
        # Populate timezone list
        self.timezone_widgets = {}
        self.update_timezone_list()
        
        # Buttons
        button_frame = ttk.Frame(self.settings_window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply", 
                  command=self.apply_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.close_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="OK", 
                  command=self.apply_and_close).pack(side='left', padx=5)
        
        # Info Button
        self.info_btn = ttk.Button(button_frame, text="View Info", command=self.toggle_info)
        self.info_btn.pack(side='left', padx=5)
        
        # Info text
        info_text = """
Author: Abhishek Kumar
GitHub: https://github.com/abhishek9292
Website: https://appsindia.in/
Version: 1.0.0, License: (GPL)
------
TimeFormat: A:Weekday B:Month H:24-hour
I:12-hour M:Minute S:Second p:AM/PM
------
Setup for Auto Start:
1. Put a shortcut of this app in the Windows Startup folder.
2. To access the Startup folder, press Win+R, type 'shell:startup', and press Enter.
3. Paste the shortcut in the opened folder.
4. The app will start automatically on system boot. 
        """  
        self.info_label = self.make_clickable_text(self.settings_window, info_text)
         
        # Handle window close (minimize to tray instead of closing)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.minimize_settings_to_tray)
        
        # Center the settings window
        self.settings_window.transient(self.root)
    
    def update_timezone_list(self):
        """Update the timezone list in settings"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.timezone_widgets = {}
        
        # Create widgets for each timezone
        for i, tz_config in enumerate(self.config["timezones"]):
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill='x', pady=2)
            
            # Timezone name
            name_var = tk.StringVar(value=tz_config["name"])
            name_entry = ttk.Entry(frame, textvariable=name_var, width=15)
            name_entry.grid(row=0, column=0, padx=2)
            
            # Timezone selection
            tz_var = tk.StringVar(value=tz_config["timezone"])
            tz_combo = ttk.Combobox(frame, textvariable=tz_var, width=20)
            tz_combo['values'] = ["local"] + sorted(pytz.all_timezones)
            tz_combo.grid(row=0, column=1, padx=2)
            
            # Font family
            font_var = tk.StringVar(value=tz_config["font_family"])
            font_combo = ttk.Combobox(frame, textvariable=font_var, width=15)
            font_combo['values'] = list(font.families())
            font_combo.grid(row=0, column=2, padx=2)
            
            # Font size
            size_var = tk.StringVar(value=str(tz_config["font_size"]))
            size_spin = ttk.Spinbox(frame, textvariable=size_var, from_=8, to=72, width=5)
            size_spin.grid(row=0, column=3, padx=2)
            
            # Format
            format_var = tk.StringVar(value=tz_config["datetime_format"])
            format_entry = ttk.Entry(frame, textvariable=format_var, width=20)
            format_entry.grid(row=0, column=4, padx=2)
            
            # Color
            color_var = tk.StringVar(value=tz_config.get("color", "white"))
            color_combo = ttk.Combobox(frame, textvariable=color_var, width=10)
            color_combo['values'] = ["white", "red", "green", "blue", "yellow", "cyan", "magenta"]
            color_combo.grid(row=0, column=5, padx=2)
            
            # Delete button
            delete_btn = ttk.Button(frame, text="X", width=2,
                                  command=lambda idx=i: self.remove_timezone(idx))
            delete_btn.grid(row=0, column=6, padx=2)
            
            # Store references
            self.timezone_widgets[i] = {
                "frame": frame,
                "name": name_var,
                "timezone": tz_var,
                "font_family": font_var,
                "font_size": size_var,
                "format": format_var,
                "color": color_var
            }
    
    def add_timezone_dialog(self):
        """Add a new timezone"""
        new_tz = {
            "name": f"Timezone {len(self.config['timezones']) + 1}",
            "timezone": "local",
            "font_family": "Segoe UI",
            "font_size": 12,
            "datetime_format": "%H:%M:%S\n%d-%m-%Y",
            "color": "white"
        }
        self.config["timezones"].append(new_tz)
        self.update_timezone_list()
    
    def remove_timezone(self, index):
        """Remove a timezone"""
        if len(self.config["timezones"]) > 1:  # Keep at least one timezone
            self.config["timezones"].pop(index)
            self.update_timezone_list()
        else:
            messagebox.showwarning("Warning", "You must have at least one timezone.")
    
    def make_clickable_text(self, parent, text):
        """Create a Text widget with auto-detected clickable URLs."""
        text_widget = tk.Text(parent, wrap="word", width=65, height=15,
                              borderwidth=0, highlightthickness=0)
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")  # make readonly
        # Store URL ranges for click detection
        self.url_ranges = []
        # Find all URLs
        url_pattern = r"(https?://[^\s]+)"
        for match in re.finditer(url_pattern, text):
            start, end = match.span()
            start_index = f"1.0+{start}c"
            end_index = f"1.0+{end}c"
            
            # Store the URL and its range
            self.url_ranges.append({
                'url': match.group(1),
                'start': start,
                'end': end
            })
            
            text_widget.tag_add("url", start_index, end_index) 
        # Style for URL
        text_widget.tag_config("url", foreground="blue", underline=True)

        # Click → open browser
        def open_url(event):
            index = text_widget.index(f"@{event.x},{event.y}")
            char_pos = int(index.split('.')[1]) 
            # Find which URL contains this position
            for url_info in self.url_ranges:
                if url_info['start'] <= char_pos < url_info['end']:
                    webbrowser.open(url_info['url'])
                    break
        text_widget.tag_bind("url", "<Button-1>", open_url)

        return text_widget

    def toggle_info(self):
        """Toggle visibility of the info section with clickable URLs."""
        if self.info_label.winfo_ismapped():
            self.info_label.pack_forget()
            self.info_btn.config(text="View Info")
            self.settings_window.geometry("600x600")
        else:
            self.info_label.pack(padx=10, pady=20, anchor="w")
            self.info_btn.config(text="Hide Info")
            self.settings_window.geometry("600x780")

    def on_position_change(self):
        """Handle position radio button change"""
        if hasattr(self, 'custom_frame'):
            if self.position_var.get() == "custom":
                for widget in self.custom_frame.winfo_children():
                    if isinstance(widget, ttk.Entry):
                        widget.configure(state='normal')
            else:
                for widget in self.custom_frame.winfo_children():
                    if isinstance(widget, ttk.Entry):
                        widget.configure(state='disabled')
    
    def apply_settings(self):
        """Apply settings from dialog"""
        try:
            # Update general config
            self.config["position"] = self.position_var.get()
            self.config["custom_x"] = int(self.custom_x_var.get())
            self.config["custom_y"] = int(self.custom_y_var.get())
            self.config["position_x"] = int(self.position_x)
            self.config["position_y"] = int(self.position_y)
            
            # Update timezone configs
            for i, tz_config in enumerate(self.config["timezones"]):
                if i in self.timezone_widgets:
                    widgets = self.timezone_widgets[i]
                    tz_config["name"] = widgets["name"].get()
                    tz_config["timezone"] = widgets["timezone"].get()
                    tz_config["font_family"] = widgets["font_family"].get()
                    tz_config["font_size"] = int(widgets["font_size"].get())
                    tz_config["datetime_format"] = widgets["format"].get()
                    tz_config["color"] = widgets["color"].get()
            
            # Apply changes
            self.create_timezone_labels()
            self.update_position()
            self.save_config()
            
            messagebox.showinfo("Settings", "Settings applied successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def apply_and_close(self):
        """Apply settings and close dialog"""
        self.apply_settings()
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
    

    def check_single_instance(self):
        if os.path.exists(self.lock_file):
            print("Another instance already running!")
            sys.exit(0)   # stop new instance
        else:
            open(self.lock_file, "w").close()

    def cleanup(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

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
        self.cleanup()
        self.root.quit()
        self.root.destroy()
        sys.exit()
    
    def run(self):
        """Start the application"""
        self.check_single_instance()
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
        import pytz
    except ImportError:
        print("Required packages missing. Install with:")
        print("pip install pystray pillow pytz")
        sys.exit(1)
    
    app = DesktopClock()
    app.run()