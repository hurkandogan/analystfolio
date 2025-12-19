import pandas as pd
import os
from database.db_manager import DBManager, Instrument

def load_csv_data(filepath, source_name):
    if not os.path.exists(filepath):
        print(f"⚠️ File not found: {filepath}")
        return pd.DataFrame()

    try:
        print(f"📂 Reading {source_name} CSV...")
        df = pd.read_csv(filepath)
        
        # STRATEJİ: İsimlere takılmadan ilk 4 sütunu alıyoruz.
        # Böylece "ICB Industry[14]" gibi saçma başlıklardan etkilenmeyiz.
        # Sütun sırası: Symbol, Name, Sector, Industry
        df = df.iloc[:, [0, 1, 2, 3]].copy()
        
        # Standart isimleri ver
        df.columns = ['symbol', 'name', 'sector', 'industry']
        df['role'] = 'TRADE'
        
        print(f"✅ Loaded {len(df)} rows from {source_name}.")
        return df

    except Exception as e:
        print(f"❌ Error reading {source_name}: {e}")
        return pd.DataFrame()

def fetch_and_seed_market():
    print("🚀 Market Loader (CSV Mode) Started...")
    db = DBManager()
    session = db.get_session()
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    NASDAQ_FILE = os.path.join(BASE_DIR, 'raw_data', 'nasdaq.csv')
    SP500_FILE = os.path.join(BASE_DIR, 'raw_data', 'sp500.csv')

    all_stocks = pd.DataFrame()

    # 1. NASDAQ
    ndx_data = load_csv_data(NASDAQ_FILE, "Nasdaq")
    all_stocks = pd.concat([all_stocks, ndx_data])

    # 2. S&P 500
    sp_data = load_csv_data(SP500_FILE, "S&P 500")
    all_stocks = pd.concat([all_stocks, sp_data])

    # 3. SAVE TO DB
    if all_stocks.empty:
        print("❌ No data loaded.")
        return

    # Duplicate Temizliği
    all_stocks = all_stocks.drop_duplicates(subset=['symbol'], keep='first')
    
    print(f"💾 Saving {len(all_stocks)} unique assets to Database...")
    
    added_count = 0
    skipped_count = 0
    
    for index, row in all_stocks.iterrows():
        raw_symbol = str(row['symbol'])
        symbol = raw_symbol.replace('.', ' ').strip()
        
        # Başlık satırı karışırsa diye koruma
        if symbol.lower() in ['symbol', 'ticker']: continue

        exists = session.query(Instrument).filter_by(symbol=symbol).first()
        
        if not exists:
            try:
                new_asset = Instrument(
                    symbol=symbol,
                    name=str(row['name']),
                    sec_type='STK',
                    data_role='TRADE',
                    sector=str(row['sector']),
                    industry=str(row['industry']),
                    currency='USD',
                    exchange='SMART'
                )
                session.add(new_asset)
                added_count += 1
            except Exception as e:
                print(f"⚠️ Error adding {symbol}: {e}")
        else:
            skipped_count += 1
    
    try:
        session.commit()
        print(f"🎉 SUCCESS!")
        print(f"➕ Added: {added_count}")
        print(f"⏭️ Skipped: {skipped_count}")
        print(f"📚 Total in DB: {session.query(Instrument).count()}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Database Commit Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fetch_and_seed_market()