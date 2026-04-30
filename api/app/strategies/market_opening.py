import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.infrastructure.database import async_sessionmaker, engine
from app.infrastructure.models.calendar import ExchangeCalendar
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.notifiers.manager import notification_manager
from ib_async import Contract

logger = logging.getLogger(__name__)

from app.strategies.base import BaseStrategy

class MarketOpeningBot(BaseStrategy):
    def __init__(self):
        super().__init__(name="MarketOpeningBot")
        self.indices = self.config.get("indices", {
            "SPX": {"symbol": "SPX", "exchange": "CBOE", "secType": "IND", "currency": "USD", "name": "S&P 500"},
            "NDX": {"symbol": "NDX", "exchange": "NASDAQ", "secType": "IND", "currency": "USD", "name": "Nasdaq 100"}
        })

    async def _is_market_open(self, exchange: str = "NYSE") -> bool:
        """
        Checks if the market is open today based on ExchangeCalendar DB.
        If no entry exists, assumes OPEN (Mon-Fri).
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        
        # 1. Weekend Check
        if now.weekday() >= 5: # Sat, Sun
            return False

        # 2. DB Check
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            stmt = select(ExchangeCalendar).where(
                ExchangeCalendar.exchange == exchange,
                ExchangeCalendar.date == today
            )
            result = (await db.execute(stmt)).scalar_one_or_none()
            
            if result:
                return result.is_open
            
        # Default: Open if weekday
        return True

    async def execute(self):
        logger.info("🔔 MarketOpeningBot: Checking market status...")
        
        # 1. Check if NYSE/NASDAQ is open
        if not await self._is_market_open("NYSE"):
            logger.info("MarketOpeningBot: Market is CLOSED today. Skipping.")
            return

        # 2. Fetch Data
        if not ibkr_client.ib.isConnected():
            logger.error("MarketOpeningBot: IBKR not connected.")
            await notification_manager.send("⚠️ MarketOpeningBot: IBKR Disconnected!", scope='PRIVATE')
            return

        report_lines = ["🇺🇸 *US Market Open Report*"]
        
        for key, info in self.indices.items():
            try:
                contract = Contract()
                contract.symbol = info["symbol"]
                contract.secType = info["secType"]
                contract.exchange = info["exchange"]
                contract.currency = info["currency"]
                
                # Qualify contract
                qualified_contracts = await ibkr_client.ib.qualifyContractsAsync(contract)
                if not qualified_contracts:
                    logger.error(f"Could not qualify {key}")
                    continue
                
                c = qualified_contracts[0]
                
                # Request Market Data Snapshot
                # We need "Close" (yesterday) and "Open" (today) or "Last" (current)
                # ReqHistoricalData might be better to get Yesterday's Close and Today's Open specifically.
                
                # Fetch 2 days of Daily bars
                bars = await ibkr_client.ib.reqHistoricalDataAsync(
                    c,
                    endDateTime='',
                    durationStr='2 D',
                    barSizeSetting='1 day',
                    whatToShow='TRADES',
                    useRTH=True,
                    formatDate=1
                )
                
                if len(bars) < 2:
                    logger.warning(f"Not enough data for {key}")
                    continue
                    
                prev_close = bars[-2].close
                # If market just opened, the last bar is today's bar.
                # It might be forming. creating a "snapshot" logic.
                current_open = bars[-1].open # Today's open
                current_price = bars[-1].close # Currently forming bar's close is the "last" price
                
                # Calculate Gap % (Open vs Prev Close)
                gap_pct = ((current_open - prev_close) / prev_close) * 100
                
                # Calculate Change % (Current vs Prev Close)
                change_pct = ((current_price - prev_close) / prev_close) * 100
                
                icon = "🟢" if change_pct > 0 else "🔴"
                if abs(change_pct) < 0.1: icon = "⚪"
                
                line = f"{icon} *{info['name']}* ({key})\n"
                line += f"   Op: {current_open:.2f} (Gap: {gap_pct:+.2f}%)\n"
                line += f"   Cur: {current_price:.2f} ({change_pct:+.2f}%)"
                report_lines.append(line)

            except Exception as e:
                logger.error(f"Error fetching {key}: {e}")
        
        if len(report_lines) > 1:
            message = "\n\n".join(report_lines)
            await notification_manager.send(message, scope='PUBLIC')
        else:
            logger.info("MarketOpeningBot: No data to report.")

