from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

class BotSchedule(Base):
    __tablename__ = "bot_schedules"

    bot_name: Mapped[str] = mapped_column(String, primary_key=True)
    cron_expression: Mapped[str] = mapped_column(String)  # E.g.: "*/30 * * * *" or "0 9 * * 1-5"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    executions: Mapped[list["BotExecution"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")

class BotExecution(Base):
    __tablename__ = "bot_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_name: Mapped[str] = mapped_column(ForeignKey("bot_schedules.bot_name"))
    
    status: Mapped[str] = mapped_column(String)  # RUNNING, COMPLETED, FAILED, INTERRUPTED
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    log_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Summary log
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    schedule: Mapped["BotSchedule"] = relationship(back_populates="executions")

    def duration_seconds(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0