from typing import List, Optional, Any, Sequence
from datetime import date
from sqlalchemy import select, func, desc, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import (
    Instrument, 
    FundamentalCache, 
    MarketDataCache, 
    TradeSignal
)

class DataRepository:
    """
    Repository class that abstracts database operations.
    Bots should use this class instead of writing direct SQL queries.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_instruments_by_role(
        self,
        roles: List[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Sequence[Instrument]:
        """Fetches instruments with specific roles.

        Args:
            roles: Data roles to filter by. Defaults to ['TRADE', 'WATCH'].
            limit: Maximum number of rows to return. None means no limit.
            offset: Number of rows to skip. Used for pagination.
        """
        if roles is None:
            roles = ['TRADE', 'WATCH']
        stmt = select(Instrument).where(Instrument.data_role.in_(roles))
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_fundamentals(self) -> Sequence[tuple[Instrument, FundamentalCache]]:
        """
        Fetches the latest fundamental data for instruments in the TRADE role.
        Return: List[(Instrument, FundamentalCache)]
        """
        # Find max date for each instrument
        subq = select(
            FundamentalCache.instrument_id,
            func.max(FundamentalCache.date).label("max_date")
        ).group_by(FundamentalCache.instrument_id).subquery()

        # Join operations
        stmt = select(Instrument, FundamentalCache).join(
            FundamentalCache, 
            (Instrument.id == FundamentalCache.instrument_id)
        ).join(
            subq,
            (FundamentalCache.instrument_id == subq.c.instrument_id) & 
            (FundamentalCache.date == subq.c.max_date)
        ).where(Instrument.data_role == 'TRADE')
        
        result = await self.session.execute(stmt)
        return result.all()

    async def get_fundamental_dates(self, instrument_id: int, start_date: date) -> Sequence[date]:
        """Fetches available fundamental data dates after a specific date."""
        stmt = select(FundamentalCache.date).where(
            FundamentalCache.instrument_id == instrument_id,
            FundamentalCache.date >= start_date
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_bars(self, instrument_id: int, timeframe: str, limit: int = 200) -> Sequence[MarketDataCache]:
        """
        Fetches historical price data (MarketDataCache).
        Results are sorted from newest to oldest (DESC).
        """
        stmt = select(MarketDataCache).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == timeframe
        ).order_by(MarketDataCache.timestamp.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_daily_signal(self, instrument_id: int, bot_name: str) -> Optional[TradeSignal]:
        """Is there a signal produced for today?"""
        today = date.today()
        stmt = select(TradeSignal).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == bot_name,
            func.date(TradeSignal.created_at) == today
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_signal(self, instrument_id: int, bot_name: str) -> Optional[TradeSignal]:
        """Fetches a signal that hasn't been closed yet (Active/New/Weak/Re-Open)."""
        stmt = select(TradeSignal).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == bot_name,
            TradeSignal.status != 'CLOSED'
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_signal_count(self, instrument_id: int, bot_name: str) -> int:
        """Fetches total signal count."""
        stmt = select(func.count()).select_from(TradeSignal).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == bot_name
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    def add(self, obj: Any):
        """Adds a new object to the session."""
        self.session.add(obj)
    
    async def commit(self):
        """Saves changes to the database."""
        await self.session.commit()

    async def get_latest_bar_timestamp(self, instrument_id: int, timeframe: str) -> Optional[Any]:
        """Returns the date of the latest bar for the specified instrument and period."""
        stmt = select(func.max(MarketDataCache.timestamp)).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == timeframe
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def delete_market_data(self, instrument_id: int):
        """Deletes all market data for an instrument (for Deep Scan)."""
        stmt = delete(MarketDataCache).where(MarketDataCache.instrument_id == instrument_id)
        await self.session.execute(stmt)

    async def upsert_market_data(self, data_list: List[dict]):
        """
        Performs bulk data saving. Updates if there's a conflict.
        """
        if not data_list:
            return

        # Process in chunks (for Postgres limit)
        chunk_size = 1000
        for i in range(0, len(data_list), chunk_size):
            chunk = data_list[i:i + chunk_size]
            
            stmt = insert(MarketDataCache).values(chunk)
            do_update_stmt = stmt.on_conflict_do_update(
                index_elements=['instrument_id', 'timestamp', 'timeframe'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'ma_50': stmt.excluded.ma_50,
                    'ma_200': stmt.excluded.ma_200,
                    'rsi_14': stmt.excluded.rsi_14,
                    'daily_return': stmt.excluded.daily_return
                }
            )
            await self.session.execute(do_update_stmt)
