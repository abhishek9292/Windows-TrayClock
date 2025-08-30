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

WS_EX_TRANSPARENT = 0x20
WS_EX_LAYERED = 0x80000
GWL_EXSTYLE = -20

class DesktopClock:
    def __init__(self):
        self.config_file = "clock_config.json"
        self.box_geometry ="500x440"
        self.position_x = 50
        self.position_y = 50
        self.lock_file = "App.lock"
        self.load_config()
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "black")
        
        self.clock_frame = tk.Frame(self.root, bg="black")
        self.clock_frame.pack()
        
        self.labels = {}
        self.create_timezone_labels()
        
        self.settings_window = None
        self.tray_icon = None
        self.running = True
        
        self.update_time()
        self.setup_clock()
        
        self.root.after(100, self.update_position)
        
        self.setup_tray()
        
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
    
    def create_timezone_labels(self):
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
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
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
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_clock(self):
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.FindWindowW(None, self.root.title())
        if hwnd:
            self.make_window_clickthrough(hwnd)
    
    def make_window_clickthrough(self, hwnd):
        styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                            styles | WS_EX_TRANSPARENT | WS_EX_LAYERED)
    
    def update_time(self):
        if self.running:
            for tz_config in self.config["timezones"]:
                tz_name = tz_config["name"]
                if tz_name not in self.labels:
                    continue
                try:
                    if tz_config["timezone"] == "local":
                        current_time = time.strftime(tz_config["datetime_format"])
                    else:
                        tz = pytz.timezone(tz_config["timezone"])
                        current_time = datetime.now(tz).strftime(tz_config["datetime_format"])
                    
                    self.labels[tz_name].config(text=current_time)
                except (ValueError, pytz.UnknownTimeZoneError):
                    try:
                        current_time = time.strftime("%H:%M:%S\n%d-%m-%Y")
                        self.labels[tz_name].config(text=current_time)
                    except:
                        current_time = "Error"
                        self.labels[tz_name].config(text=current_time)
            
            self.root.after(1000, self.update_time)
    
    def update_position(self):
        self.root.update_idletasks()
        
        if self.config["position"] == "custom":
            x, y = self.config["custom_x"], self.config["custom_y"]
        else:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            self.clock_frame.update_idletasks()
            self.root.update_idletasks()
            
            window_width = self.root.winfo_reqwidth()
            window_height = self.root.winfo_reqheight()
            
            if window_width <= 1 or window_height <= 1:
                estimated_width = len("00:00:00 AM") * max(tz["font_size"] for tz in self.config["timezones"]) * 0.6
                estimated_height = sum(2 * tz["font_size"] * 1.5 for tz in self.config["timezones"])
                window_width = int(estimated_width)
                window_height = int(estimated_height)
            
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
        self.root.update_idletasks()
    
    def create_tray_image(self):
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        
        draw.ellipse([8, 8, 56, 56], outline='black', width=3)
        draw.line([32, 32, 32, 20], fill='black', width=2)
        draw.line([32, 32, 42, 32], fill='black', width=2)
        draw.ellipse([30, 30, 34, 34], fill='black')
        
        return image
    
    def setup_tray(self):
        image = self.create_tray_image()
        
        menu = pystray.Menu(
            MenuItem('Settings', self.show_settings),
            MenuItem('Show Clock' if not self.config["visible"] else 'Hide Clock', self.toggle_visibility),
            pystray.Menu.SEPARATOR,
            MenuItem('Exit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("desktop_clock", image, "Desktop Clock", menu)
        
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def show_settings(self, icon=None, item=None):
        if self.settings_window is not None:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_set()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Clock Settings")
        self.settings_window.geometry(self.box_geometry)
        self.settings_window.resizable(True, True)
        
        notebook = ttk.Notebook(self.settings_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        # General Tab
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="General")
        
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
        # Timezone Tab
        timezone_frame = ttk.Frame(notebook, padding=10)
        notebook.add(timezone_frame, text="Timezones")
        
        container = ttk.Frame(timezone_frame)
        container.pack(fill='both', expand=True)
        # Create canvas + scrollbars
        canvas = tk.Canvas(container)
        scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(timezone_frame, orient="horizontal", command=canvas.xview)
        
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y") 
        scrollbar_x.pack(fill="x") 
        
        add_button = ttk.Button(timezone_frame, text="Add Timezone", command=self.add_timezone_dialog)
        add_button.pack(pady=5)
        
        self.timezone_widgets = {}
        self.update_timezone_list()
        # Info Tab
        timeinfo_frame = ttk.Frame(notebook, padding=10)
        notebook.add(timeinfo_frame, text="Info")
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
        self.info_label = self.make_clickable_text(timeinfo_frame, info_text)
        self.info_label.pack(padx=10, pady=20, anchor="w")
        # toggle_info
        button_frame = ttk.Frame(self.settings_window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply", command=self.apply_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.close_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="OK", command=self.apply_and_close).pack(side='left', padx=5)
        # 
        self.settings_window.protocol("WM_DELETE_WINDOW", self.minimize_settings_to_tray)
        self.settings_window.transient(self.root)
    
    def update_timezone_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.timezone_widgets = {}
        
        headers = ["Name", "Timezone", "Font", "Size", "Format", "Color", ""]
        for col, header in enumerate(headers):
            ttk.Label(self.scrollable_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=2, pady=5, sticky="w"
            )
        
        for i, tz_config in enumerate(self.config["timezones"]):
            name_var = tk.StringVar(value=tz_config["name"])
            name_entry = ttk.Entry(self.scrollable_frame, textvariable=name_var, width=15)
            name_entry.grid(row=i+1, column=0, padx=2, pady=2, sticky="ew")
            
            tz_var = tk.StringVar(value=tz_config["timezone"])
            tz_combo = ttk.Combobox(self.scrollable_frame, textvariable=tz_var, width=20)
            tz_combo['values'] = ["local"] + sorted(pytz.all_timezones)
            tz_combo.grid(row=i+1, column=1, padx=2, pady=2, sticky="ew")
            
            font_var = tk.StringVar(value=tz_config["font_family"])
            font_combo = ttk.Combobox(self.scrollable_frame, textvariable=font_var, width=15)
            font_combo['values'] = list(font.families())
            font_combo.grid(row=i+1, column=2, padx=2, pady=2, sticky="ew")
            
            size_var = tk.StringVar(value=str(tz_config["font_size"]))
            size_spin = ttk.Spinbox(self.scrollable_frame, textvariable=size_var, from_=8, to=72, width=5)
            size_spin.grid(row=i+1, column=3, padx=2, pady=2, sticky="ew")
            
            format_var = tk.StringVar(value=tz_config["datetime_format"])
            format_entry = ttk.Entry(self.scrollable_frame, textvariable=format_var, width=20, state="readonly")
            # Bind click to open dialog
            format_entry.bind("<Button-1>", lambda e, w=format_entry: self.edit_text_dialog(w))
            format_entry.grid(row=i+1, column=4, padx=2, pady=2, sticky="ew")
            
            color_var = tk.StringVar(value=tz_config.get("color", "white"))
            color_combo = ttk.Combobox(self.scrollable_frame, textvariable=color_var, width=10)
            color_combo['values'] = ["white", "red", "green", "blue", "yellow", "cyan", "magenta"]
            color_combo.grid(row=i+1, column=5, padx=2, pady=2, sticky="ew")
            
            delete_btn = ttk.Button(self.scrollable_frame, text="X", width=2,
                                  command=lambda idx=i: self.remove_timezone(idx))
            delete_btn.grid(row=i+1, column=6, padx=2, pady=2, sticky="ew")
            
            self.timezone_widgets[i] = {
                "name": name_var,
                "timezone": tz_var,
                "font_family": font_var,
                "font_size": size_var,
                "format": format_var,
                "color": color_var
            }
    
    def add_timezone_dialog(self):
        new_tz = {
            "name": f"Time {len(self.config['timezones']) + 1}",
            "timezone": "local",
            "font_family": "Segoe UI",
            "font_size": 12,
            "datetime_format": "%H:%M:%S\n%d-%m-%Y",
            "color": "white"
        }
        self.config["timezones"].append(new_tz)
        self.update_timezone_list()
    
    def remove_timezone(self, index):
        if len(self.config["timezones"]) > 1:
            self.config["timezones"].pop(index)
            self.update_timezone_list()
        else:
            messagebox.showwarning("Warning", "You must have at least one timezone.")
    
    def make_clickable_text(self, parent, text):
        text_widget = tk.Text(parent, wrap="word", width=65, height=15,
                              borderwidth=0, highlightthickness=0)
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")
        self.url_ranges = []
        url_pattern = r"(https?://[^\s]+)"
        for match in re.finditer(url_pattern, text):
            start, end = match.span()
            start_index = f"1.0+{start}c"
            end_index = f"1.0+{end}c"
            self.url_ranges.append({
                'url': match.group(1),
                'start': start,
                'end': end
            })
            text_widget.tag_add("url", start_index, end_index) 
        text_widget.tag_config("url", foreground="blue", underline=True)

        def open_url(event):
            index = text_widget.index(f"@{event.x},{event.y}")
            char_pos = int(index.split('.')[1]) 
            for url_info in self.url_ranges:
                if url_info['start'] <= char_pos < url_info['end']:
                    webbrowser.open(url_info['url'])
                    break
        text_widget.tag_bind("url", "<Button-1>", open_url)

        return text_widget
 
    def on_position_change(self):
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
        try:
            self.config["position"] = self.position_var.get()
            self.config["custom_x"] = int(self.custom_x_var.get())
            self.config["custom_y"] = int(self.custom_y_var.get())
            self.config["position_x"] = int(self.position_x)
            self.config["position_y"] = int(self.position_y)
            
            for i, tz_config in enumerate(self.config["timezones"]):
                if i in self.timezone_widgets:
                    widgets = self.timezone_widgets[i]
                    tz_config["name"] = widgets["name"].get()
                    tz_config["timezone"] = widgets["timezone"].get()
                    tz_config["font_family"] = widgets["font_family"].get()
                    tz_config["font_size"] = int(widgets["font_size"].get())
                    tz_config["datetime_format"] = widgets["format"].get()
                    tz_config["color"] = widgets["color"].get()
            
            self.create_timezone_labels() 
            self.save_config() 
            messagebox.showinfo("Settings", "Settings applied successfully!")
            self.update_position()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
    
    def apply_and_close(self):
        self.apply_settings()
        self.close_settings()
    
    def minimize_settings_to_tray(self):
        if self.settings_window:
            self.settings_window.withdraw()
    
    def close_settings(self):
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
    
    def toggle_visibility(self, icon=None, item=None):
        self.config["visible"] = not self.config["visible"]
        
        if self.config["visible"]:
            self.root.deiconify()
        else:
            self.root.withdraw()
        self.update_position()
        self.save_config()
        
        if self.tray_icon:
            menu = pystray.Menu(
                MenuItem('Settings', self.show_settings),
                MenuItem('Show Clock' if not self.config["visible"] else 'Hide Clock', self.toggle_visibility),
                pystray.Menu.SEPARATOR,
                MenuItem('Exit', self.quit_app)
            )
            self.tray_icon.menu = menu
    
    def edit_text_dialog(self, entry_widget):
        # Create a new dialog window
        dialog = tk.Toplevel(self.root)   # use self.root as master
        dialog.title("Edit Format")
        dialog.grab_set()  # make it modal
        # Get current value
        current_value = entry_widget.get()
        # Insert current value into Text
        text = tk.Text(dialog, height=5, width=40)
        text.insert("1.0", current_value)
        text.pack(padx=10, pady=10)

        def save_and_close(): 
            new_value = text.get("1.0", "end-1c")
            entry_widget.config(state="normal")
            entry_widget.delete(0, "end")
            entry_widget.insert(0, new_value)
            entry_widget.config(state="readonly")
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="OK", command=save_and_close).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)

    
    def hide_window(self):
        self.config["visible"] = False
        self.root.withdraw()
        
        self.save_config()
        
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
            sys.exit(0)
        else:
            open(self.lock_file, "w").close()

    def cleanup(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def quit_app(self, icon=None, item=None):
        self.running = False
        self.save_config()
        
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
        self.check_single_instance()
        if not self.config["visible"]:
            self.root.withdraw()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

if __name__ == "__main__":
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