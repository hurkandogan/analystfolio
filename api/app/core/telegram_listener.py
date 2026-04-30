import asyncio
import json
import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
from sqlalchemy import select, desc

from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.scheduler import BotSchedule
from app.infrastructure.models.common import Instrument, FundamentalCache, MarketDataCache
from app.infrastructure.telegram_client import telegram_client
from app.data.fetcher import market_fetcher

# Import Logic Modules
from app.logic.fundamentals_scorer import evaluate_fundamentals
from app.logic.small_cap_scorer import evaluate_small_cap
from app.logic.watchlist_evaluator import evaluate_watchlist_state

def load_bot_config(bot_name: str) -> dict:
    """Helper to load bot configuration."""
    config_path = Path(__file__).parent.parent / "strategies" / "config" / f"{bot_name}.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

async def get_instrument_and_data(symbol: str, db):
    """Common helper to fetch instrument, fundamental, and market data."""
    symbol = symbol.upper()
    instr_stmt = select(Instrument).where(Instrument.symbol == symbol)
    instr = (await db.execute(instr_stmt)).scalar_one_or_none()
    
    if not instr:
        return None, None, None
    
    fund_stmt = select(FundamentalCache).where(FundamentalCache.instrument_id == instr.id).order_by(desc(FundamentalCache.date)).limit(1)
    fdata = (await db.execute(fund_stmt)).scalar_one_or_none()
    
    bars_stmt = select(MarketDataCache).where(
        MarketDataCache.instrument_id == instr.id,
        MarketDataCache.timeframe == '1h'
    ).order_by(MarketDataCache.timestamp.desc()).limit(2000)
    bars_result = await db.execute(bars_stmt)
    bars = list(reversed(bars_result.scalars().all()))
    
    return instr, fdata, bars

async def start_telegram_listener():
    """Background service listening for Telegram commands."""
    print("👂 Telegram Listener Started (Secure Mode)")
    while True:
        try:
            updates = await telegram_client.get_updates()
            for update in updates:
                message = update.get("message", {})
                text = message.get("text", "").strip()
                chat_id = str(message.get("chat", {}).get("id"))
                
                if chat_id != telegram_client.chat_id:
                    continue

                parts = text.split()
                if not parts:
                    continue
                
                cmd = parts[0].lower()
                symbol = parts[1].upper() if len(parts) > 1 else None

                async with AsyncSessionLocal() as db:
                    if cmd == "/analyse_fundamental":
                        if not symbol:
                            await telegram_client.send_alert("⚠️ Usage: `/analyse_fundamental SYMBOL`")
                            continue
                        
                        await telegram_client.send_alert(f"🔎 *Fundamental Analysis:* `{symbol}`...")
                        instr, fdata, bars = await get_instrument_and_data(symbol, db)
                        
                        if not instr or not fdata:
                            await telegram_client.send_alert(f"❌ No data found for `{symbol}`. Please ensure it's in the system.")
                            continue
                        
                        cfg = load_bot_config("FundamentalAnalyst")
                        # Mock WACC as missing for quick command (Bot usually fetches it live)
                        res = evaluate_fundamentals(instr, fdata, bars, None, cfg)
                        
                        msg = (
                            f"📑 *ANALYSIS REPORT: {symbol}*\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🏷️ *Name:* {instr.name or symbol}\n"
                            f"🏭 *Score:* `{res['score']:.1f}/100`\n"
                            f"💰 *Price:* `${res['current_price']:.2f}`\n"
                            f"📊 *{res['disp_roic_or_roe_label']}:* `{res['disp_roic_or_roe_val']}`\n"
                            f"📉 *RSI:* `{res['momentum_data']['rsi'] or 'N/A'}`\n"
                            f"🔥 *Rvol:* `{res['momentum_data']['rvol'] or 'N/A'}x`\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"💡 *Reasons:*\n• " + "\n• ".join(res['reasons'])
                        )
                        await telegram_client.send_alert(msg)

                    elif cmd == "/analyse_smallcap":
                        if not symbol:
                            await telegram_client.send_alert("⚠️ Usage: `/analyse_smallcap SYMBOL`")
                            continue
                        
                        await telegram_client.send_alert(f"🔎 *Small Cap Scout:* `{symbol}`...")
                        instr, fdata, bars = await get_instrument_and_data(symbol, db)
                        
                        if not instr or not fdata:
                            await telegram_client.send_alert(f"❌ No data found for `{symbol}`.")
                            continue
                        
                        mcap = fdata.market_cap or 0
                        if mcap > 2_000_000_000:
                            await telegram_client.send_alert(f"🚫 This company is not a small-cap stock. `{symbol}` market cap is `${mcap/1e9:.1f}B`, which is above the $2B limit.")
                            continue
                        
                        cfg = load_bot_config("SmallCapScout")
                        # We don't have sector_avg_ps here easily, passed empty dict
                        res = evaluate_small_cap(instr, fdata, bars, {}, cfg)
                        
                        msg = (
                            f"🚀 *SMALL CAP REPORT: {symbol}*\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"💎 *Score:* `{res['score']:.1f}`\n"
                            f"💵 *M.Cap:* `${mcap/1e6:.1f}M`\n"
                            f"📈 *Rvol:* `{res['rvol']:.1f}x`\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"💡 *Findings:*\n• " + "\n• ".join(res['reasons'])
                        )
                        await telegram_client.send_alert(msg)

                    elif cmd == "/analyse_option":
                        if not symbol:
                            await telegram_client.send_alert("⚠️ Usage: `/analyse_option SYMBOL`")
                            continue
                        
                        await telegram_client.send_alert(f"💎 *Option Check:* `{symbol}`...")
                        instr, fdata, bars = await get_instrument_and_data(symbol, db)
                        
                        if not instr:
                            await telegram_client.send_alert(f"❌ Instrument `{symbol}` not found.")
                            continue
                        
                        iv = await market_fetcher.get_implied_volatility(instr)
                        current_iv = iv if iv else 0.0
                        current_price = bars[-1].close if bars else 0.0
                        
                        cfg = load_bot_config("WatchlistStateMachine")
                        # Mock item
                        mock_item = SimpleNamespace(source='Manual', fundamental_score=fdata.fundamental_score if fdata else 0)
                        
                        res = evaluate_watchlist_state(mock_item, instr, current_price, 0.0, current_iv, bars, None, cfg)
                        
                        iv_str = f"{current_iv:.1f}%" if current_iv else "N/A"
                        msg = (
                            f"🔥 *OPTION ANALYSIS: {symbol}* {res['state_emoji']}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"💰 *Price:* `${current_price:.2f}`\n"
                            f"🔥 *IV:* `{iv_str}` ({res['vol_status']})\n"
                            f"📉 *RSI:* `{res['latest_rsi']:.1f}`\n"
                            f"📈 *Action:* `{res['new_state']}`\n"
                            f"🛡️ *Strategy:* {res['strategy']}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"💡 *Status:* " + (", ".join(res['state_changes']) if res['state_changes'] else "Watching closely.")
                        )
                        await telegram_client.send_alert(msg)

                    elif cmd == "/status":
                        lines = ["📊 *System Status Report*"]
                        try:
                            result = await db.execute(select(BotSchedule))
                            bots_list = result.scalars().all()
                            lines.append(f"\n🤖 *Bots ({len(bots_list)})*")
                            for b in bots_list:
                                icon = "🟢" if b.is_active else "🔴"
                                lines.append(f"{icon} `{b.bot_name}`")
                        except Exception as e:
                            lines.append(f"⚠️ DB Error: {e}")
                        
                        await telegram_client.send_alert("\n".join(lines))

            await asyncio.sleep(1)
        except Exception as e:
            print(f"Telegram Listener Error: {e}")
            await asyncio.sleep(5)