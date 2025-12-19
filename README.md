# 📈 Analysfolio Desktop

Bu proje, IBKR API kullanarak yerel bilgisayarda çalışan, algo-trading ve analiz botudur.

## 🚀 Günlük Çalışma Rutini (Her Seferinde Yap!)

Terminali açtığında projeye başlamadan önce **MUTLAKA** sanal ortamı (venv) aktif etmelisin.

Bunu proje klasörünün en üstüne README.md adıyla kaydet. Yarın bir gün "Ben bu ortamı nasıl kuruyordum ya?" dediğinde hayatını kurtaracak.

Markdown

# 🚀 AnalystFolio

Kişisel Algoritmik Trading ve Portföy Yönetim Sistemi.
IBKR (Interactive Brokers) altyapısı, Python ve PostgreSQL kullanır.

---

## 🛠️ Kurulum ve Başlangıç

### 1. Gereksinimler
* Python 3.10+
* Poetry (Paket Yöneticisi)
* PostgreSQL 15+ (Localhost:5432)
* IBKR TWS veya IB Gateway (Açık olmalı)

### 2. Projeyi Kur
```bash
# Bağımlılıkları yükle
poetry install
3. Veritabanı Ayarları
PostgreSQL'de analystfolio_db adında boş bir database oluştur.

alembic.ini dosyasındaki sqlalchemy.url kısmını kendi şifrene göre düzenle.

🏃‍♂️ Komutlar (Cheat Sheet)
Bu projede taskipy kullanıyoruz. Uzun komutlar yerine şu kısayolları kullan:

🟢 Uygulamayı Başlat
Bash

poetry run task start
⛏️ Veri Yükleme (Data Seeding)
Wikipedia'dan S&P 500 ve Nasdaq listelerini indirip veritabanına basar.

Bash

poetry run task scrape
(Manuel ekleme için: poetry run task seed)

🏗️ Veritabanı Yönetimi (Alembic)
models.py dosyasında bir değişiklik yaparsan (yeni tablo, yeni sütun vb.) sırasıyla:

1. Değişikliği Algıla (Migration Dosyası Oluştur):

Bash

poetry run alembic revision --autogenerate -m "degisiklik_mesaji"
2. Veritabanına Uygula (Tabloları Güncelle):

Bash

poetry run alembic upgrade head
⚠️ Acil Durum (Stamp): Eğer veritabanını elle düzelttiysen ve Alembic hata veriyorsa, "Sus ve senkronize olduğunu kabul et" demek için:

Bash

poetry run alembic stamp head
📂 Proje Yapısı
main.py: Uygulamanın giriş kapısı.

ui/: Görsel arayüz (Tkinter) kodları.

database/: Veritabanı bağlantısı ve modeller (models.py).

raw_data/: Scrape edilen ham CSV dosyaları.

migrations/: Alembic versiyon dosyaları.

"Roma bir günde kurulmadı ama AnalystFolio bir gecede ayağa kalktı." - Hafız