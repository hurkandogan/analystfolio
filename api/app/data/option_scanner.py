import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from ib_async import Option
from app.infrastructure.ibkr_client import ibkr_client
from app.data.contracts import ContractFactory

logger = logging.getLogger(__name__)


async def find_best_puts(instr, current_price: float, cfg: dict) -> List[dict]:
    """
    Finds the best cash-secured put sell candidates for a given instrument.

    Flow:
      1. Qualify the underlying to get conId
      2. reqSecDefOptParams → expiries + strikes
      3. Filter: DTE between 7 and dte_max, strikes in OTM band
      4. Qualify all candidate option contracts in one batch call
      5. reqTickersAsync for Greeks in one batch call
      6. Filter by delta range, compute annualised yield
      7. Return top max_put_suggestions sorted by yield DESC

    Args:
        instr:          Instrument ORM object (needs .symbol)
        current_price:  Latest market price of the underlying
        cfg:            Bot config dict — keys used:
                          dte_max (int, default 30)
                          delta_min (float, default 0.20)
                          delta_max (float, default 0.35)
                          otm_min_pct (float, default 0.05)   — min OTM distance
                          otm_max_pct (float, default 0.15)   — max OTM distance
                          max_put_suggestions (int, default 3)

    Returns:
        List of candidate dicts sorted by annual_yield_pct descending.
        Empty list on any failure or if no candidates pass filters.
    """
    if not ibkr_client.is_connected():
        logger.warning(f"{instr.symbol}: IBKR not connected, skipping option scan.")
        return []

    dte_max   = int(cfg.get("dte_max", 30))
    delta_min = float(cfg.get("delta_min", 0.20))
    delta_max = float(cfg.get("delta_max", 0.35))
    otm_min   = float(cfg.get("otm_min_pct", 0.05))
    otm_max   = float(cfg.get("otm_max_pct", 0.15))
    max_res   = int(cfg.get("max_put_suggestions", 3))

    ib    = ibkr_client.ib
    today = datetime.now(timezone.utc).date()

    try:
        # ── 1. Qualify underlying to get conId ─────────────────────────────
        stock = ContractFactory.stock(instr.symbol)
        qualified_stock = await asyncio.wait_for(
            ib.qualifyContractsAsync(stock), timeout=10
        )
        if not qualified_stock or not qualified_stock[0].conId:
            logger.warning(f"{instr.symbol}: Could not qualify underlying.")
            return []
        con_id = qualified_stock[0].conId

        # ── 2. Fetch option chain definition ───────────────────────────────
        chains = await asyncio.wait_for(
            ib.reqSecDefOptParamsAsync(instr.symbol, '', 'STK', con_id),
            timeout=10
        )
        if not chains:
            logger.warning(f"{instr.symbol}: No option chain returned.")
            return []

        # Prefer SMART if available; otherwise use first exchange
        chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
        opt_exchange = chain.exchange

        # ── 3. Filter expiries: 7 ≤ DTE ≤ dte_max ─────────────────────────
        # 7-day floor avoids expiry-week gamma risk
        valid_exps = []
        for exp_str in sorted(chain.expirations):
            exp_date = datetime.strptime(exp_str, '%Y%m%d').date()
            dte = (exp_date - today).days
            if 7 <= dte <= dte_max:
                valid_exps.append((exp_str, exp_date, dte))

        if not valid_exps:
            logger.info(f"{instr.symbol}: No expiries within 7–{dte_max} DTE.")
            return []

        # ── 4. Filter strikes: OTM band below current price ────────────────
        strike_lo = current_price * (1.0 - otm_max)
        strike_hi = current_price * (1.0 - otm_min)
        valid_strikes = sorted([s for s in chain.strikes if strike_lo <= s <= strike_hi])

        if not valid_strikes:
            logger.info(
                f"{instr.symbol}: No strikes in OTM band "
                f"[{strike_lo:.2f} – {strike_hi:.2f}] (price={current_price:.2f})."
            )
            return []

        # ── 5. Build candidate contracts (cap to keep IBKR load minimal) ───
        # Max 2 nearest expiries × max 6 strikes = max 12 contracts per scan
        contracts_meta = []
        for exp_str, exp_date, dte in valid_exps[:2]:
            for strike in valid_strikes[:6]:
                opt = Option(instr.symbol, exp_str, strike, 'P', opt_exchange)
                contracts_meta.append({
                    'contract':        opt,
                    'expiry_str':      exp_str,
                    'expiry_readable': exp_date.strftime('%d %b %Y'),
                    'dte':             dte,
                    'strike':          strike,
                })

        if not contracts_meta:
            return []

        # ── 6. Qualify all candidates in one batch call ────────────────────
        try:
            qualified_opts = await asyncio.wait_for(
                ib.qualifyContractsAsync(*[m['contract'] for m in contracts_meta]),
                timeout=20
            )
        except Exception as e:
            logger.error(f"{instr.symbol}: Option qualification failed: {e}")
            return []

        # Map qualified contracts back to metadata by (strike, expiry)
        qualified_map = {
            (qc.strike, qc.lastTradeDateOrContractMonth): qc
            for qc in qualified_opts
            if qc.conId
        }

        paired = [
            (qualified_map[(m['strike'], m['expiry_str'])], m)
            for m in contracts_meta
            if (m['strike'], m['expiry_str']) in qualified_map
        ]

        if not paired:
            logger.info(f"{instr.symbol}: No option contracts could be qualified.")
            return []

        # ── 7. Fetch tickers (Greeks) in one batch call ────────────────────
        try:
            tickers = await asyncio.wait_for(
                ib.reqTickersAsync(*[qc for qc, _ in paired]),
                timeout=20
            )
        except Exception as e:
            logger.error(f"{instr.symbol}: Option ticker fetch failed: {e}")
            return []

        # ── 8. Apply delta filter and compute metrics ──────────────────────
        results = []
        for ticker, (_, meta) in zip(tickers, paired):
            greeks = ticker.modelGreeks
            if not greeks or greeks.delta is None:
                continue

            delta_abs = abs(greeks.delta)
            if not (delta_min <= delta_abs <= delta_max):
                continue

            bid = ticker.bid if (ticker.bid and ticker.bid > 0) else 0.0
            ask = ticker.ask if (ticker.ask and ticker.ask > 0) else 0.0
            mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else (bid or ask)

            if mid <= 0:
                continue

            strike = meta['strike']
            dte    = meta['dte']

            # Annualised yield = (premium / strike) * (365 / DTE) * 100
            annual_yield   = (mid / strike) * (365.0 / dte) * 100.0
            break_even     = strike - mid
            protection_pct = ((current_price - break_even) / current_price) * 100.0

            results.append({
                'strike':           strike,
                'expiry_readable':  meta['expiry_readable'],
                'dte':              dte,
                'delta':            round(greeks.delta, 3),
                'bid':              round(bid, 2),
                'ask':              round(ask, 2),
                'mid':              round(mid, 2),
                'annual_yield_pct': round(annual_yield, 1),
                'break_even':       round(break_even, 2),
                'protection_pct':   round(protection_pct, 1),
                'iv_pct':           round(greeks.impliedVol * 100.0, 1) if greeks.impliedVol else None,
            })

        results.sort(key=lambda x: x['annual_yield_pct'], reverse=True)
        top = results[:max_res]

        if top:
            logger.info(
                f"{instr.symbol}: Found {len(top)} put candidates. "
                f"Best yield: %{top[0]['annual_yield_pct']:.1f} "
                f"({top[0]['strike']:.0f}P {top[0]['expiry_readable']})"
            )

        return top

    except asyncio.TimeoutError:
        logger.error(f"{instr.symbol}: Timeout during option chain scan.")
        return []
    except Exception as e:
        logger.error(f"{instr.symbol}: Option scan unexpected error: {e}")
        return []
