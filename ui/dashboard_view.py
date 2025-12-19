import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import Menu, messagebox
from .edit_asset import EditAssetDialog


class DashboardView(ttk.Frame):
    def __init__(self, parent, db_manager, ib, log_func):
        super().__init__(parent)
        self.db = db_manager
        self.ib = ib
        self.log = log_func
        self.all_data = []

        # Top Bar
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=X, padx=10, pady=10)

        ttk.Label(top_frame, text="Search:", font=("Helvetica", 10, "bold")).pack(side=LEFT, padx=(0, 5))
        self.search_var = ttk.StringVar()
        self.search_var.trace_add("write", self.filter_table)
        self.search_entry = ttk.Entry(top_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=LEFT)

        ttk.Button(top_frame, text="Refresh Data", bootstyle="info-outline", command=self.refresh_data).pack(side=RIGHT)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL, bootstyle="secondary-round")
        self.scrollbar.pack(side=RIGHT, fill=Y)

        columns = ("symbol", "name", "sector", "price", "change", "pe", "role")

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", bootstyle="dark", height=20, yscrollcommand=self.scrollbar.set)

        self.scrollbar.config(command=self.tree.yview)
        
        self.tree.heading("symbol", text="Symbol", command=lambda: self.sort_column("symbol", False))
        self.tree.heading("name", text="Company Name")
        self.tree.heading("sector", text="Sector")
        self.tree.heading("price", text="Last Price")
        self.tree.heading("change", text="Change %")
        self.tree.heading("pe", text="P/E Ratio")
        self.tree.heading("role", text="Role")

        self.tree.column("symbol", width=80, anchor=CENTER)
        self.tree.column("name", width=200, anchor=CENTER)
        self.tree.column("sector", width=120, anchor=CENTER)
        self.tree.column("price", width=80, anchor=CENTER)
        self.tree.column("change", width=80, anchor=CENTER)
        self.tree.column("pe", width=80, anchor=CENTER)
        self.tree.column("role", width=80, anchor=CENTER)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)

        self.tree.tag_configure("up", foreground="#2ecc71")
        self.tree.tag_configure("down", foreground="#e74c3c")

        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="📝 Edit Asset", command=self.edit_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete Asset", command=self.delete_selected)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Button-2>", self.show_context_menu)
    
    def log(self, level, msg):
        if self.log:
            self.log(level, "Dashboard", msg)

    def refresh_data(self):
        self.log("INFO", module="System", message="Fetching data from DB...")
        self.all_data = self.db.get_dashboard_data()
        
        if not self.all_data:
            self.log("WARNING", module="System", message="ℹ️ Watchlist is empty.")
        else:
            self.log("INFO", module="System", message=f"✅ Loaded {len(self.all_data)} assets")

        self.populate_tree(self.all_data)
    
    def delete_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_values = self.tree.item(selected_item)['values']
        symbol_raw = item_values[0]
        
        symbol = symbol_raw.split(" ")[0] 
        confirm = messagebox.askyesno(
            "Confirm Delete", 
            f"Are you sure you want to delete '{symbol}'?\n\nThis will remove it from both your Watchlist and the Database permanently."
        )

        if confirm:
            success, msg = self.db.delete_instrument(symbol)
            if success:
                self.refresh_data()
                messagebox.showinfo("Deleted", f"{symbol} has been removed.")
            else:
                messagebox.showerror("Error", f"Could not delete: {msg}")

    def populate_tree(self, data):
        for i in self.tree.get_children():
            self.tree.delete(i)

        for item in data:
            tag = "up" if item["change"] >= 0 else "down"
            self.tree.insert("", END, values=(
                item["symbol"],
                item["name"],
                item["sector"],
                f"${item['price']}",
                f"{item['change']}%",
                item["pe"],
                item["role"]
            ), tags=(tag,))

    def filter_table(self, *args):
        """Arama kutusuna göre filtreler"""
        query = self.search_var.get().lower()
        filtered_data = []
        for item in self.all_data:
            if query in item["symbol"].lower() or query in item["name"].lower():
                filtered_data.append(item)
        self.populate_tree(filtered_data)
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def edit_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        # Seçilen satırdan sembolü al
        item_values = self.tree.item(selected_item)['values']
        symbol_raw = item_values[0] # "AAPL ⭐"
        symbol = symbol_raw.split(" ")[0] # Saf sembol

        # IBKR Bağlantı kontrolü (Main app üzerinden erişim lazım)
        # Pratik çözüm: MainApp'teki IB objesini Dashboard'a parametre olarak geçebiliriz
        # VEYA basitçe DB güncellemelerini yaparız ama IB yoksa fiyat çekmeyiz.
        # Ama EditAssetDialog IB objesi istiyor.
        
        # ÇÖZÜM: self.master (Main Window) üzerinden erişebiliriz ama en temizi
        # DashboardView __init__ fonksiyonuna 'ib' parametresi eklemek.
        
        # Şimdilik hata vermemesi için parent (MainWindow) üzerinden IB'yi bulmaya çalışalım:
        main_window = self.master.master.master # Frame -> ContentArea -> MainWindow (Biraz hileli ama çalışır)
        # Veya daha şık olsun diye DashboardView'a 'ib' parametresi ekle.
        
        # Hadi doğru yolu yapalım:
        # DashboardView.__init__ içine self.ib = ib ekle (Aşağıda anlatıyorum)
        if hasattr(self, 'ib') and self.ib:
             EditAssetDialog(self, symbol, self.ib, self.db, self.refresh_data)
        else:
            print("❌ IB object missing in DashboardView")

    def sort_column(self, col, reverse):
        pass



    