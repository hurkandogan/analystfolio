import asyncio
from sqlalchemy import select
from datetime import date, timedelta
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import Instrument
from app.strategies.base import BaseStrategy
from app.services.fundamental_service import FundamentalService

class FundamentalMinerBot(BaseStrategy):
    def __init__(self):
        super().__init__("FundamentalMiner")
        self.fundamental_service = FundamentalService()

    async def execute(self):
        # Configuration
        deep_scan = False 
        backfill_days = 1
        sleep_between_tickers = 0.5 

        await self.log(f"Fundamental data mining started...", "INFO")
        
        async with AsyncSessionLocal() as db:
            instruments_stmt = select(Instrument).where(Instrument.data_role == 'TRADE')
            instruments = (await db.execute(instruments_stmt)).scalars().all()
            
            total = len(instruments)
            await self.log(f"Mining fundamentals for {total} instruments.", "INFO")

            # Use Yesterday as target date (today's data might be incomplete)
            target_date = date.today() - timedelta(days=1)

            for index, instr in enumerate(instruments):
                if not self.is_running: break
                try:
                    await self.fundamental_service.collect_fundamentals(
                        db, instr, target_date=target_date, deep_scan=deep_scan, backfill_days=backfill_days
                    )
                except Exception as e:
                    await db.rollback()
                    await self.log(f"Failed to collect fundamentals for {instr.symbol}: {e}", "ERROR")
                
                if (index + 1) % 50 == 0:
                    await self.log(f"Mined ({index + 1}/{total}) - Current: {instr.symbol}", "INFO")
                    await db.commit()
                
                await asyncio.sleep(sleep_between_tickers) 
            
            await db.commit()
            await self.log("Fundamental data mining completed successfully.", "SUCCESS")
