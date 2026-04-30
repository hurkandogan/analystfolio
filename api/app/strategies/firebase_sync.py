import asyncio
import math
from datetime import datetime
from app.strategies.base import BaseStrategy
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.yahoo_client import yahoo_client
from app.infrastructure.firebase_client import firebase_client
from app.infrastructure.database import AsyncSessionLocal
from app.data.repository import DataRepository

class FirebaseSyncBot(BaseStrategy):
    def __init__(self):
        super().__init__("FirebaseSync")

    async def execute(self):
        if not ibkr_client.is_connected():
            await self.log("IBKR is not connected. Skipping sync.", "ERROR")
            return

        try:
            # reqMarketDataType(4) is Delayed-Frozen. 
            # This is essential to get SOME price for non-subscribed symbols without errors.
            ibkr_client.ib.reqMarketDataType(4) 
            
            # Use non-blocking reqAccountUpdates and a sleep to avoid "event loop already running" errors
            # which occur when reqAccountUpdatesAsync is called within a web-triggered task.
            ibkr_client.ib.reqAccountUpdates(True)
            await asyncio.sleep(3.0) 
        except Exception as e:
            await self.log(f"⚠️ IBKR Update Stream Warning: {e}", "WARNING")
            # For other errors, we might still have data from a previous successful update, 
            # but timeout is particularly dangerous as it implies we might have partial data.

        await asyncio.sleep(1.0)

        portfolio = ibkr_client.ib.portfolio()
        account_values = ibkr_client.ib.accountValues()
        
        cash_positions = []
        for v in account_values:
            if v.tag == 'CashBalance' and v.currency != 'BASE':
                try:
                    val = float(v.value)
                    if abs(val) > 1.0:
                        cash_positions.append({'currency': v.currency, 'value': val})
                except ValueError:
                    pass

        await self.log(f"Fetched IBKR Data: {len(portfolio)} positions, {len(cash_positions)} cash accounts.", "INFO")

        enrichment_map = {}
        async with AsyncSessionLocal() as session:
            repo = DataRepository(session)
            instruments = await repo.get_instruments_by_role(['TRADE', 'WATCH']) 
            
            for instr in instruments:
                enrichment_map[instr.symbol] = {
                    "sector": instr.sector,
                    "industry": instr.industry,
                    "name": instr.name
                }

        # Sync Portfolio Data
        if not portfolio and not cash_positions:
            await self.log("IBKR portfolio and cash positions are empty. Skipping sync to prevent data loss.", "WARNING")
        else:
            try:
                success, msg = await asyncio.wait_for(
                    firebase_client.sync_portfolio(portfolio, cash_positions, enrichment_map), 
                    timeout=30.0
                )
                if success:
                    await self.log(f"IBKR Portfolio Sync Success: {msg}", "SUCCESS")
                else:
                    await self.log(f"IBKR Portfolio Sync Failed: {msg}", "ERROR")
            except asyncio.TimeoutError:
                await self.log("IBKR Portfolio Sync Timeout (30s).", "ERROR")
            except Exception as e:
                await self.log(f"IBKR Portfolio Sync Error: {e}", "ERROR")

        # --- Kraken, Crypto & Manual Assets Sync ---
        try:
            await firebase_client.sync_kraken_portfolio()
            await firebase_client.sync_all_users_crypto()
            await firebase_client.sync_all_users_manual_assets()
            await self.log("Kraken, Crypto and Manual assets successfully synced.", "SUCCESS")
        except Exception as e:
            await self.log(f"Additional Sync (Kraken/Crypto/Manual) Error: {e}", "ERROR")

        # --- Currency Sync ---
        try:
            yahoo_currency_map = {
                "EURUSD": "EURUSD=X",
                "USDCHF": "USDCHF=X",
                "USDJPY": "USDJPY=X",
                "USDHKD": "USDHKD=X",
                "USDTRY": "USDTRY=X",
                "GBPUSD": "GBPUSD=X"
            }
            
            yahoo_results = await yahoo_client.get_prices(yahoo_currency_map)
            
            currency_data = []
            today_str = datetime.now().strftime("%d/%m/%Y")
            
            for key, val in yahoo_results.items():
                rate = val.get('price')
                
                if not rate or math.isnan(rate) or rate <= 0:
                    continue
                
                clean_key = key.split('=')[0]
                base = clean_key[:3]
                quote = clean_key[3:]
                
                clean_key = key.split('=')[0]
                base = clean_key[:3]
                quote = clean_key[3:]
                
                currency_data.append({
                    "id": f"{base}_{quote}",
                    "from": base,
                    "to": quote,
                    "rate": float(rate),
                    "date": today_str,
                    "source": "YAHOO"
                })
                
                currency_data.append({
                    "id": f"{quote}_{base}",
                    "from": quote,
                    "to": base,
                    "rate": float(1.0 / rate),
                    "date": today_str,
                    "source": "YAHOO"
                })
            
            if currency_data:
                await firebase_client.sync_currencies(currency_data)
                await self.log(f"Synced {len(currency_data)} currency rates from Yahoo.", "SUCCESS")
                
        except Exception as e:
            await self.log(f"Currency Sync Error: {e}", "ERROR")

        # --- Daily Snapshot ---
        try:
            await firebase_client.create_all_users_daily_snapshots()
            await self.log("Daily snapshot created/updated.", "SUCCESS")
        except Exception as e:
            await self.log(f"Snapshot Error: {e}", "ERROR")
