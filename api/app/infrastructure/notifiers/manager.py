import logging
from typing import List, Dict, Optional
from app.infrastructure.notifiers.base import BaseNotifier
from app.infrastructure.notifiers.telegram import TelegramNotifier
from app.config import settings
from app.infrastructure.database import async_sessionmaker, engine
from app.infrastructure.models.notification import Notification, NotificationChannel, NotificationScope, NotificationStatus

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Central manager for routing notifications to different channels based on scope.
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

    async def send(self, message: str, scope: str = 'PRIVATE', channels: Optional[List[str]] = None, **kwargs):
        target_notifiers = self.channels.get(scope, [])
        if not target_notifiers:
            return

        for notifier in target_notifiers:
            if channels and "TELEGRAM" not in channels:
                continue

            try:
                await notifier.send(message, **kwargs)
                await self._save_notification(scope, "TELEGRAM", message, "SENT")
            except Exception as e:
                logger.error(f"Failed to send to {notifier.name}: {e}")
                await self._save_notification(scope, "TELEGRAM", message, "FAILED", {"error": str(e)})

    # Helper for legacy compatibility (for now)
    def get_private_telegram_instance(self) -> Optional[TelegramNotifier]:
        for n in self.channels.get('PRIVATE', []):
            if isinstance(n, TelegramNotifier):
                return n
        return None

notification_manager = NotificationManager()
