import asyncio
from sqlalchemy import select
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import Instrument, MarketDataCache

async def main():
    async with AsyncSessionLocal() as session:
        # Check COF or ANET
        stmt = select(Instrument).where(Instrument.symbol == 'COF')
        instr = (await session.execute(stmt)).scalar_one_or_none()
        
        if instr:
            bars_stmt = select(MarketDataCache).where(
                MarketDataCache.instrument_id == instr.id,
                MarketDataCache.timeframe == '1h'
            ).order_by(MarketDataCache.timestamp.desc()).limit(5)
            bars = (await session.execute(bars_stmt)).scalars().all()
            for b in bars:
                print(f"{b.timestamp} | C: {b.close} | MA50: {b.ma_50} | RSI: {b.rsi_14}")

asyncio.run(main())
