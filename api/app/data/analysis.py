import pandas as pd
import numpy as np
from datetime import timedelta

class TechnicalAnalysis:
    @staticmethod
    def calculate_support_resistance(bars, window=10):
        """
        Advanced Support and Resistance calculation.
        """
        if not bars:
            return {"supports": [], "resistances": []}

        data = []
        for b in bars:
            if hasattr(b, 'high'):
                data.append({'high': b.high, 'low': b.low, 'close': b.close, 'volume': getattr(b, 'volume', 0)})
            elif isinstance(b, dict):
                data.append({'high': b['high'], 'low': b['low'], 'close': b['close'], 'volume': b.get('volume', 0)})

        df = pd.DataFrame(data)
        if len(df) < window * 2:
            return {"supports": [], "resistances": []}

        current_price = df['close'].iloc[-1]
        
        # 1. Find Pivot Points
        df['is_min'] = df['low'] == df['low'].rolling(window=window, center=True).min()
        df['is_max'] = df['high'] == df['high'].rolling(window=window, center=True).max()
        
        pivots = df[df['is_min']]['low'].tolist() + df[df['is_max']]['high'].tolist()
        pivots = sorted(list(set(pivots)))

        if not pivots:
            return {"supports": [], "resistances": []}

        # 2. Group Levels (Clustering)
        threshold = current_price * 0.015 
        clusters = []
        if pivots:
            curr_cluster = [pivots[0]]
            for i in range(1, len(pivots)):
                cluster_mean = sum(curr_cluster) / len(curr_cluster)
                if pivots[i] - cluster_mean <= threshold:
                    curr_cluster.append(pivots[i])
                else:
                    clusters.append(sum(curr_cluster) / len(curr_cluster))
                    curr_cluster = [pivots[i]]
            clusters.append(sum(curr_cluster) / len(curr_cluster))

        # 3. Calculate Level Strength
        scored_levels = []
        for level in clusters:
            margin = level * 0.0075
            zone_min = round(level - margin, 2)
            zone_max = round(level + margin, 2)
            
            hits = df[(df['close'] <= zone_max) & (df['close'] >= zone_min)]
            score = len(hits)
            
            scored_levels.append({
                "price": round(level, 2),
                "zone": [zone_min, zone_max],
                "score": score
            })

        # 4. Classification
        supports = [l for l in scored_levels if l['price'] < current_price]
        resistances = [l for l in scored_levels if l['price'] > current_price]

        top_supports = sorted(supports, key=lambda x: x['score'], reverse=True)[:3]
        top_resistances = sorted(resistances, key=lambda x: x['score'], reverse=True)[:3]

        return {
            "supports": sorted([s['price'] for s in top_supports], reverse=True),
            "resistances": sorted([r['price'] for r in top_resistances]),
            "supports_detailed": sorted(top_supports, key=lambda x: x['price'], reverse=True),
            "resistances_detailed": sorted(top_resistances, key=lambda x: x['price'])
        }

    @staticmethod
    def calculate_momentum_metrics(bars, min_periods=60):
        """
        Calculates RSI (14), Rvol, Golden Cross, and price changes.
        """
        if not bars or len(bars) < 20:
            return {"rsi": None, "rvol": None, "avg_vol_3m": 0, "status": "Neutral", "rsi_trending_up": False, "golden_cross_recent": False, "change_30d": 0}
            
        res = {
            "rsi": None, 
            "rvol": None, 
            "avg_vol_3m": 0, 
            "status": "Neutral", 
            "rsi_trending_up": False, 
            "golden_cross_recent": False,
            "change_30d": 0
        }

        try:
            df_hourly = pd.DataFrame([{
                'timestamp': getattr(b, 'timestamp', None) or b.get('timestamp'),
                'close': getattr(b, 'close', None) or b.get('close'),
                'volume': getattr(b, 'volume', 0) or b.get('volume', 0)
            } for b in bars])
            
            df_hourly['timestamp'] = pd.to_datetime(df_hourly['timestamp'])
            df_hourly.set_index('timestamp', inplace=True)
            
            df_daily = df_hourly.resample('D').agg({
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            if len(df_daily) > 2:
                current_price = df_daily['close'].iloc[-1]
                
                # 1. Price Change (Last 30 days)
                # We use -21 for approx 1 trading month if daily data is limited, 
                # but since we have 1 year of daily data, we can use exact calendar days if available.
                # Actually, -30 in the resampled daily dataframe is 30 calendar days of activity.
                start_30d_price = df_daily['close'].iloc[-30] if len(df_daily) >= 30 else df_daily['close'].iloc[0]
                res["change_30d"] = (current_price - start_30d_price) / start_30d_price if start_30d_price > 0 else 0

                # 2. RSI (14)
                delta = df_daily['close'].diff()
                up = delta.clip(lower=0); down = -1 * delta.clip(upper=0)
                # com = (span - 1) / 2 = (14 - 1) / 2 = 6.5 for RSI-14
                ma_up = up.ewm(com=6.5, adjust=False).mean(); ma_down = down.ewm(com=6.5, adjust=False).mean()
                rs = ma_up / ma_down; rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                res["rsi"] = round(current_rsi, 2)
                if len(rsi) >= 5: res["rsi_trending_up"] = bool(rsi.iloc[-1] > rsi.iloc[-5])

                # 3. RVOL
                avg_vol = df_daily['volume'].iloc[-61:-1].mean() if len(df_daily) > 60 else df_daily['volume'].mean()
                curr_vol = df_daily['volume'].iloc[-1]
                rvol = (curr_vol / avg_vol) if avg_vol > 0 else 0
                res["rvol"] = round(float(rvol), 2); res["avg_vol_3m"] = float(avg_vol)

                # 4. Golden Cross
                if len(df_daily) >= 200:
                    sma50 = df_daily['close'].rolling(window=50).mean()
                    sma200 = df_daily['close'].rolling(window=200).mean()
                    last_30_cross = False
                    for i in range(-30, 0):
                        if i-1 < -len(sma50): continue
                        if sma50.iloc[i-1] <= sma200.iloc[i-1] and sma50.iloc[i] > sma200.iloc[i]:
                            last_30_cross = True; break
                    res["golden_cross_recent"] = bool(last_30_cross)

                # Status
                status = "Neutral"
                if rvol > 3.0: status = "Unusual Activity 🚨"
                elif rvol > 1.5: status = "High Vol 🚀"
                elif current_rsi > 70: status = "Overbought ⚠️"
                elif current_rsi < 30: status = "Oversold 🟢"
                res["status"] = status

                return res
        except Exception: pass
        return res

analysis = TechnicalAnalysis()


def get_momentum_value(momentum_data, key: str, default=None):
    """Safely reads a field from momentum_data whether it's a dict or an object."""
    if isinstance(momentum_data, dict):
        return momentum_data.get(key, default)
    return getattr(momentum_data, key, default)
