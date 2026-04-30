import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date, timezone
from sqlalchemy import select, func
from ib_async import Stock

from app.strategies.base import BaseStrategy
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.database import AsyncSessionLocal
from app.data.repository import DataRepository
from app.data.fetcher import market_fetcher
from app.data.processor import market_processor
from app.data.validator import market_validator

class CandleMinerBot(BaseStrategy):
    def __init__(self):
        super().__init__(name="DailyCandleMiner")

    async def execute(self):

        if not ibkr_client.is_connected():
            await self.log("IBKR not connected! Task stopped.", "ERROR")
            return

        async with AsyncSessionLocal() as session:
            repo = DataRepository(session)
            instruments = await repo.get_instruments_by_role(['TRADE'])
            total_count = len(instruments)
            
            await self.log(f"Analysis started. Total Instruments: {total_count}")

            for index, instr in enumerate(instruments):
                if not self.is_running:
                    await self.log("Bot stopped by user.", "INFO")
                    break

                try:
                    # 1. FETCH (Data Fetching)
                    bars, is_deep_scan = await market_fetcher.get_historical_bars(repo, instr, timeframe='1h')
                    
                    if not bars:
                        continue

                    # Prepend DB bars if not deep scan to maintain indicator context (MA200 needs 200 days = ~1400 hours)
                    if not is_deep_scan:
                        db_bars = await repo.get_bars(instr.id, timeframe='1h', limit=1500)
                        
                        class DummyBar:
                            def __init__(self, d):
                                # Ensure datetime is timezone-aware before appending to IBKR bars
                                ts = d.timestamp
                                if ts.tzinfo is None:
                                    ts = ts.replace(tzinfo=timezone.utc)
                                self.date = ts
                                self.open = d.open
                                self.high = d.high
                                self.low = d.low
                                self.close = d.close
                                self.volume = d.volume
                                
                        historical_dummy = [DummyBar(b) for b in db_bars]
                        bars.extend(historical_dummy)

                    # 2. PROCESS (Processing & Analysis)
                    save_data = market_processor.process_bars(instr.id, bars, timeframe='1h')
                    
                    if not save_data:
                        continue

                    # 3. VALIDATE (Validation)
                    valid_data = market_validator.validate_bars(instr.symbol, save_data)
                    
                    # 4. SAVE (Saving)
                    # If deep scan, delete old data
                    if is_deep_scan:
                        await repo.delete_market_data(instr.id)
                        await self.log(f"{instr.symbol}: Deep Scan - Old data cleared and rewritten.")

                    await repo.upsert_market_data(valid_data)
                    
                    # Success log and meta update
                    instr.updated_at = datetime.now(timezone.utc)
                    repo.add(instr)
                    await repo.commit()

                    if len(valid_data) < len(save_data):
                        await self.log(f"⚠️ {instr.symbol}: {len(save_data) - len(valid_data)} corrupt bars removed.", "WARNING")

                except Exception as e:
                    await self.log(f"Error ({instr.symbol}): {str(e)}", "ERROR")
                
                # Progress status
                if (index + 1) % 5 == 0 or (index + 1) == total_count:
                    progress = int(((index + 1) / total_count) * 100)
                    await self.log(f"Progress: {instr.symbol} ({progress}%)")

    def stop(self):
        """Stops the bot."""
        self.is_running = False