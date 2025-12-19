import asyncio
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ib_async import Stock

from config.constants import SecType, Exchange, DataRole

class AddAssetDialog(ttk.Toplevel):
    def __init__(self, parent, ib, db_manager, on_success_callback):
        super().__init__(parent)
        self.title("Add New Asset")
        self.geometry("450x400")
        
        self.ib = ib
        self.db = db_manager
        self.callback = on_success_callback
        
        ttk.Label(self, text="Symbol (e.g. NVDA):", font=("Helvetica", 10, "bold")).pack(pady=(20, 5))
        self.entry_symbol = ttk.Entry(self)
        self.entry_symbol.pack(pady=5, padx=40, fill=X)
        self.entry_symbol.focus() # Direkt yazmaya başla

        ttk.Label(self, text="Your Note (Optional):").pack(pady=(10, 5))
        self.entry_note = ttk.Entry(self)
        self.entry_note.pack(pady=5, padx=40, fill=X)
        
        self.status_lbl = ttk.Label(self, text="Ready to validate via IBKR", bootstyle="secondary")
        self.status_lbl.pack(pady=20)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=BOTTOM, pady=20)
        
        self.btn_add = ttk.Button(btn_frame, text="🔍 Validate & Add", bootstyle="primary", command=self.on_submit)
        self.btn_add.pack(side=LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Cancel", bootstyle="secondary", command=self.destroy).pack(side=LEFT, padx=5)

    def on_submit(self):
        symbol = self.entry_symbol.get().upper().strip()
        note = self.entry_note.get().strip()
        
        if not symbol:
            self.status_lbl.config(text="⚠️ Please enter a symbol!", bootstyle="warning")
            return
            
        asyncio.create_task(self.validate_and_save(symbol, note))

    async def validate_and_save(self, symbol, note):
        self.status_lbl.config(text=f"⏳ Contacting IBKR for {symbol}...", bootstyle="info")
        self.btn_add.config(state="disabled")
        
        try:
            contract = Stock(symbol, Exchange.SMART.value, 'USD')
            
            details = await self.ib.reqContractDetailsAsync(contract)
            
            if not details:
                self.status_lbl.config(text=f"❌ '{symbol}' not found on IBKR!", bootstyle="danger")
                self.btn_add.config(state="normal")
                return

            d = details[0]
            long_name = d.longName
            sector = d.industry
            subsector = d.category
            
            self.status_lbl.config(text=f"✅ Found: {long_name}. Fetching Price...", bootstyle="info")

            await self.ib.qualifyContractsAsync(contract)

            tickers = await self.ib.reqTickersAsync(contract)
            last_price = None
            close_price = None
            
            if tickers:
                t = tickers[0]
                last_price = t.last if t.last else t.close
                close_price = t.close
            
            asset_data = {
                'symbol': symbol,
                'con_id': contract.conId,
                'name': long_name,
                'sector': sector,
                'industry': subsector,
                'sec_type': SecType.STOCK.value,
                'currency': 'USD',
                'exchange': Exchange.SMART.value,
                'last_price': last_price,
                'close_price': close_price
            }

            success, instr_id = self.db.upsert_instrument_from_ibkr(asset_data)
            
            if success:
                w_success, w_msg = self.db.add_stock_to_watchlist(symbol, note)
                
                if w_success:
                    self.status_lbl.config(text=f"🎉 {symbol} Added Successfully!", bootstyle="success")
                    await asyncio.sleep(1.5)
                    self.callback()
                    self.destroy()
                else:
                    self.status_lbl.config(text=f"⚠️ {w_msg}", bootstyle="warning")
            else:
                self.status_lbl.config(text="❌ Database Error!", bootstyle="danger")
                
        except Exception as e:
            print(e)
            self.status_lbl.config(text=f"❌ Error: {str(e)}", bootstyle="danger")
        finally:
            self.btn_add.config(state="normal")