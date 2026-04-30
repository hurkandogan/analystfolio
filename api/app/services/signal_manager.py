import json
from datetime import datetime, date, timezone
from sqlalchemy import select, func, desc
from app.infrastructure.models.trading import TradeSignal
from app.infrastructure.database import AsyncSessionLocal

class SignalManager:
    def __init__(self, bot_name: str):
        self.bot_name = bot_name

    async def get_latest_active_signal(self, db, instrument_id):
        """Fetch the latest signal that is not CLOSED."""
        stmt = select(TradeSignal).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == self.bot_name,
            TradeSignal.status != 'CLOSED'
        ).order_by(desc(TradeSignal.created_at)).limit(1)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_daily_signal(self, db, instrument_id):
        """Check if there is already a signal for today."""
        today = date.today()
        stmt = select(TradeSignal).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == self.bot_name,
            func.date(TradeSignal.created_at) == today
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def determine_new_status(self, db, instrument_id, score, min_score, is_chain_active):
        """Determines the status of the signal based on current score and history."""
        if is_chain_active:
            if score >= min_score:
                return "OPEN"
            else:
                # 5-day rule: If the last 4 signals are also WEAK, make it CLOSED.
                weak_check_stmt = select(TradeSignal.status).where(
                    TradeSignal.instrument_id == instrument_id,
                    TradeSignal.bot_name == self.bot_name
                ).order_by(desc(TradeSignal.created_at)).limit(4)
                
                last_statuses = (await db.execute(weak_check_stmt)).scalars().all()
                weak_count = sum(1 for s in last_statuses if s == 'WEAK')
                
                if weak_count >= 4:
                    return "CLOSED"
                return "WEAK"
        else:
            if score >= min_score:
                return "NEW"
            return None

    async def calculate_chain_count(self, db, instrument_id, daily_signal_exists):
        """Calculates the position of this signal in the current chain."""
        # Find the date of the last CLOSED signal
        last_closed_stmt = select(func.max(TradeSignal.created_at)).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == self.bot_name,
            TradeSignal.status == 'CLOSED'
        )
        last_closed_date = (await db.execute(last_closed_stmt)).scalar()
        
        count_query = select(func.count()).where(
            TradeSignal.instrument_id == instrument_id,
            TradeSignal.bot_name == self.bot_name
        )
        
        if last_closed_date:
            count_query = count_query.where(TradeSignal.created_at > last_closed_date)
            
        chain_count = (await db.execute(count_query)).scalar() or 0
        return chain_count if daily_signal_exists else (chain_count + 1)
