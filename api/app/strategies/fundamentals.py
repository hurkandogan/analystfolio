import asyncio
from sqlalchemy import select, func, desc
from datetime import datetime, date, timezone
from typing import List, Tuple

from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import Instrument, FundamentalCache, MarketDataCache
from app.strategies.base import BaseStrategy
from app.logic.fundamentals_scorer import evaluate_fundamentals
from app.services.signal_manager import SignalManager
from app.services.watchlist_manager import WatchlistManager
from app.services.fundamental_service import FundamentalService
from app.core.schemas import ScoringResult

class FundamentalAnalystBot(BaseStrategy):
    def __init__(self):
        super().__init__("FundamentalAnalyst")
        self.signal_manager = SignalManager(self.name)
        self.watchlist_manager = WatchlistManager()
        self.fundamental_service = FundamentalService()

    async def execute(self):
        await self.log("🚀 Fundamental Analyst 2.0 (Deep Scan) Started...", "INFO")
        
        async with AsyncSessionLocal() as db:
            results = await self.fundamental_service.fetch_instruments_with_fundamentals(db)
            if not results:
                await self.log("❌ No instruments with fundamental data found in DB.", "ERROR")
                return

            await self.log(f"🔍 Analyzing {len(results)} instruments...", "INFO")
            
            skipped_mc = 0
            processed = 0
            for i, (instr, fdata) in enumerate(results):
                if not self.is_running: break
                
                try:
                    # 1. Hard Filter (Market Cap)
                    min_mc = self.config.get("min_market_cap", 5000000000)
                    if (fdata.market_cap or 0) < min_mc:
                        skipped_mc += 1
                        continue

                    await self._process_instrument(db, instr, fdata)
                    processed += 1
                    await db.commit()
                except Exception as e:
                    await self.log(f"❌ Error processing {instr.symbol}: {e}", "ERROR")
                
                await asyncio.sleep(0.05)

            await self.log(f"Scan complete. MC Filter: -{skipped_mc}, Processed: {processed}", "INFO")

        await self.log("✅ Analysis completed successfully.", "SUCCESS")

    async def _process_instrument(self, db, instr: Instrument, fdata: FundamentalCache):
        # 1. Fetch 1 Year of Hourly Bars
        bars = await self._fetch_bars(db, instr.id)
        
        # 2. Evaluate
        eval_res_dict = evaluate_fundamentals(instr, fdata, bars, None, self.config)
        eval_res = ScoringResult(**eval_res_dict)
        
        # 3. Watchlist Management (Threshold 7)
        await self._manage_watchlist(db, instr, eval_res)
        
        # 4. Signal Management (Threshold 7)
        final_status = await self._manage_signals(db, instr, fdata, bars, eval_res)
        
        # 5. Score Persistence
        fdata.fundamental_score = eval_res.score
        fdata.score_breakdown = eval_res.score_details

        # 6. Logging
        pe_val = fdata.pe_ratio if fdata.pe_ratio else 0.0
        await self.log(f"[{instr.symbol:<5}] Score: {eval_res.score:<2.0f} | Status: {final_status or 'SKIPPED'}", "INFO")

    async def _fetch_bars(self, db, instrument_id: int):
        stmt = select(MarketDataCache).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == '1h'
        ).order_by(MarketDataCache.timestamp.desc()).limit(2500)
        result = await db.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def _manage_watchlist(self, db, instr, eval_res: ScoringResult):
        wl_min_score = int(self.config.get("watchlist_min_score", 7))
        await self.watchlist_manager.process_instrument(db, instr, eval_res.score, wl_min_score)

    async def _manage_signals(self, db, instr, fdata, bars, eval_res: ScoringResult):
        min_score = int(self.config.get("min_score", 7))
        
        daily_signal = await self.signal_manager.get_daily_signal(db, instr.id)
        latest_signal = await self.signal_manager.get_latest_active_signal(db, instr.id)
        
        final_status = await self.signal_manager.determine_new_status(
            db, instr.id, eval_res.score, min_score, latest_signal is not None
        )

        if final_status and bars:
            display_count = await self.signal_manager.calculate_chain_count(db, instr.id, daily_signal is not None)
            msg = self._format_signal_message(instr, fdata, eval_res, display_count)

            if daily_signal:
                old_status = daily_signal.status
                daily_signal.score = eval_res.score
                daily_signal.reason = ", ".join(eval_res.reasons)
                daily_signal.status = final_status
                daily_signal.updated_at = datetime.now(timezone.utc)
                
                if final_status == 'CLOSED' and old_status != 'CLOSED':
                    await self.notify(f"⛔ *SIGNAL CLOSED: {instr.symbol}*")
                elif final_status == 'OPEN' and old_status == 'WEAK':
                    await self.notify(f"🔄 *SIGNAL RECOVERED: {instr.symbol}*\n" + msg)
                elif eval_res.score >= min_score and old_status in ['OPEN', 'NEW']:
                    await self.notify(msg)
            else:
                db.add(self.signal_manager.build_signal(
                    instr.id, eval_res.current_price, eval_res.score,
                    eval_res.reasons, final_status, {"metrics": eval_res.model_dump()}
                ))
                if final_status in ['NEW', 'OPEN']:
                    await self.notify(msg)

        await self.watchlist_manager.deactivate_if_tracking_stopped(db, instr.symbol, final_status)
        return final_status

    def _format_signal_message(self, instr, fdata, eval_res, display_count):
        reasons_fmt = "\n".join([f"• {r}" for r in eval_res.reasons])
        mom = eval_res.momentum_data
        def f_n(v): return f"{v:.1f}" if v is not None else "N/A"
        def f_p(v): return f"{v:+.1%}" if v is not None else "N/A"

        pe_str     = f"{fdata.pe_ratio:.1f}" if fdata.pe_ratio else "N/A"
        peg_str    = f"{fdata.peg_ratio:.1f}" if fdata.peg_ratio else "N/A"
        target_str = f"${fdata.target_price:.2f}" if fdata.target_price else "N/A"
        change_30d = f_p(mom.change_30d)

        upside_str  = f"{eval_res.analyst_upside:+.1%}" if eval_res.analyst_upside is not None else "N/A"
        rev_str     = f"{eval_res.revenue_growth:+.1%}" if eval_res.revenue_growth else "N/A"

        prefix = "🎯 *FUNDAMENTAL OPPORTUNITY"
        if eval_res.is_unusual_activity:
            prefix = "🚨 *UNUSUAL ACTIVITY DETECTED"

        return (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{prefix}*\n"
            f"🎫 *Symbol:* `{instr.symbol}`\n"
            f"📊 *Score:* `{eval_res.score:.0f}/10`\n"
            f"💰 *Price:* `${eval_res.current_price:.2f}`\n"
            f"📅 *30D Change:* `{change_30d}`\n"
            f"🔢 *Signal Day:* `{display_count}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 *Rev Growth:* `{rev_str}` | *Analyst Upside:* `{upside_str}`\n"
            f"💵 *P/E:* `{pe_str}` | *PEG:* `{peg_str}`\n"
            f"🎯 *Analyst Target:* `{target_str}`\n"
            f"🌊 *Momentum:* RSI: `{f_n(mom.rsi)}` | rVol: `{f_n(mom.rvol)}x`\n"
            f"🧱 *Levels:* S: `{eval_res.supports_str}` | R: `{eval_res.resistances_str}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Reasons:*\n{reasons_fmt}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
