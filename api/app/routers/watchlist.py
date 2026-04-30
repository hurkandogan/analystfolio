from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.infrastructure.database import get_db
from app.infrastructure.models.trading import PremiumWatchlist

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

class WatchlistBase(BaseModel):
    ticker: str
    fundamental_score: Optional[float] = None

class WatchlistResponse(WatchlistBase):
    id: int
    source: str
    added_at: datetime
    last_signal_at: Optional[datetime]
    current_state: str

    class Config:
        orm_mode = True

@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Fetches the active Premium Watchlist."""
    stmt = select(PremiumWatchlist).where(PremiumWatchlist.is_active == True).order_by(PremiumWatchlist.added_at.desc())
    items = (await db.execute(stmt)).scalars().all()
    return items

@router.post("/", response_model=WatchlistResponse)
async def add_to_watchlist(item: WatchlistBase, db: AsyncSession = Depends(get_db)):
    """Manually adds a high-quality stock (ticker) to the watchlist."""
    # Check if exists
    stmt = select(PremiumWatchlist).where(PremiumWatchlist.ticker == item.ticker.upper())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Ticker already in watchlist")
        else:
            # Resurrect deleted item
            existing.is_active = True
            existing.source = "Manual"
            existing.fundamental_score = item.fundamental_score
            existing.current_state = "Watching"
            existing.added_at = datetime.now() # Reset added time
            await db.commit()
            await db.refresh(existing)
            return existing
        
    new_item = PremiumWatchlist(
        ticker=item.ticker.upper(),
        source="Manual",
        fundamental_score=item.fundamental_score,
        current_state="Watching",
        is_active=True
    )
    
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item

@router.delete("/{watchlist_id}")
async def remove_from_watchlist(watchlist_id: int, db: AsyncSession = Depends(get_db)):
    """Deletes a manually added stock."""
    stmt = select(PremiumWatchlist).where(PremiumWatchlist.id == watchlist_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if not existing or not existing.is_active:
         raise HTTPException(status_code=404, detail="Item not found")
         
    existing.is_active = False # Soft delete
    await db.commit()
    return {"status": "success"}
