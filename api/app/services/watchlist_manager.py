from datetime import datetime, timezone
from sqlalchemy import select
from app.infrastructure.models.trading import PremiumWatchlist

class WatchlistManager:
    @staticmethod
    async def process_instrument(db, instr, score, wl_min_score):
        """Adds, updates, or reactivates an instrument in the premium watchlist."""
        if score >= wl_min_score:
            wl_stmt = select(PremiumWatchlist).where(PremiumWatchlist.ticker == instr.symbol)
            wl_item = (await db.execute(wl_stmt)).scalar_one_or_none()
            
            if not wl_item:
                new_wl = PremiumWatchlist(
                    ticker=instr.symbol,
                    source='Auto',
                    fundamental_score=score,
                    current_state='Watching',
                    is_active=True
                )
                db.add(new_wl)
                return "ADDED", score
            elif wl_item.is_active:
                if wl_item.fundamental_score != score:
                    wl_item.fundamental_score = score
                    return "UPDATED", score
            elif not wl_item.is_active and score >= 85:
                wl_item.is_active = True
                wl_item.fundamental_score = score
                wl_item.added_at = datetime.now(timezone.utc)
                return "REACTIVATED", score
        elif score < wl_min_score:
            # Auto-Evict if score dropped
            wl_stmt = select(PremiumWatchlist).where(
                PremiumWatchlist.ticker == instr.symbol,
                PremiumWatchlist.source == 'Auto',
                PremiumWatchlist.is_active == True
            )
            wl_item = (await db.execute(wl_stmt)).scalar_one_or_none()
            if wl_item:
                wl_item.is_active = False
                return "EVICTED", score
        
        return None, score

    @staticmethod
    async def deactivate_if_tracking_stopped(db, symbol, status):
        """Deactivates a watchlist item if tracking has stopped (CLOSED or None status)."""
        if status in ['CLOSED', None]:
            wl_stmt = select(PremiumWatchlist).where(
                PremiumWatchlist.ticker == symbol, 
                PremiumWatchlist.source == 'Auto', 
                PremiumWatchlist.is_active == True
            )
            wl_item = (await db.execute(wl_stmt)).scalar_one_or_none()
            if wl_item:
                wl_item.is_active = False
                return True
        return False
