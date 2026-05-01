from app.data.analysis import analysis, get_momentum_value

def evaluate_fundamentals(instr, fdata, bars, wacc, cfg):
    """
    Evaluates fundamental metrics for rapid-upside potential (Total 10 pts).
    Revenue Growth (2), Analyst Upside (2), ROE/ROIC (2),
    RSI Accumulation Zone (1), Golden Cross (1), rVol (1), Valuation (1).
    """
    momentum_data = analysis.calculate_momentum_metrics(bars, min_periods=60)

    score = 0
    reasons = []
    score_details = {}
    is_unusual_activity = False

    rev_growth_thr  = float(cfg.get("revenue_growth_threshold", 0.15))
    upside_thr      = float(cfg.get("analyst_upside_threshold", 0.15))
    quality_thr     = float(cfg.get("roe_roic_threshold", 0.10))
    rsi_min         = float(cfg.get("rsi_min", 40.0))
    rsi_max         = float(cfg.get("rsi_max", 65.0))
    rvol_thr        = float(cfg.get("rvol_threshold", 1.5))
    peg_max         = float(cfg.get("peg_max", 1.2))
    pe_max          = float(cfg.get("pe_max", 30.0))

    # ── 1. REVENUE GROWTH (2 points) ──────────────────────────────────────
    # Best forward-looking signal for rapid price appreciation.
    rev_growth = fdata.revenue_growth or 0
    if rev_growth > rev_growth_thr:
        pts = 2
        score += pts
        msg = f"Strong Revenue Growth ({rev_growth:.1%})"
        reasons.append(msg)
        score_details["revenue_growth"] = {"points": pts, "detail": msg}

    # ── 2. ANALYST UPSIDE (2 points) ──────────────────────────────────────
    # Consensus target price implies meaningful upside.
    current_price = 0.0
    if bars:
        current_price = getattr(bars[-1], 'close', 0.0) or (bars[-1].get('close', 0.0) if isinstance(bars[-1], dict) else 0.0)

    analyst_upside = None
    if fdata.target_price and current_price and current_price > 0:
        analyst_upside = (fdata.target_price / current_price) - 1.0

    if analyst_upside is not None and analyst_upside > upside_thr:
        pts = 2
        score += pts
        msg = f"Analyst Upside ({analyst_upside:.1%} → ${fdata.target_price:.2f})"
        reasons.append(msg)
        score_details["analyst_upside"] = {"points": pts, "detail": msg}

    # ── 3. ROE / ROIC (2 points) ──────────────────────────────────────────
    # Capital efficiency confirms the business can compound the growth.
    roe  = fdata.roe  or 0
    roic = fdata.roic or 0
    if roe > quality_thr or roic > quality_thr:
        pts = 2
        score += pts
        val = max(roe, roic)
        msg = f"High Quality (ROE/ROIC: {val:.1%})"
        reasons.append(msg)
        score_details["quality_metrics"] = {"points": pts, "detail": msg}

    # ── 4. RSI ACCUMULATION ZONE (1 point) ────────────────────────────────
    # Stock building up in the 40–65 range with rising momentum = early entry.
    rsi    = get_momentum_value(momentum_data, "rsi")
    rsi_up = get_momentum_value(momentum_data, "rsi_trending_up", False)
    if rsi and rsi_min < rsi < rsi_max and rsi_up:
        pts = 1
        score += pts
        msg = f"RSI Accumulation Zone ({rsi:.1f}, Rising)"
        reasons.append(msg)
        score_details["rsi_trend"] = {"points": pts, "detail": msg}

    # ── 5. GOLDEN CROSS (1 point) ─────────────────────────────────────────
    is_gc = get_momentum_value(momentum_data, "golden_cross_recent", False)
    if is_gc:
        pts = 1
        score += pts
        msg = "Golden Cross (Last 30 days)"
        reasons.append(msg)
        score_details["golden_cross"] = {"points": pts, "detail": msg}

    # ── 6. RVOL CONFIRMATION (1 point) ────────────────────────────────────
    # Volume confirms institutional interest; alone it's not enough anymore.
    rvol = get_momentum_value(momentum_data, "rvol", 0) or 0
    if rvol > rvol_thr:
        pts = 1
        score += pts
        msg = f"Volume Confirmation (rVol {rvol:.1f}x)"
        reasons.append(msg)
        score_details["high_vol"] = {"points": pts, "detail": msg}
        if rvol > 2.5:
            is_unusual_activity = True

    # ── 7. VALUATION BONUS (1 point) ──────────────────────────────────────
    pe  = fdata.pe_ratio  or 999
    peg = fdata.peg_ratio or 999
    if peg < peg_max and pe < pe_max:
        pts = 1
        score += pts
        msg = f"Attractive Valuation (PE: {pe:.1f}, PEG: {peg:.1f})"
        reasons.append(msg)
        score_details["valuation_bonus"] = {"points": pts, "detail": msg}

    # Supports and Resistances
    sr_levels = analysis.calculate_support_resistance(bars, window=100)
    supports_str    = ", ".join([f"{s['price']:.2f} ({s['score']})" for s in sr_levels.get("supports_detailed", [])])
    resistances_str = ", ".join([f"{r['price']:.2f} ({r['score']})" for r in sr_levels.get("resistances_detailed", [])])

    return {
        "score": score,
        "reasons": reasons,
        "score_details": score_details,
        "momentum_data": momentum_data,
        "disp_roic_or_roe_label": "ROE/ROIC",
        "disp_roic_or_roe_val": f"{max(roe, roic):.1%}" if max(roe, roic) > 0 else "N/A",
        "supports_str": supports_str,
        "resistances_str": resistances_str,
        "sr_levels": sr_levels,
        "is_unusual_activity": is_unusual_activity,
        "current_price": current_price,
        "analyst_upside": analyst_upside,
        "revenue_growth": rev_growth,
    }
