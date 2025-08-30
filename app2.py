import time
import pytz
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

class WorldClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("World Clock")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        # Configuration with multiple timezone support
        self.config = {
            "timezones": ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"],
            "datetime_format": "%H:%M:%S\n%d-%m-%Y",
            "update_interval": 1000  # milliseconds
        }
        
        self.create_widgets()
        self.update_time()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="World Clocks", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Timezone selection
        ttk.Label(main_frame, text="Add Timezone:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        self.tz_var = tk.StringVar()
        tz_combo = ttk.Combobox(main_frame, textvariable=self.tz_var, width=20)
        tz_combo['values'] = sorted(pytz.all_timezones)
        tz_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        add_button = ttk.Button(main_frame, text="Add", command=self.add_timezone)
        add_button.grid(row=1, column=2, padx=(5, 0), pady=(0, 5))
        
        # Timezone list frame with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
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
        
        # Clock display frame
        self.clock_frame = ttk.Frame(main_frame)
        self.clock_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Initialize timezone displays
        self.timezone_frames = {}
        self.update_timezone_displays()
    
    def add_timezone(self):
        new_tz = self.tz_var.get()
        if new_tz and new_tz in pytz.all_timezones and new_tz not in self.config["timezones"]:
            self.config["timezones"].append(new_tz)
            self.update_timezone_displays()
        elif new_tz in self.config["timezones"]:
            messagebox.showinfo("Info", f"Timezone {new_tz} is already in the list.")
        else:
            messagebox.showerror("Error", "Please select a valid timezone.")
    
    def remove_timezone(self, timezone):
        if timezone in self.config["timezones"]:
            self.config["timezones"].remove(timezone)
            self.update_timezone_displays()
    
    def update_timezone_displays(self):
        # Clear existing displays
        for widget in self.clock_frame.winfo_children():
            widget.destroy()
        
        for frame in self.timezone_frames.values():
            frame.destroy()
        self.timezone_frames = {}
        
        # Create new displays
        for i, tz in enumerate(self.config["timezones"]):
            frame = ttk.Frame(self.clock_frame, relief="solid", padding="5")
            frame.grid(row=i // 2, column=i % 2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            
            # Timezone name with remove button
            header_frame = ttk.Frame(frame)
            header_frame.pack(fill=tk.X)
            
            ttk.Label(header_frame, text=tz, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
            
            if tz != "UTC":  # Don't allow removal of UTC
                remove_btn = ttk.Button(header_frame, text="X", width=2, 
                                       command=lambda tz=tz: self.remove_timezone(tz))
                remove_btn.pack(side=tk.RIGHT)
            
            # Time display
            time_label = ttk.Label(frame, font=("Courier New", 14))
            time_label.pack(pady=5)
            
            # Store reference to update later
            self.timezone_frames[tz] = {
                "label": time_label,
                "frame": frame
            }
        
        # Configure grid weights for even spacing
        for i in range((len(self.config["timezones"]) + 1) // 2):
            self.clock_frame.rowconfigure(i, weight=1)
        for i in range(2):
            self.clock_frame.columnconfigure(i, weight=1)
    
    def update_time(self):
        for tz_name, data in self.timezone_frames.items():
            try:
                # Get the timezone
                tz = pytz.timezone(tz_name)
                # Get current time in the timezone
                current_time = datetime.now(tz)
                # Format according to the configured format
                formatted_time = current_time.strftime(self.config["datetime_format"])
                data["label"].config(text=formatted_time)
            except Exception as e:
                # Fallback if any error occurs
                current_time = time.strftime("%H:%M:%S\n%d-%m-%Y")
                data["label"].config(text=current_time)
        
        # Schedule the next update
        self.root.after(self.config["update_interval"], self.update_time)

if __name__ == "__main__":
    root = tk.Tk()
    app = WorldClockApp(root)
    root.mainloop()