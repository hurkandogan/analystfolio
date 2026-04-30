from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.infrastructure.database import Base
import enum

class BotState(str, enum.Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    IDLE = "IDLE"

class SystemLog(Base):
    __tablename__ = "system_logs"
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String(20)) # INFO, ERROR, WARNING
    module = Column(String(50))
    message = Column(Text)