import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from database.db_manager import DBManager
from .navbar import NavBar
from .dashboard_view import DashboardView
from ib_async import IB
from .add_asset import AddAssetDialog
from .log_panel import LogPanel

class AnalystFolioApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("AnalystFolio - Pro Manager")
        self.geometry("1920x1080")
        
        self.ib = IB()
        self.db = DBManager()
        
        # --- UI LAYOUT ---
        # 1. Navigation Bar
        self.navbar = NavBar(self, self.switch_view, self.open_add_stock)
        
        # 2. Content Area
        self.content_area = ttk.Frame(self)
        self.content_area.pack(fill=BOTH, expand=True)
        
        # Views
        self.dashboard_view = DashboardView(self.content_area, self.db, self.ib, self.log)
        self.analytics_view = ttk.Label(self.content_area, text="Analytics Module (Coming Soon)", font=("Helvetica", 20))
        
        # 3. Footer
        self.log_panel = LogPanel(self)
        #self.footer_lbl = ttk.Label(self, text="Ready.", bootstyle="secondary", font=("Consolas", 10))
        #self.footer_lbl.pack(side=BOTTOM, fill=X, padx=10, pady=5)
        
        # Start
        self.current_view = None
        self.switch_view("dashboard")

    def switch_view(self, view_name):

        self.navbar.set_active(view_name)

        if self.current_view: 
            self.current_view.pack_forget()
            
        if view_name == "dashboard":
            self.current_view = self.dashboard_view
            self.dashboard_view.refresh_data()
        elif view_name == "analytics":
            self.current_view = self.analytics_view

        if self.current_view:    
            self.current_view.pack(fill=BOTH, expand=True)

    def open_add_stock(self):
        if not self.ib.isConnected():
            from tkinter import messagebox
            messagebox.showerror("Connection Error", "IBKR TWS is NOT connected!\nCannot validate assets.")
            return

        AddAssetDialog(self, self.ib, self.db, self.on_asset_added)

    def on_asset_added(self):
        print("🔄 Asset added, refreshing dashboard...")
        if self.current_view == self.dashboard_view:
            self.dashboard_view.refresh_data()
        self.db.get_watchlist_count()
    
    def log(self, level, module, message):
        self.log_panel.write_log(level, module, message)
        try:
            self.db.log_system_event(level, module, message)
        except:
            pass