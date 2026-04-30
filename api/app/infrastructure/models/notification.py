from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SAEnum
from sqlalchemy.sql import func
from app.infrastructure.database import Base
import enum

class NotificationChannel(str, enum.Enum):
    TELEGRAM = "TELEGRAM"
    TWITTER = "TWITTER"

class NotificationScope(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

class NotificationStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class Notification(Base):
    __tablename__ = 'notifications'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    channel = Column(SAEnum(NotificationChannel), nullable=False)
    scope = Column(SAEnum(NotificationScope), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(SAEnum(NotificationStatus), default=NotificationStatus.SENT)
    meta = Column(JSON, nullable=True) # Stores tweet_id, error message, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
