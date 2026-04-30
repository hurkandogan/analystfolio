import logging
import json
import os
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from app.core.logger import log_manager
from app.infrastructure.notifiers.manager import notification_manager
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.system import SystemLog

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_running = True
        self.config = self._load_config()
        # Simple logger configuration (can be linked to core/logger.py later)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(name)

    def _load_config(self) -> dict:
        """Loads bot-specific strategy configuration from JSON file."""
        config_path = Path(__file__).parent / "config" / f"{self.name}.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading config for {self.name}: {e}")
        return {}

    async def log(self, message: str, level: str = "INFO"):
        # Printing to console for now, can be directed to DB or Telegram later
        if level == "ERROR":
            self.logger.error(message)
        else:
            self.logger.info(message)
            
        # Broadcast to Frontend via WebSocket
        log_data = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "module": self.name,
            "type": level,
            "msg": message
        }
        await log_manager.broadcast(log_data)

        # Persist to Database
        try:
            async with AsyncSessionLocal() as db:
                db_log = SystemLog(
                    level=level,
                    module=self.name,
                    message=message
                )
                db.add(db_log)
                await db.commit()
        except Exception as e:
            # We don't want log persistence errors to break the strategy
            print(f"FAILED TO PERSIST LOG: {e}")

    async def notify(self, message: str):
        """Sends a private alert to the bot owner."""
        await notification_manager.send(f"🤖 *{self.name}* (Private)\n{message}", scope='PRIVATE')

    async def broadcast_public(self, message: str, channels=None):
        """Broadcasts a message to public channels (Telegram Channel, Twitter)."""
        await notification_manager.send(f"📢 *{self.name}* (Public)\n{message}", scope='PUBLIC', channels=channels)

    @abstractmethod
    async def execute(self):
        pass