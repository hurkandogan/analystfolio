import asyncio
from sqlalchemy import select, func, desc
from datetime import datetime, date, timezone
from typing import List, Dict

from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import Instrument, FundamentalCache, MarketDataCache
from app.infrastructure.models.trading import TradeSignal
from app.strategies.base import BaseStrategy
from app.logic.small_cap_scorer import evaluate_small_cap
from app.services.signal_manager import SignalManager
from app.services.fundamental_service import FundamentalService

class SmallCapScoutBot(BaseStrategy):
    def __init__(self):
        super().__init__("SmallCapScout")
        self.signal_manager = SignalManager(self.name)
        self.fundamental_service = FundamentalService()

    async def execute(self):
        cfg = self.config
        max_mc = int(cfg.get("max_market_cap", 5000000000))
        min_mc = int(cfg.get("min_market_cap", 100000000))
        min_avg_vol = cfg.get("min_avg_volume", 200000)
        
        # Extended blacklist to exclude Bio/Pharma
        blacklist = ["Biotechnology", "Pharmaceuticals", "Drug Manufacturers", "Biotechnology & Medical Research"]

        await self.log("🚀 Small Cap Scout 2.0 (Deep Scan) Started...", "INFO")

        async with AsyncSessionLocal() as db:
            all_results = await self.fundamental_service.fetch_instruments_with_fundamentals(db)
            if not all_results:
                await self.log("❌ No instruments with fundamental data found in DB.", "ERROR")
                return

            await self.log(f"🔍 Analyzing {len(all_results)} instruments...", "INFO")
            sector_avg_ps = self._calculate_sector_averages(all_results)
            
            hits = []
            skipped_mc = 0
            skipped_ind = 0
            skipped_roic = 0
            skipped_sec = 0

            for instr, fdata in all_results:
                if not self.is_running: break
                
                # 1. Hard Filters (Market Cap, Sector, ROIC)
                mc = fdata.market_cap or 0
                ind = instr.industry or ""
                sec = instr.sector or ""
                
                # Industry Filter
                if any(b.lower() in ind.lower() or b.lower() in sec.lower() for b in blacklist):
                    skipped_ind += 1
                    continue
                
                # ROIC Filter (No negative ROIC)
                if (fdata.roic or 0) < 0:
                    skipped_roic += 1
                    continue

                if mc < min_mc or mc > max_mc:
                    skipped_mc += 1
                    continue
                
                # Fetch Bars
                bars = await self._fetch_bars(db, instr.id)
                if not bars:
                    skipped_sec += 1
                    continue

                # Evaluate (10-point scale)
                eval_res = evaluate_small_cap(instr, fdata, bars, sector_avg_ps, cfg)
                
                # Secondary Filters
                if eval_res["avg_vol_3m"] < min_avg_vol or (fdata.operating_cash_flow or 0) <= 0:
                    skipped_sec += 1
                    continue

                hits.append({"instr": instr, "fdata": fdata, "eval": eval_res})
                await asyncio.sleep(0.01)

            await self.log(f"Scan complete. Stats: MC: -{skipped_mc}, IND: -{skipped_ind}, ROIC: -{skipped_roic}, SEC: -{skipped_sec}. Hits: {len(hits)}", "INFO")

            # Process Hits
            hits.sort(key=lambda x: x["eval"]["score"], reverse=True)
            for hit in hits:
                if not self.is_running: break
                await self._process_hit(db, hit["instr"], hit["fdata"], hit["eval"])
                await db.commit()
                await asyncio.sleep(0.05)

        await self.log("✅ Small Cap Scout Analysis completed.", "SUCCESS")

    def _calculate_sector_averages(self, results):
        sector_ps_data = {}
        for instr, fdata in results:
            if fdata.price_to_sales and instr.sector:
                if instr.sector not in sector_ps_data: sector_ps_data[instr.sector] = []
                sector_ps_data[instr.sector].append(fdata.price_to_sales)
        return {s: sum(v)/len(v) for s, v in sector_ps_data.items() if v}

    async def _fetch_bars(self, db, instrument_id):
        stmt = select(MarketDataCache).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == '1h'
        ).order_by(MarketDataCache.timestamp.desc()).limit(2000)
        result = await db.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def _process_hit(self, db, instr, fdata, eval_res):
        watch_threshold = int(self.config.get("min_score", 6)) # Default 6/10
        
        daily_signal = await self.signal_manager.get_daily_signal(db, instr.id)
        latest_signal = await self.signal_manager.get_latest_active_signal(db, instr.id)
        
        final_status = await self.signal_manager.determine_new_status(
            db, instr.id, eval_res["score"], watch_threshold, latest_signal is not None
        )

        if final_status:
            msg = self._format_scout_message(instr, fdata, eval_res)
            
            if daily_signal:
                old_status = daily_signal.status
                daily_signal.score = eval_res["score"]
                daily_signal.reason = ", ".join(eval_res["reasons"])
                daily_signal.status = final_status
                daily_signal.updated_at = datetime.now(timezone.utc)
                
                if final_status == 'CLOSED' and old_status != 'CLOSED':
                    await self.notify(f"⛔ *SMALL CAP CLOSED: {instr.symbol}*")
                elif eval_res["score"] >= watch_threshold and old_status in ['WEAK', 'OPEN']:
                    await self.notify(msg)
            else:
                new_sig = TradeSignal(
                    instrument_id=instr.id,
                    bot_name=self.name,
                    signal_price=eval_res["current_price"],
                    reason=", ".join(eval_res["reasons"]),
                    score=eval_res["score"],
                    status=final_status,
                    signal_data={"metrics": eval_res}
                )
                db.add(new_sig)
                if eval_res["score"] >= watch_threshold:
                    await self.notify(msg)
        
        await self.log(f"[{instr.symbol:<5}] Score: {eval_res['score']:<2.0f}/10 | Status: {final_status or 'SKIPPED'}", "INFO")

    def _format_scout_message(self, instr, fdata, eval_res):
        diamond_threshold = int(self.config.get("diamond_threshold", 8))
        label = "💎 DIAMOND OPPORTUNITY" if eval_res["score"] >= diamond_threshold else "👀 SMALL CAP WATCH"
        
        # UNUSUAL ACTIVITY Banner
        if eval_res["rvol"] > 2.0:
            label = "🚨 UNUSUAL ACTIVITY DETECTED"

        reasons_fmt = "\n".join([f"• {r}" for r in eval_res["reasons"]])
        def f_pct(v): return f"{v:.1%}" if v is not None else "N/A"
        def f_val(v): return f"{v:.1f}" if v is not None else "N/A"
        
        return (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{label}: `{instr.symbol}`\n"
            f"📊 *Scout Score:* `{eval_res['score']:.0f}/10`\n"
            f"💰 *Price:* `${eval_res['current_price']:.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 *Growth:* `{f_pct(fdata.revenue_growth)}` | *ROIC:* `{f_pct(fdata.roic)}`\n"
            f"💵 *P/E:* `{f_val(fdata.pe_ratio)}` | *PEG:* `{f_val(fdata.peg_ratio)}`\n"
            f"🌊 *Avg Vol:* `{eval_res['avg_vol_3m']/1000:.0f}K` | `rVol: {eval_res['rvol']:.1f}x`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Reasons:*\n{reasons_fmt}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
