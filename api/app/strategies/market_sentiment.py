import asyncio
from datetime import datetime
from sqlalchemy import select, desc

from app.strategies.base import BaseStrategy
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import MarketSentiment
from app.data.sentiment_fetcher import sentiment_fetcher
from app.core.formatters import format_currency_eu, format_change_eu

class MarketSentimentBot(BaseStrategy):
    def __init__(self):
        super().__init__("MarketSentiment")
        
    async def execute(self):
        if ibkr_client.is_connected():
            ibkr_client.ib.reqMarketDataType(3)

        await self.log("📡 Market Sentiment Scan Starting...", "INFO")
        
        market_data, market_changes = await sentiment_fetcher.fetch_all()
        if not market_data:
            await self.log("No data received, analysis cancelled.", "ERROR")
            return

        # Normalize Data
        us10y_raw = market_data.get("US10Y")
        us10y = (us10y_raw / 10.0) if us10y_raw else None 
        if us10y: market_data["US10Y"] = us10y

        # Save to Database
        async with AsyncSessionLocal() as db:
            sentiment = MarketSentiment(
                vix=market_data.get("VIX"),
                us10y=us10y,
                dxy=market_data.get("DXY"),
                spx=market_data.get("SPX"),
                ndx=market_data.get("NDX"),
                dax=market_data.get("DAX"),
                btc_usd=market_data.get("BTC"),
                xau_usd=market_data.get("GOLD"),
                details={"vxn": market_data.get("VXN")}
            )
            db.add(sentiment)
            await db.commit()
            await self.log(f"💾 Sentiment Saved", "SUCCESS")

            # Notification
            msg = self._format_pulse_message(market_data, market_changes)
            await self.notify(msg)
            await self.broadcast_public(msg)

    def _format_pulse_message(self, market_data, market_changes):
        def fmt(key, val, is_pct=False):
            if val is None: return "N/A"
            chg = market_changes.get(key, 0.0)
            icon = "🟢" if chg > 0 else "🔴" if chg < 0 else "⚪"
            suffix = "%" if is_pct else ""
            
            val_str = format_currency_eu(val)
            chg_str = format_change_eu(chg)
            return f"`{val_str}{suffix}` ({icon} `{chg_str}%`)"

        return (
            f"🌍 *MARKET PULSE UPDATE*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🇺🇸 *SPX:* {fmt('SPX', market_data.get('SPX'))}\n"
            f"🚀 *NDX:* {fmt('NDX', market_data.get('NDX'))}\n"
            f"🇩🇪 *DAX:* {fmt('DAX', market_data.get('DAX'))}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 *VIX:* {fmt('VIX', market_data.get('VIX'))}\n"
            f"📉 *VXN:* {fmt('VXN', market_data.get('VXN'))}\n"
            f"💵 *DXY:* {fmt('DXY', market_data.get('DXY'))}\n"
            f"🇺🇸 *US10Y:* {fmt('US10Y', market_data.get('US10Y'), is_pct=True)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 *Gold:* {fmt('GOLD', market_data.get('GOLD'))}\n"
            f"🪙 *BTC:* {fmt('BTC', market_data.get('BTC'))}"
        )