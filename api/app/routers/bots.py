from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database import get_db
from app.infrastructure.models.scheduler import BotSchedule, BotExecution
from app.infrastructure.models.system import SystemLog
from app.core.scheduler import scheduler
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/bots", tags=["Bots"])

class BotStatusDTO(BaseModel):
    id: str
    name: str
    status: str
    last_run_at: Optional[datetime]
    is_auto_run: bool
    run_interval_mins: str
    info_message: Optional[str]

class LogEntryDTO(BaseModel):
    time: str
    module: str
    type: str
    msg: str

@router.get("/", response_model=List[BotStatusDTO])
async def get_bots(db: AsyncSession = Depends(get_db)):
    """Returns the status of all bots in the system."""
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
        
        # Frontend compatibility: 'RUNNING' if active (for Stop button), otherwise 'STOPPED'
        status = "RUNNING" if s.is_active else "STOPPED"
        
        info_msg = ""
        if last_exec and last_exec.status == "FAILED":
             info_msg = f"Error: {last_exec.error_message[:40]}..."
        elif next_run:
             info_msg = f"Next: {next_run.strftime('%H:%M:%S')}"

        results.append(BotStatusDTO(
            id=s.bot_name,
            name=s.bot_name,
            status=status,
            last_run_at=s.last_run_at,
            is_auto_run=s.is_active,
            run_interval_mins=s.cron_expression,
            info_message=info_msg
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

@router.get("/logs", response_model=List[LogEntryDTO])
async def get_logs(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Fetches historical system logs."""
    from sqlalchemy import desc
    stmt = select(SystemLog).order_by(desc(SystemLog.timestamp)).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [
        LogEntryDTO(
            time=l.timestamp.strftime("%H:%M:%S") if l.timestamp else "N/A",
            module=l.module,
            type=l.level,
            msg=l.message
        ) for l in logs
    ]
