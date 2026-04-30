from app.data.analysis import analysis

def evaluate_fundamentals(instr, fdata, bars, wacc, cfg):
    """
    Evaluates fundamental metrics based on a new weight system (Total 9-10 pts).
    rVol (3), ROE/ROIC (2), RSI (2), Golden Cross (1), Valuation (1).
    """
    momentum_data = analysis.calculate_momentum_metrics(bars, min_periods=60)
    
    score = 0
    reasons = []
    score_details = {}
    is_unusual_activity = False

    # 1. RVOL (3 points)
    rvol = momentum_data.get("rvol") if isinstance(momentum_data, dict) else getattr(momentum_data, "rvol", 0)
    rvol = rvol or 0
    if rvol > 1.5:
        pts = 3
        score += pts
        msg = f"High Volume (rVol {rvol:.1f}x)"
        reasons.append(msg)
        score_details["high_vol"] = {"points": pts, "detail": msg}
        if rvol > 2.5: is_unusual_activity = True

    # 2. ROE / ROIC (2 points)
    roe = fdata.roe or 0
    roic = fdata.roic or 0
    if (roe and roe > 0.10) or (roic and roic > 0.10):
        pts = 2
        score += pts
        val = max(roe, roic)
        msg = f"High Quality (ROE/ROIC: {val:.1%})"
        reasons.append(msg)
        score_details["quality_metrics"] = {"points": pts, "detail": msg}

    # 3. RSI TREND (2 points)
    rsi = momentum_data.get("rsi") if isinstance(momentum_data, dict) else getattr(momentum_data, "rsi", None)
    rsi_up = momentum_data.get("rsi_trending_up") if isinstance(momentum_data, dict) else getattr(momentum_data, "rsi_trending_up", False)
    if rsi and rsi < 60 and rsi_up:
        pts = 2
        score += pts
        msg = f"RSI Breakout Trend ({rsi:.1f} & Rising)"
        reasons.append(msg)
        score_details["rsi_trend"] = {"points": pts, "detail": msg}

    # 4. GOLDEN CROSS (2 points)
    is_gc = momentum_data.get("golden_cross_recent") if isinstance(momentum_data, dict) else getattr(momentum_data, "golden_cross_recent", False)
    if is_gc:
        pts = 2
        score += pts
        msg = "Golden Cross (Last 30 days)"
        reasons.append(msg)
        score_details["golden_cross"] = {"points": pts, "detail": msg}

    # 5. VALUATION (1 point)
    pe = fdata.pe_ratio or 999
    peg = fdata.peg_ratio or 999
    if peg < 1.2 and pe < 30:
        pts = 1
        score += pts
        msg = f"Valuation Bonus (PE: {pe:.1f}, PEG: {peg:.1f})"
        reasons.append(msg)
        score_details["valuation_bonus"] = {"points": pts, "detail": msg}

    # Price and Changes
    current_price = 0.0
    if bars:
        current_price = getattr(bars[-1], 'close', 0.0) or (bars[-1].get('close', 0.0) if isinstance(bars[-1], dict) else 0.0)

    # Supports and Resistances
    sr_levels = analysis.calculate_support_resistance(bars, window=100) 
    supports_str = ", ".join([f"{s['price']:.2f} ({s['score']})" for s in sr_levels.get("supports_detailed", [])])
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
        "current_price": current_price
    }
