import logging
import asyncio
from app.infrastructure.notifiers.manager import notification_manager

logger = logging.getLogger("TelegramClient")

class TelegramClient:
    """
    Legacy wrapper for Telegram functionality.
    Delegates to NotificationManager for sending messages.
    """
    def __init__(self):
        self.manager = notification_manager

    @property
    def chat_id(self) -> str:
        instance = self.manager.get_private_telegram_instance()
        return instance.chat_id if instance else ""

    async def send_alert(self, message: str, parse_mode: str = "Markdown"):
        """
        Sends an alert to the PRIVATE scope (AnalystFolio Bot -> You).
        """
        await self.manager.send(message, scope='PRIVATE', parse_mode=parse_mode)

    async def get_updates(self):
        """
        Delegates polling to the private Telegram instance.
        """
        private_instance = self.manager.get_private_telegram_instance()
        if private_instance:
            return await private_instance.get_updates()
        return []

telegram_client = TelegramClient()
