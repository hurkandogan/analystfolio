import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter.scrolledtext import ScrolledText
from datetime import datetime

class LogPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bootstyle="dark")
        self.pack(side=BOTTOM, fill=X)
        
        # Yüksekliği ayarlayabilirsin (height=8 satır demek)
        self.text_area = ScrolledText(self, height=8, state="disabled", bg="#0f0f0f", fg="white", font=("Consolas", 9))
        self.text_area.pack(fill=BOTH, expand=True, padx=2, pady=2)

        # Renk Etiketleri (Tags)
        self.text_area.tag_config("INFO", foreground="#2ecc71")    # Yeşil
        self.text_area.tag_config("WARNING", foreground="#f39c12") # Turuncu
        self.text_area.tag_config("ERROR", foreground="#e74c3c")   # Kırmızı
        self.text_area.tag_config("TIME", foreground="#95a5a6")    # Gri

    def write_log(self, level, module, message):
        self.text_area.config(state="normal") # Yazmak için kilidi aç
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format: [SAAT] [LEVEL] [MODULE] Mesaj
        self.text_area.insert(END, f"[{timestamp}] ", "TIME")
        self.text_area.insert(END, f"[{level}] ", level) # Level rengini kullan
        self.text_area.insert(END, f"[{module}] {message}\n")
        
        self.text_area.see(END) # En aşağıya kaydır (Otomatik scroll)
        self.text_area.config(state="disabled") # Tekrar kilitle (Kullanıcı değiştiremesin)