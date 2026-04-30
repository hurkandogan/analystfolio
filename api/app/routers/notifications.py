from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.infrastructure.database import get_db
from app.infrastructure.models.notification import Notification, NotificationStatus, NotificationChannel
from app.infrastructure.notifiers.manager import notification_manager

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

# --- DTOs ---
class NotificationDTO(BaseModel):
    id: int
    channel: str
    scope: str
    content: str
    status: str
    created_at: datetime
    meta: Optional[dict] = None

    class Config:
        from_attributes = True

class ResendRequest(BaseModel):
    new_content: Optional[str] = None

# --- Endpoints ---

@router.get("/", response_model=List[NotificationDTO])
async def get_notifications(
    limit: int = 50,
    offset: int = 0,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Notification).order_by(desc(Notification.created_at)).limit(limit).offset(offset)
    
    if channel:
        stmt = stmt.where(Notification.channel == channel)
    if status:
        stmt = stmt.where(Notification.status == status)
        
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{notification_id}/resend")
async def resend_notification(
    notification_id: int, 
    request: ResendRequest = None,
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch original notification
    stmt = select(Notification).where(Notification.id == notification_id)
    original = (await db.execute(stmt)).scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    # 2. Determine content
    content_to_send = request.new_content if (request and request.new_content) else original.content
    
    # 3. Resend via Manager
    # Note: Manager expects channel names as strings in a list
    channels = [original.channel.name] 
    
    # We use 'scope' from original
    await notification_manager.send(
        message=content_to_send,
        scope=original.scope.name,
        channels=channels
    )
    
    return {"status": "success", "message": "Resend triggered"}
