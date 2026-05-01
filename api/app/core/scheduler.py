import asyncio
import traceback
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.scheduler import BotSchedule, BotExecution
from app.strategies.base import BaseStrategy

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.registered_bots = {}

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            print("✅ Scheduler Service Started")

    def stop(self):
        self.scheduler.shutdown()
        print("🛑 Scheduler Service Stopped")

    async def sync_with_db(self):
        """Removes bots from DB that are no longer registered in the code."""
        async with AsyncSessionLocal() as db:
            # 1. Get all bot names from DB
            stmt = select(BotSchedule.bot_name)
            result = await db.execute(stmt)
            db_bot_names = result.scalars().all()

            # 2. Identify orphaned bots (In DB but NOT in self.registered_bots)
            active_names = set(self.registered_bots.keys())
            orphans = [name for name in db_bot_names if name not in active_names]

            if orphans:
                print(f"🧹 Found {len(orphans)} orphaned bots in DB: {orphans}")
                for bot_name in orphans:
                    # Fetch the object to let SQLAlchemy handle cascades (if configured)
                    # or manually delete related data first.
                    # Since we have cascade="all, delete-orphan" in relationship,
                    # db.delete(schedule_obj) will work beautifully.
                    orphan_stmt = select(BotSchedule).where(BotSchedule.bot_name == bot_name)
                    orphan_obj = (await db.execute(orphan_stmt)).scalar_one_or_none()
                    
                    if orphan_obj:
                        await db.delete(orphan_obj)
                        print(f"🗑️ Purged orphaned bot data: {bot_name}")
                
                await db.commit()
                print("✨ Database Bot Sync Complete")
            else:
                print("✅ Database Bot Sync: No orphans found.")

    def _schedule_job(self, bot_name: str, cron_expression: str):
        """Adds or replaces a bot job in the APScheduler instance."""
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(
            self._run_job_wrapper,
            trigger=trigger,
            id=bot_name,
            name=bot_name,
            replace_existing=True,
            args=[bot_name]
        )

    async def register_bot(self, bot: BaseStrategy, cron_expression: str):
        self.registered_bots[bot.name] = bot
        
        async with AsyncSessionLocal() as db:
            stmt = select(BotSchedule).where(BotSchedule.bot_name == bot.name)
            schedule = (await db.execute(stmt)).scalar_one_or_none()
            
            if not schedule:
                schedule = BotSchedule(
                    bot_name=bot.name,
                    cron_expression=cron_expression,
                    is_active=True
                )
                db.add(schedule)
                await db.commit()
                print(f"🆕 New Schedule Created: {bot.name} ({cron_expression})")
            else:
                if schedule.cron_expression != cron_expression:
                    schedule.cron_expression = cron_expression
                    await db.commit()
            if not schedule.is_active:
                print(f"⚠️ Bot {bot.name} is INACTIVE in DB. Skipping schedule.")
                return

        self._schedule_job(bot.name, cron_expression)
        print(f"⏰ Scheduled: {bot.name} -> {cron_expression}")

    async def _run_job_wrapper(self, bot_name: str):
        bot = self.registered_bots.get(bot_name)
        if not bot:
            return

        execution_id = None
        
        async with AsyncSessionLocal() as db:
            execution = BotExecution(
                bot_name=bot_name,
                status="RUNNING",
                start_time=datetime.now()
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)
            execution_id = execution.id

        try:
            print(f"🚀 Executing Bot: {bot_name}")
            await bot.execute()
            status = "COMPLETED"
            error_msg = None

        except Exception as e:
            status = "FAILED"
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"❌ Error in {bot_name}: {e}")

        finally:
            async with AsyncSessionLocal() as db:
                stmt = select(BotExecution).where(BotExecution.id == execution_id)
                execution = (await db.execute(stmt)).scalar_one()
                
                execution.end_time = datetime.now()
                execution.status = status
                execution.error_message = error_msg
                
                # Update Schedule table (Last Run)
                sched_stmt = select(BotSchedule).where(BotSchedule.bot_name == bot_name)
                schedule = (await db.execute(sched_stmt)).scalar_one()
                schedule.last_run_at = execution.start_time
                
                await db.commit()

    async def toggle_bot(self, bot_name: str, active: bool):
        """Toggles bot activity (DB + Scheduler)."""
        async with AsyncSessionLocal() as db:
            stmt = select(BotSchedule).where(BotSchedule.bot_name == bot_name)
            schedule = (await db.execute(stmt)).scalar_one_or_none()
            
            if not schedule:
                raise ValueError(f"Bot '{bot_name}' not found.")
            
            schedule.is_active = active
            await db.commit()
            
            cron = schedule.cron_expression

        if active:
            if not self.scheduler.get_job(bot_name):
                if self.registered_bots.get(bot_name):
                    self._schedule_job(bot_name, cron)
            else:
                self.scheduler.resume_job(bot_name)
        else:
            if self.scheduler.get_job(bot_name):
                self.scheduler.pause_job(bot_name)

    async def trigger_bot(self, bot_name: str):
        if bot_name not in self.registered_bots:
            raise ValueError(f"Bot '{bot_name}' not found.")
        print(f"⚡ Manual trigger received for {bot_name}")
        asyncio.create_task(self._run_job_wrapper(bot_name))

scheduler = SchedulerService()