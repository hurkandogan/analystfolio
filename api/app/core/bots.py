from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database import get_db
from app.infrastructure.models.scheduler import BotSchedule, BotExecution
from app.core.scheduler import scheduler
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/bots", tags=["Bots"])

class BotStatusDTO(BaseModel):
    bot_name: str
    is_active: bool
    cron_expression: str
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_status: Optional[str]
    last_error: Optional[str]

@router.get("/", response_model=List[BotStatusDTO])
async def get_bots(db: AsyncSession = Depends(get_db)):
    """Fetches the status of all bots in the system."""
    stmt = select(BotSchedule)
    schedules = (await db.execute(stmt)).scalars().all()
    
    results = []
    for s in schedules:
        # Get last execution status
        exec_stmt = select(BotExecution).where(BotExecution.bot_name == s.bot_name).order_by(BotExecution.start_time.desc()).limit(1)
        last_exec = (await db.execute(exec_stmt)).scalar_one_or_none()
        
        # Get next run time from APScheduler
        job = scheduler.scheduler.get_job(s.bot_name)
        next_run = job.next_run_time if job else None
        
        results.append(BotStatusDTO(
            bot_name=s.bot_name,
            is_active=s.is_active,
            cron_expression=s.cron_expression,
            last_run_at=s.last_run_at,
            next_run_at=next_run,
            last_status=last_exec.status if last_exec else "NEVER",
            last_error=last_exec.error_message if last_exec else None
        ))
    return results

@router.post("/{bot_name}/start")
async def start_bot(bot_name: str):
    try:
        await scheduler.toggle_bot(bot_name, True)
        return {"status": "started", "bot": bot_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{bot_name}/stop")
async def stop_bot(bot_name: str):
    try:
        await scheduler.toggle_bot(bot_name, False)
        return {"status": "stopped", "bot": bot_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{bot_name}/run")
async def run_bot(bot_name: str):
    await scheduler.trigger_bot(bot_name)
    return {"status": "triggered", "bot": bot_name}
