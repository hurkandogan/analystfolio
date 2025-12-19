import asyncio
import tkinter as tk # Hata yakalamak için lazım
from ib_async import IB
from ui.main_window import AnalystFolioApp
from config.settings import *

def start_app():
    # 1. Uygulama Penceresini Yarat
    app = AnalystFolioApp()
    
    # 2. Hem GUI'yi hem IBKR'ı yöneten ana asenkron fonksiyon
    async def run_lifecycle():
        try:
            print("⏳ Connecting to IBKR...")
            await app.ib.connectAsync(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
            print("✅ Connected to IBKR!")
            app.navbar.status_indicator.config(text="● IBKR Online", foreground="#2ecc71")
        except Exception as e:
            print(f"❌ Connection Warning: {e}")
            # Bağlanamasa bile uygulama açılsın, o yüzden return yapmıyoruz.
            app.navbar.status_indicator.config(text="● IBKR Offline", foreground="#e74c3c")

        # --- SONSUZ DÖNGÜ (KALP ATIŞI) ---
        # Burası programı ayakta tutan yer.
        try:
            while True:
                # 1. GUI'yi güncelle (Tıklamalar, çizimler)
                app.update()
                
                # 2. Asenkron işlemlere (IBKR'dan veri gelmesine) nefes payı ver
                await asyncio.sleep(0.03) 
                
        except (tk.TclError, KeyboardInterrupt):
            # Pencere kapatıldığında (X'e basıldığında) buraya düşer
            print("🛑 App closed by user.")
        finally:
            if app.ib.isConnected():
                app.ib.disconnect()

    # 3. Motoru Çalıştır
    app.ib.run(run_lifecycle())

if __name__ == "__main__":
    start_app()