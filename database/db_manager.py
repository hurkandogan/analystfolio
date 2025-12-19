from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from .models import Base, Instrument, Watchlist
from datetime import datetime

DB_URL = "postgresql://postgres@localhost:5432/analystfolio_db"

class DBManager:
    def __init__(self):
        self.engine = create_engine(DB_URL)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def upsert_instrument_from_ibkr(self, data: dict):

        if not isinstance(data, dict):
            print(f"❌ Upsert Error: Expected dict, got {type(data)}")
            return False, None

        session = self.get_session()
        try:
            instrument = session.query(Instrument).filter_by(symbol=data['symbol']).first()
            
            if not instrument:
                instrument = Instrument(symbol=data['symbol'])
                session.add(instrument)
            
            if data.get('con_id'):
                instrument.con_id = data['con_id']

            if data.get('con_id'): instrument.con_id = data['con_id']
            if data.get('name'): instrument.name = data['name']
            if data.get('sector'): instrument.sector = data['sector']
            if data.get('industry'): instrument.industry = data['industry']
            if data.get('last_price'): instrument.last_price = data['last_price']
            if data.get('close_price'): instrument.close_price = data['close_price']

            instrument.sec_type = data.get('sec_type', 'STK')
            instrument.currency = data.get('currency', 'USD')
            instrument.exchange = data.get('exchange', 'SMART')
            instrument.updated_at = datetime.utcnow()
            
            session.commit()
            print(f"💾 Instrument upserted: {data['symbol']}")
            return True, instrument.id
        except Exception as e:
            session.rollback()
            print(f"❌ Upsert Error: {e}")
            return False, None
        finally:
            session.close()

    def add_stock_to_watchlist(self, symbol: str, note: str = ""):
        session = self.get_session()
        try:
            instrument = session.query(Instrument).filter_by(symbol=symbol).first()
            
            if not instrument:
                return False, "Instrument not found in DB. Validate first."
            
            from database.models import Watchlist
            
            entry = session.query(Watchlist).filter_by(instrument_id=instrument.id).first()
            
            if entry:
                entry.note = note
                msg = "Asset already in watchlist. Note updated."
            else:
                new_entry = Watchlist(instrument_id=instrument.id, note=note)
                session.add(new_entry)
                msg = "Asset added to watchlist."
            
            session.commit()
            print(f"✅ Watchlist updated: {symbol}")
            return True, msg
            
        except Exception as e:
            session.rollback()
            print(f"❌ Watchlist Error: {e}")
            return False, str(e)
        finally:
            session.close()
    
    def delete_instrument(self, symbol: str):
        session = self.get_session()
        try:
            instr = session.query(Instrument).filter_by(symbol=symbol).first()
            if not instr:
                return False, "Instrument not found."

            session.query(Watchlist).filter_by(instrument_id=instr.id).delete()
            
            session.delete(instr)
            
            session.commit()
            print(f"🗑️ Deleted permanently: {symbol}")
            return True, f"{symbol} deleted successfully."
            
        except Exception as e:
            session.rollback()
            print(f"❌ Delete Error: {e}")
            return False, str(e)
        finally:
            session.close()

    def get_asset_details(self, symbol: str):
        session = self.get_session()
        try:
            # Left Join ile hepsini alalım
            result = session.query(Instrument, Watchlist).\
                outerjoin(Watchlist, Instrument.id == Watchlist.instrument_id).\
                filter(Instrument.symbol == symbol).\
                first()
            
            if not result:
                return None
            
            instr, watch_item = result
            
            return {
                "symbol": instr.symbol,
                "name": instr.name,
                "sector": instr.sector,
                "industry": instr.industry,
                "data_role": instr.data_role,
                "note": watch_item.note if watch_item else "",
                "con_id": instr.con_id
            }
        finally:
            session.close()

    def update_asset_metadata(self, symbol: str, updates: dict):
        session = self.get_session()
        try:
            instr = session.query(Instrument).filter_by(symbol=symbol).first()
            if not instr:
                return False, "Asset not found."
            
            # 1. Instrument Tablosunu Güncelle
            if "sector" in updates: instr.sector = updates["sector"]
            if "industry" in updates: instr.industry = updates["industry"]
            if "data_role" in updates: instr.data_role = updates["data_role"]
            
            # 2. Watchlist Tablosunu Güncelle (Note)
            if "note" in updates:
                watch_item = session.query(Watchlist).filter_by(instrument_id=instr.id).first()
                if watch_item:
                    watch_item.note = updates["note"]
                else:
                    # Eğer not yazdıysa ama listede yoksa ekleyelim
                    new_item = Watchlist(instrument_id=instr.id, note=updates["note"])
                    session.add(new_item)

            session.commit()
            return True, "Updated successfully."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()

    def get_dashboard_data(self):
        session = self.get_session()
        data = []
        try:
            results = session.query(Instrument, Watchlist).\
                outerjoin(Watchlist, Instrument.id == Watchlist.instrument_id).\
                order_by(Instrument.symbol).\
                all()
            
            for i, w in results:
                
                if not i:
                    continue

                change_pct = 0.0
                if i.last_price and i.close_price and i.close_price > 0:
                    change_pct = ((i.last_price - i.close_price) / i.close_price) * 100
                
                row = {
                    "id": i.id,
                    "symbol": i.symbol,
                    "name": i.name if i.name else "",
                    "sector": i.sector if i.sector else "-",
                    "price": i.last_price if i.last_price else 0.0,
                    "change": round(change_pct, 2),
                    "pe": "-", #TODO get PE ratio if available
                    "role": i.data_role if i.data_role else "N/A"
                }
                data.append(row)
                
            return data
            
        except Exception as e:
            print(f"❌ Dashboard Data Error: {e}")
            return []
        finally:
            session.close()


    def get_watchlist_count(self):
        session = self.get_session()
        try:
            count = session.query(func.count(Watchlist.id)).scalar()
            return count
        finally:
            session.close()

    def get_all_watchlist_symbols(self):
        session = self.get_session()
        try:
            results = session.query(Instrument.symbol).join(Watchlist).all()
            return [r[0] for r in results]
        finally:
            session.close()

    def log_system_event(self, level: str, module: str, message: str):
        session = self.get_session()
        try:
            from database.models import SystemLog # Model importu
            
            new_log = SystemLog(
                level=level,
                module=module,
                message=message
            )
            session.add(new_log)
            session.commit()
        except Exception as e:
            print(f"❌ LOGGING ERROR: {e}")
        finally:
            session.close()