import aiohttp
import logging
from typing import Optional
from app.infrastructure.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """
    Concrete implementation for Telegram notifications.
    Can be instantiated for different bots/channels (Public/Private).
    """
    def __init__(self, bot_token: str, chat_id: str, name: str = "Telegram"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.name = name
        self.last_update_id = 0

    async def send(self, message: str, **kwargs) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning(f"[{self.name}] Token or Chat ID missing. Skipping.")
            return False

        parse_mode = kwargs.get("parse_mode", "Markdown")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"[{self.name}] Failed: {await response.text()}")
                        return False
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return False

    async def check_health(self) -> bool:
        if not self.bot_token:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return response.status == 200
        except:
            return False

    async def get_updates(self):
        """
        Polls for updates. Only relevant if this instance is acting as a bot receiver.
        """
        if not self.bot_token:
            return []

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 2, 
            "allowed_updates": ["message"]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        updates = data.get("result", [])
                        if updates:
                            self.last_update_id = updates[-1]["update_id"]
                        return updates
        except Exception as e:
            logger.error(f"[{self.name}] Polling Error: {e}")
            return []
