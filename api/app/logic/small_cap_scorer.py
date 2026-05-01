from app.data.analysis import analysis, get_momentum_value

def evaluate_small_cap(instr, fdata, bars, sector_avg_ps, cfg):
    """
    Evaluates small-cap stock metrics based on a 10-point scale.
    ROIC < 0 filter is applied in the bot before calling this.
    """
    weights = cfg.get("weights", {})
    
    # Momentum and Volume
    momentum_data = analysis.calculate_momentum_metrics(bars, min_periods=60)
    avg_vol_3m = get_momentum_value(momentum_data, "avg_vol_3m", 0)
    rvol = get_momentum_value(momentum_data, "rvol", 0)
    
    current_price = 0.0
    if bars:
        current_price = getattr(bars[-1], 'close', 0.0) or (bars[-1].get('close', 0.0) if isinstance(bars[-1], dict) else 0.0)

    # Scoring Phase (10-point scale)
    score = 0
    reasons = []
    score_details = {}

    # 1. Revenue Growth (30%+) -> 3 Points
    if fdata.revenue_growth and fdata.revenue_growth >= 0.30:
        pts = 3
        score += pts
        msg = f"Strong Revenue Growth ({fdata.revenue_growth:.1%})"
        reasons.append(msg)
        score_details["revenue_growth"] = {"points": pts, "detail": msg}
    
    # 2. Gross Margin (> 50%) -> 2 Points
    if fdata.gross_margin and fdata.gross_margin >= 0.50:
        pts = 2
        score += pts
        msg = f"Excellent Gross Margin ({fdata.gross_margin:.1%})"
        reasons.append(msg)
        score_details["gross_margin"] = {"points": pts, "detail": msg}
    
    # 3. Positive Operating Cash Flow -> 2 Points
    if fdata.operating_cash_flow and fdata.operating_cash_flow > 0:
        pts = 2
        score += pts
        msg = "Positive Operating Cash Flow"
        reasons.append(msg)
        score_details["positive_cash_flow"] = {"points": pts, "detail": msg}
    
    # 4. ROIC (> 12%) -> 2 Points
    if fdata.roic and fdata.roic >= 0.12:
        pts = 2
        score += pts
        msg = f"High Efficiency (ROIC: {fdata.roic:.1%})"
        reasons.append(msg)
        score_details["roic_bonus"] = {"points": pts, "detail": msg}
    
    # 5. Price/Sales < Sector Average -> 1 Point
    s_avg = sector_avg_ps.get(instr.sector)
    if s_avg and fdata.price_to_sales and fdata.price_to_sales < s_avg:
        pts = 1
        score += pts
        msg = f"Value P/S ({fdata.price_to_sales:.1f} < Sector: {s_avg:.1f})"
        reasons.append(msg)
        score_details["valuation"] = {"points": pts, "detail": msg}

    return {
        "score": score,
        "reasons": reasons,
        "score_details": score_details,
        "avg_vol_3m": avg_vol_3m or 0,
        "rvol": rvol or 0,
        "current_price": current_price,
        "momentum_data": momentum_data,
        "s_avg": s_avg
    }
