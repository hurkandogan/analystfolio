import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ib_async import Stock
from config.constants import DataRole, Exchange

class EditAssetDialog(ttk.Toplevel):
    def __init__(self, parent, symbol, ib, db_manager, on_success_callback):
        super().__init__(parent)
        self.title(f"Edit Asset: {symbol}")
        self.geometry("450x550")
        
        self.symbol = symbol
        self.ib = ib
        self.db = db_manager
        self.callback = on_success_callback
        
        # Verileri DB'den çek
        self.current_data = self.db.get_asset_details(symbol)
        
        self.create_widgets()
        self.load_initial_data()

    def create_widgets(self):
        # --- READ ONLY FIELDS ---
        ttk.Label(self, text="Company Name:", bootstyle="secondary").pack(anchor=W, padx=20, pady=(15,0))
        self.lbl_name = ttk.Label(self, text="Loading...", font=("Helvetica", 10, "bold"))
        self.lbl_name.pack(anchor=W, padx=20, pady=(0, 10))

        # --- EDITABLE FIELDS ---
        
        # 1. Role (Combobox)
        ttk.Label(self, text="Data Role:").pack(anchor=W, padx=20)
        self.combo_role = ttk.Combobox(self, values=[e.value for e in DataRole], state="readonly")
        self.combo_role.pack(fill=X, padx=20, pady=5)

        # 2. Sector
        ttk.Label(self, text="Sector:").pack(anchor=W, padx=20)
        self.entry_sector = ttk.Entry(self)
        self.entry_sector.pack(fill=X, padx=20, pady=5)

        # 3. Industry
        ttk.Label(self, text="Industry:").pack(anchor=W, padx=20)
        self.entry_industry = ttk.Entry(self)
        self.entry_industry.pack(fill=X, padx=20, pady=5)

        # 4. Note
        ttk.Label(self, text="Your Note:").pack(anchor=W, padx=20)
        self.entry_note = ttk.Entry(self)
        self.entry_note.pack(fill=X, padx=20, pady=5)
        
        # --- STATUS & BUTTONS ---
        self.status_lbl = ttk.Label(self, text="", bootstyle="info")
        self.status_lbl.pack(pady=15)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=BOTTOM, pady=20)
        
        self.btn_save = ttk.Button(btn_frame, text="💾 Update & Refresh Price", bootstyle="primary", command=self.on_save)
        self.btn_save.pack(side=LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self.destroy).pack(side=LEFT, padx=5)

    def load_initial_data(self):
        if not self.current_data:
            self.status_lbl.config(text="❌ Error loading data!", bootstyle="danger")
            self.btn_save.config(state="disabled")
            return

        # Kutucukları doldur
        self.lbl_name.config(text=self.current_data.get('name', 'Unknown'))
        
        # Role Seçimi
        current_role = self.current_data.get('data_role')
        if current_role in self.combo_role['values']:
            self.combo_role.set(current_role)
        else:
            self.combo_role.set(DataRole.TRADE.value) # Varsayılan

        self.entry_sector.insert(0, self.current_data.get('sector') or "")
        self.entry_industry.insert(0, self.current_data.get('industry') or "")
        self.entry_note.insert(0, self.current_data.get('note') or "")

    def on_save(self):
        # Async işlemi başlat
        asyncio.create_task(self.save_and_refresh())

    async def save_and_refresh(self):
        self.btn_save.config(state="disabled")
        self.status_lbl.config(text="💾 Saving metadata...", bootstyle="info")
        
        try:
            # 1. Metadata Güncelle (DB)
            updates = {
                "data_role": self.combo_role.get(),
                "sector": self.entry_sector.get(),
                "industry": self.entry_industry.get(),
                "note": self.entry_note.get()
            }
            
            success, msg = self.db.update_asset_metadata(self.symbol, updates)
            if not success:
                raise Exception(msg)

            # 2. IBKR'dan Fiyat Güncelle (Snapshot)
            self.status_lbl.config(text="⚡ Fetching latest price from IBKR...", bootstyle="warning")
            
            # Kontrat oluştur
            contract = Stock(self.symbol, Exchange.SMART.value, 'USD')
            # ConID varsa ekleyelim, daha hızlı olur
            if self.current_data.get('con_id'):
                contract.conId = self.current_data['con_id']
            
            # Qualify et (Her ihtimale karşı)
            await self.ib.qualifyContractsAsync(contract)
            
            # Fiyatı çek
            tickers = await self.ib.reqTickersAsync(contract)
            
            if tickers:
                t = tickers[0]
                last_price = t.last if t.last else t.close
                close_price = t.close
                
                # Fiyatı DB'ye Upsert et
                price_data = {
                    "symbol": self.symbol,
                    "last_price": last_price,
                    "close_price": close_price,
                    # Diğer alanları tekrar göndermeye gerek yok, upsert sadece bunları günceller
                }
                # Upsert fonksiyonunu reuse ediyoruz
                self.db.upsert_instrument_from_ibkr(price_data)
                
                self.status_lbl.config(text="✅ Updated & Refreshed!", bootstyle="success")
            else:
                self.status_lbl.config(text="⚠️ Metadata saved, but Price update failed.", bootstyle="warning")

            await asyncio.sleep(1)
            self.callback() # Dashboard'u yenile
            self.destroy()

        except Exception as e:
            self.status_lbl.config(text=f"❌ Error: {str(e)}", bootstyle="danger")
        finally:
            self.btn_save.config(state="normal")