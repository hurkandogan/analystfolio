import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class NavBar(ttk.Frame):
    def __init__(self, parent, switch_callback, add_callback):
        super().__init__(parent, bootstyle="secondary")
        self.pack(side=TOP, fill=X)
        
        self.buttons = {}
        
        # Logo
        ttk.Label(self, text="AnalystFolio", font=("Impact", 18), bootstyle="inverse-secondary").pack(side=LEFT, padx=10)
        
        self.create_btn("📊 Monitor", "dashboard", switch_callback)
        self.create_btn("🧠 Analytics", "analytics", switch_callback)
        self.create_btn("⚙️ Settings", "settings", lambda x: print("Settings clicked"))
        # -------------------------------
        
        # Add Stock Button
        ttk.Button(self, text="+ ADD ASSET", bootstyle="success", command=add_callback).pack(side=RIGHT, padx=20, pady=5)
        
        # Status
        self.status_indicator = ttk.Label(self, text="● DB Connected", bootstyle="inverse-secondary", foreground="#2ecc71")
        self.status_indicator.pack(side=RIGHT, padx=10)

    def create_btn(self, text, view_name, callback):
        btn = ttk.Button(
            self, 
            text=text, 
            bootstyle="secondary", 
            command=lambda: callback(view_name)
        )
        btn.pack(side=LEFT, padx=2)
        
        self.buttons[view_name] = btn

    def set_active(self, active_view_name):
        for view_name, btn in self.buttons.items():
            if view_name == active_view_name:
                btn.configure(bootstyle="primary")
            else:
                btn.configure(bootstyle="secondary")