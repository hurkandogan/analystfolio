from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date, time
from pydantic import BaseModel

from app.infrastructure.database import get_db
from app.infrastructure.models.calendar import ExchangeCalendar

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

# --- DTOs ---
class CalendarEntryDTO(BaseModel):
    id: Optional[int] = None
    exchange: str
    date: date
    is_open: bool
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/", response_model=List[CalendarEntryDTO])
async def get_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    exchange: str = "NYSE",
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExchangeCalendar).where(ExchangeCalendar.exchange == exchange)
    
    if start_date:
        stmt = stmt.where(ExchangeCalendar.date >= start_date)
    if end_date:
        stmt = stmt.where(ExchangeCalendar.date <= end_date)
        
    stmt = stmt.order_by(ExchangeCalendar.date.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=CalendarEntryDTO)
async def create_or_update_entry(entry: CalendarEntryDTO, db: AsyncSession = Depends(get_db)):
    # Check if exists
    stmt = select(ExchangeCalendar).where(
        ExchangeCalendar.exchange == entry.exchange,
        ExchangeCalendar.date == entry.date
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if existing:
        # Update
        existing.is_open = entry.is_open
        existing.open_time = entry.open_time
        existing.close_time = entry.close_time
        existing.note = entry.note
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create
        new_entry = ExchangeCalendar(
            exchange=entry.exchange,
            date=entry.date,
            is_open=entry.is_open,
            open_time=entry.open_time,
            close_time=entry.close_time,
            note=entry.note
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)
        return new_entry

@router.delete("/{entry_id}")
async def delete_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await db.get(ExchangeCalendar, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    await db.delete(entry)
    await db.commit()
    return {"status": "success"}
