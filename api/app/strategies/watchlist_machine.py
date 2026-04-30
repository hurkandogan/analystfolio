import asyncio
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy import select, delete

from app.strategies.base import BaseStrategy
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.trading import PremiumWatchlist, TradeSignal
from app.infrastructure.models.common import Instrument, MarketDataCache, FundamentalCache
from app.infrastructure.ibkr_client import ibkr_client
from app.data.fetcher import market_fetcher
from app.logic.watchlist_evaluator import evaluate_watchlist_state
from ib_async import Stock
from sqlalchemy import desc

logger = logging.getLogger(__name__)

class WatchlistStateMachine(BaseStrategy):
    """
    Premium Watchlist Stock Analysis Algorithm:
    Monitors Pre-Market changes, RSI (oversold) levels, and IV (Premium Volatility)
    levels for selected (Auto or Manual) quality companies hourly.
    Publishes Put Sell Opportunities where appropriate.
    """
    def __init__(self):
        super().__init__("WatchlistStateMachine")

    async def execute(self):
        cfg = self.config
        iv_ultra = cfg.get("iv_ultra", 80.0)
        iv_high = cfg.get("iv_high", 70.0)
        iv_mid = cfg.get("iv_mid", 40.0)
        rsi_limit = cfg.get("rsi_oversold", 32.0)
        vol_mult = cfg.get("volume_spike_multiplier", 1.5)
        dev_alert = cfg.get("price_deviation_alert", 0.03)
        min_ps_score = cfg.get("put_sell_min_score", 75)
        labels = cfg.get("labels", {})

        await self.log("🚀 Premium Watchlist State Machine Scan Started...", "INFO")
        
        async with AsyncSessionLocal() as db:
            # 1. Eviction Policy: Removed. FundamentalAnalystBot handles deactivation.

            # Fetch Current Watchlist
            stmt = select(PremiumWatchlist).where(PremiumWatchlist.is_active == True)
            watchlist_items = (await db.execute(stmt)).scalars().all()
            
            if not watchlist_items:
                await self.log("📭 Watchlist is empty. Add some tickers to scan.", "INFO")
                return

            collected_data = []

            for index, item in enumerate(watchlist_items):
                if not self.is_running: break
                
                # Fetch Instrument info
                instr_stmt = select(Instrument).where(Instrument.symbol == item.ticker)
                instr = (await db.execute(instr_stmt)).scalar_one_or_none()
                if not instr:
                    await self.log(f"⚠️ {item.ticker} is not an active instrument in DB.", "WARNING")
                    continue

                # Fetch Technical History (RSI & Vol Avg) first for fallback
                bars_stmt = select(MarketDataCache).where(
                    MarketDataCache.instrument_id == instr.id,
                    MarketDataCache.timeframe == '1h'
                ).order_by(MarketDataCache.timestamp.desc()).limit(200)

                bars_result = (await db.execute(bars_stmt)).scalars().all()
                bars = list(reversed(bars_result))

                snapshot = await market_fetcher.get_market_snapshot(instr)
                if snapshot:
                    current_price, current_vol = snapshot
                    if pd.isna(current_vol): current_vol = 0.0
                elif bars:
                    current_price, current_vol = bars[-1].close, 0.0
                    if item.source == 'Manual':
                        await self.log(f"⚠️ IBKR Offline: using DB close ({current_price}) for {item.ticker}", "WARNING")
                else:
                    await self.log(f"📉 No live data or history for {item.ticker}.", "WARNING")
                    continue

                # Fetch Option Implied Volatility
                iv_rank = await market_fetcher.get_implied_volatility(instr)
                current_iv = iv_rank if iv_rank else 0.0
                
                # Fetch Latest Valid Fundamental Score dynamically
                fund_stmt = select(FundamentalCache.fundamental_score).where(
                    FundamentalCache.instrument_id == instr.id
                ).order_by(desc(FundamentalCache.date)).limit(1)
                latest_fund_score = (await db.execute(fund_stmt)).scalar()

                # EVALUATE STATE
                eval_res = evaluate_watchlist_state(item, instr, current_price, current_vol, current_iv, bars, latest_fund_score, cfg)
                
                new_state = eval_res["new_state"]
                has_alert = eval_res["has_alert"]
                is_high_iv = eval_res["is_high_iv"]
                is_oversold = eval_res["is_oversold"]
                is_high_volume = eval_res["is_high_volume"]
                latest_rsi = eval_res["latest_rsi"]
                avg_vol = eval_res["avg_vol"]
                score = eval_res["score"]
                state_changes = eval_res["state_changes"]
                vol_status = eval_res["vol_status"]
                strategy = eval_res["strategy"]
                state_emoji = eval_res["state_emoji"]

                if new_state == "Action":
                    new_signal = TradeSignal(
                        instrument_id=instr.id,
                        bot_name=self.name,
                        signal_price=current_price,
                        reason=f"Fundamental Score > {min_ps_score}, Solid Premium (IV>{iv_high:.0f}), and Tech Oversold (RSI<{rsi_limit:.0f}).",
                        score=100.0,
                        status="NEW",
                        signal_data={
                            "strategy": "PUT SELL OPPORTUNITY",
                            "metrics": {
                                "rsi": latest_rsi,
                                "iv": current_iv,
                                "fundamental_score": score
                            }
                        }
                    )
                    db.add(new_signal)
                    item.last_signal_at = datetime.now(timezone.utc)
                    item.current_state = "Action"
                    
                    msg = (
                        f"🔥 *PREMIUM WATCHLIST ACTION*\\n"
                        f"━━━━━━━━━━━━━━━━━━━━\\n"
                        f"🎫 *Symbol:* `{item.ticker}`\\n"
                        f"🏭 *Score:* `{score:.1f}/100`\\n"
                        f"📈 *Strategy:* `Put Sell Opportunity`\\n"
                        f"💰 *Price:* `${current_price:.2f}`\\n"
                        f"📉 *RSI:* `{latest_rsi:.1f}` (Oversold)\\n"
                        f"🔥 *Implied Vol:* `{current_iv:.1f}%`\\n"
                        f"━━━━━━━━━━━━━━━━━━━━\\n"
                        f"💡 *Action:* High Premium available on heavily oversold quality asset."
                    )
                    await self.notify(msg)
                
                # In real TWS pre-market, snapshot usually holds the live delayed tick.
                elif bars:
                    last_close = bars[-1].close
                    deviation = abs((current_price - last_close) / last_close)
                    if deviation > dev_alert:  # dynamic threshold
                        item.current_state = "Alert"
                        state_emoji = "⚠️"
                        if item.source == 'Manual':
                            await self.notify(f"⚠️ `{item.ticker}` moving dynamically by {deviation*100:.1f}%. State: Alert.")
                            
                # Detailed Debug Log
                await self.log(
                    f"🔍 {item.ticker} Evaluated | "
                    f"Score: {score} | "
                    f"RSI: {latest_rsi:.1f} | "
                    f"IV: {current_iv:.1f}% | "
                    f"Vol: {current_vol}/{avg_vol:.0f} | "
                    f"Status: {item.current_state}",
                    "INFO"
                )
                
                # Add to summary table multi-line mobile format
                iv_str = f"{current_iv:.1f}%" if current_iv else "N/A"
                if pd.isna(current_vol): current_vol = 0.0

                # Info logic based on IV
                if current_iv >= iv_high:
                    info_str = "🌋 SPC"
                elif current_iv >= iv_mid:
                    info_str = "➖ N"
                else:
                    info_str = "🌊 BC"

                # New compact format: Symbol|price$|puan|RSI:xx|IV:xx%|Info
                msg_block = (
                    f"• `{item.ticker}|{current_price:.1f}$|{score:.0f}|RSI:{latest_rsi:.0f}|IV:{current_iv:.0f}%|{info_str}`"
                )
                
                collected_data.append({
                    "score": score,
                    "iv": current_iv,
                    "msg_block": msg_block
                })

                if not has_alert and item.current_state != "Alert":
                    item.current_state = "Watching"

                await asyncio.sleep(0.1) # Throttle loop
                
            await db.commit()

        # Sort the collected watchlist data by Score (Desc) and then IV% (Desc)
        collected_data.sort(key=lambda x: (x["score"], x["iv"]), reverse=True)
        summary_rows = [item["msg_block"] for item in collected_data]

        # Build summary message in chunks to prevent Telegram's 4096 char limit crashes
        chunk_size = 20 # 20 stocks per message chunk is safe
        for i in range(0, len(summary_rows), chunk_size):
            chunk = summary_rows[i:i + chunk_size]
            summary_text = "\n".join(chunk)
            page_info = f" (Part {i//chunk_size + 1})" if len(summary_rows) > chunk_size else ""
            
            final_msg = (
                f"🤖 *WatchlistStateMachine (v2.0)*{page_info}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{summary_text}\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            
            await self.notify(final_msg)
            await asyncio.sleep(1) # Throttling for Telegram API rate limits

        await self.log("✅ Watchlist Machine Scan Completed.", "SUCCESS")
