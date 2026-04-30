import pandas as pd

def evaluate_watchlist_state(item, instr, current_price, current_vol, current_iv, bars, latest_fund_score, cfg):
    """
    Evaluates the state of a watchlist item and determines if an action/alert is needed.
    
    Returns:
        dict: {
            "new_state": str,
            "has_alert": bool,
            "is_high_iv": bool,
            "is_oversold": bool,
            "is_high_volume": bool,
            "latest_rsi": float,
            "avg_vol": float,
            "score": float,
            "state_changes": list,
            "vol_status": str,
            "strategy": str,
            "state_emoji": str
        }
    """
    iv_ultra = cfg.get("iv_ultra", 80.0)
    iv_high = cfg.get("iv_high", 70.0)
    iv_mid = cfg.get("iv_mid", 40.0)
    rsi_limit = cfg.get("rsi_oversold", 32.0)
    vol_mult = cfg.get("volume_spike_multiplier", 1.5)
    labels = cfg.get("labels", {})

    latest_rsi = 50.0
    avg_vol = 0
    
    if bars and len(bars) > 50:
        latest_rsi = getattr(bars[-1], 'rsi_14', 50.0) or 50.0
        df = pd.DataFrame([getattr(b, 'volume', 0) for b in bars], columns=['volume'])
        avg_vol = df['volume'].mean()
        if pd.isna(avg_vol):
            avg_vol = 0

    is_high_iv = current_iv > iv_high
    is_oversold = latest_rsi < rsi_limit
    is_high_volume = current_vol > (avg_vol * vol_mult) if avg_vol > 0 else False

    new_state = "Watching"
    has_alert = False
    state_changes = []

    if is_high_iv:
        state_changes.append(f"🚨 High Premium (IV > {iv_high:.0f}%)")
    if is_oversold and is_high_volume:
        state_changes.append("⚡ Oversold Recovery Supported by Volume")

    score = latest_fund_score if latest_fund_score is not None else (item.fundamental_score if item.fundamental_score else 0.0)

    # Put Sell Opportunity Logic
    min_ps_score = cfg.get("put_sell_min_score", 75)
    if (score > min_ps_score or item.source == 'Manual') and is_oversold and is_high_iv:
        new_state = "Action"
        has_alert = True

    # Strategy and Vol Status labeling
    if current_iv >= iv_ultra:
        vol_status = labels.get("vol_ultra", "🌋 ULTRA")
        strategy = labels.get("strat_ultra", "💸 SELL PREMIUM")
    elif current_iv >= iv_high:
        vol_status = labels.get("vol_high", "🔥 HIGH")
        strategy = labels.get("strat_high", "🛡️ CSP (Deep OTM)")
    elif current_iv >= iv_mid:
        vol_status = labels.get("vol_mid", "📊 MID")
        strategy = labels.get("strat_mid", "⚖️ NEUTRAL")
    else:
        vol_status = labels.get("vol_low", "🧊 LOW")
        strategy = labels.get("strat_low", "🏦 BUY STOCK")

    state_emoji = "👀"
    if new_state == "Action": state_emoji = "🔥"
    
    return {
        "new_state": new_state,
        "has_alert": has_alert,
        "is_high_iv": is_high_iv,
        "is_oversold": is_oversold,
        "is_high_volume": is_high_volume,
        "latest_rsi": latest_rsi,
        "avg_vol": avg_vol,
        "score": score,
        "state_changes": state_changes,
        "vol_status": vol_status,
        "strategy": strategy,
        "state_emoji": state_emoji
    }
