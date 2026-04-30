import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select, func
from app.infrastructure.notifiers.base import BaseNotifier
from app.infrastructure.notifiers.telegram import TelegramNotifier
from app.infrastructure.notifiers.twitter import TwitterNotifier
from app.config import settings
from app.infrastructure.database import async_sessionmaker, engine
from app.infrastructure.models.notification import Notification, NotificationChannel, NotificationScope, NotificationStatus

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Central manager for routing notifications to different channels based on scope.
    Handles:
    - Routing (Private/Public)
    - Rate Limiting (Twitter 21 limit)
    - History Logging (DB)
    """
    def __init__(self):
        self.channels: Dict[str, List[BaseNotifier]] = {
            'PRIVATE': [],
            'PUBLIC': []
        }
        self.initialize_channels()

    def initialize_channels(self):
        # 1. Private Telegram (AnalystFolio Bot -> You)
        if settings.TELEGRAM_PRIVATE_BOT_TOKEN and settings.TELEGRAM_PRIVATE_CHAT_ID:
            private_tg = TelegramNotifier(
                bot_token=settings.TELEGRAM_PRIVATE_BOT_TOKEN,
                chat_id=settings.TELEGRAM_PRIVATE_CHAT_ID,
                name="TelegramPrivate"
            )
            self.channels['PRIVATE'].append(private_tg)
            
        elif settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            private_tg = TelegramNotifier(
                bot_token=settings.TELEGRAM_BOT_TOKEN,
                chat_id=settings.TELEGRAM_CHAT_ID,
                name="TelegramPrivate(Legacy)"
            )
            self.channels['PRIVATE'].append(private_tg)

        # 2. Public Telegram (MetrixFolio Bot -> Channel)
        if settings.TELEGRAM_PUBLIC_BOT_TOKEN and settings.TELEGRAM_PUBLIC_CHANNEL_ID:
            public_tg = TelegramNotifier(
                bot_token=settings.TELEGRAM_PUBLIC_BOT_TOKEN,
                chat_id=settings.TELEGRAM_PUBLIC_CHANNEL_ID,
                name="TelegramPublic"
            )
            self.channels['PUBLIC'].append(public_tg)

        # 3. Twitter (Public) - New Keys
        if settings.TWITTER_CONSUMER_KEY:
             # Use the keys provided by user (mapped in config)
             twitter = TwitterNotifier(
                 api_key=settings.TWITTER_CONSUMER_KEY,
                 api_secret=settings.TWITTER_CONSUMER_KEY_SECRET,
                 access_token=settings.TWITTER_CLIENT_ID_KEY, # User said CLIENT_ID_KEY, double check mapping if fails
                 access_secret=settings.TWITTER_CLIENT_SECRET
             )
             self.channels['PUBLIC'].append(twitter)
             logger.info("✅ Twitter Notifier initialized.")

    async def _save_notification(self, scope: str, channel: str, content: str, status: str, meta: dict = None):
        """Saves notification attempt to DB."""
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                note = Notification(
                    scope=NotificationScope(scope),
                    channel=NotificationChannel(channel),
                    content=content,
                    status=NotificationStatus(status),
                    meta=meta
                )
                db.add(note)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save notification history: {e}")

    async def _check_twitter_limit(self) -> bool:
        """
        Checks if we reached the 21 daily post limit for Twitter.
        Also returns False if it is Weekend.
        """
        now = datetime.now()
        
        # 1. Weekend Check (Sat=5, Sun=6)
        if now.weekday() >= 5:
            logger.info("Twitter limit: Skipped due to Weekend.")
            return False

        # 2. Daily Count Check
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                stmt = select(func.count()).where(
                    Notification.channel == NotificationChannel.TWITTER,
                    Notification.status == NotificationStatus.SENT,
                    func.date(Notification.created_at) == now.date()
                )
                count = (await db.execute(stmt)).scalar() or 0
                
                if count >= 21:
                    logger.warning(f"Twitter limit reached ({count}/21). Skipping.")
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to check Twitter limit: {e}")
            return True # Fail open to not block critical alerts? Or Fail close? let's Fail open for now.

    async def send(self, message: str, scope: str = 'PRIVATE', channels: Optional[List[str]] = None, **kwargs):
        target_notifiers = self.channels.get(scope, [])
        if not target_notifiers:
            return

        for notifier in target_notifiers:
            # Determine Channel Enum based on class name
            channel_enum = "TELEGRAM" 
            if isinstance(notifier, TwitterNotifier):
                channel_enum = "TWITTER"
            
            # Filter by specific channels if requested
            if channels:
                # Simple check: is 'TWITTER' in ['TELEGRAM']?
                if channel_enum not in channels:
                    continue

            # --- PRE-SEND CHECKS ---
            if channel_enum == "TWITTER":
                can_post = await self._check_twitter_limit()
                if not can_post:
                    await self._save_notification(scope, channel_enum, message, "SKIPPED", {"reason": "Rate Limit/Weekend"})
                    continue

            # --- SEND ---
            try:
                await notifier.send(message, **kwargs)
                await self._save_notification(scope, channel_enum, message, "SENT")
            except Exception as e:
                logger.error(f"Failed to send to {notifier.name}: {e}")
                await self._save_notification(scope, channel_enum, message, "FAILED", {"error": str(e)})

    # Helper for legacy compatibility (for now)
    def get_private_telegram_instance(self) -> Optional[TelegramNotifier]:
        for n in self.channels.get('PRIVATE', []):
            if isinstance(n, TelegramNotifier):
                return n
        return None

notification_manager = NotificationManager()
