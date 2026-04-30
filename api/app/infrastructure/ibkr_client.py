import asyncio
import logging
import random
from ib_async import IB
from app.config import settings
from app.infrastructure.base_exchange import BaseExchange
from app.infrastructure.telegram_client import telegram_client

logger = logging.getLogger(__name__)

class IBKRClient(BaseExchange):
    def __init__(self):
        self.ib = IB()
        self.host = settings.IBKR_HOST      # 127.0.0.1
        self.port = settings.IBKR_PORT      # 7497
        self.client_id = random.randint(10, 9999)
        self._connected_event = asyncio.Event() 
        self._is_connecting = False 
        self._watchdog_task: asyncio.Task | None = None

        # Event to be triggered on disconnection
        self.ib.disconnectedEvent += self._on_disconnected

    def _on_disconnected(self, *args):
        """Automatically tries to reconnect when connection is lost."""
        logger.warning("🔌 IBKR Connection Lost! Starting reconnection...")
        asyncio.create_task(telegram_client.send_alert("🔌 *IBKR Connection Lost!* Starting reconnection..."))
        self._connected_event.clear()
        
        # Stop watchdog to prevent overlap
        if self._watchdog_task is not None:
            self._watchdog_task.cancel()
            self._watchdog_task = None

        # Trigger asynchronous connect within the event loop
        asyncio.create_task(self.connect())

    async def connect(self):
        """
        Connection function to run in the background.
        Tries to reconnect with Exponential Backoff.
        """
        if self.ib.isConnected() or self._is_connecting:
            logger.info("ℹ️ IBKR is already connected.")
            return

        logger.info(f"🔄 IBKR Connection Loop Started ({self.host}:{self.port})")
        self._is_connecting = True
        
        attempt = 0
        max_delay = 60
        
        while True:
            try:
                # connectAsync does not block Uvicorn loop even when awaited
                await self.ib.connectAsync(
                    self.host, 
                    self.port, 
                    clientId=self.client_id, 
                    timeout=5
                )
                
                logger.info("✅ IBKR CONNECTED SUCCESSFULLY!")
                # Use Delayed Market Data (3) by default
                self.ib.reqMarketDataType(3)
                self.ib.reqAccountUpdatesAsync(True)
                await telegram_client.send_alert(f"✅ *IBKR Connected Successfully!* (ID: {self.client_id})")
                self._connected_event.set()
                self._is_connecting = False
                attempt = 0 # Reset attempt on success
                
                # Start Watchdog
                if self._watchdog_task is None or self._watchdog_task.done():
                    self._watchdog_task = asyncio.create_task(self._watchdog_loop())

                break # Exit loop
                
            except Exception as e:
                import traceback
                attempt += 1
                delay = min(5 * (2 ** (attempt - 1)), max_delay)
                logger.warning(f"⚠️ Connection Failed (Attempt {attempt}): {e}\n{traceback.format_exc()}")
                
                self.disconnect() # Clean up faulty state
                await asyncio.sleep(delay)

    async def _watchdog_loop(self):
        """Checks connection every 60 seconds."""
        logger.info("🐕 IBKR Watchdog Started")
        while True:
            try:
                await asyncio.sleep(60)
                if not self.ib.isConnected():
                    logger.warning("🐕 Watchdog: Disconnected detected!")
                    continue # _on_disconnected will handle it
                
                # Test if alive with a light request
                try:
                    await asyncio.wait_for(self.ib.reqCurrentTimeAsync(), timeout=5)
                    # logger.debug("🐕 Watchdog: Heartbeat OK")
                except Exception as e:
                    logger.error(f"🐕 Watchdog: Heartbeat FAILED! Reconnecting... Error: {e}")
                    self.disconnect() # This triggers _on_disconnected and reconnects
                    break

            except asyncio.CancelledError:
                logger.info("🐕 IBKR Watchdog Stopped")
                break
            except Exception as e:
                logger.error(f"🐕 Watchdog Error: {e}")
                await asyncio.sleep(10)

    def disconnect(self):
        if self._watchdog_task is not None:
            self._watchdog_task.cancel()
            
        if self.ib.isConnected():
            self.ib.disconnect()
            logger.info("🔌 IBKR Connection Closed.")

    def is_connected(self) -> bool:
        return self.ib.isConnected()
    
    @property
    def client(self):
        return self.ib

# Singleton Instance
ibkr_client = IBKRClient()