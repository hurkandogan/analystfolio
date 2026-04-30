import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.data.indicators import indicators

logger = logging.getLogger(__name__)

class MarketDataProcessor:
    """
    Takes raw bar data, calculates indicators, and 
    converts it to the format to be saved in the DB.
    """

    def process_bars(self, instrument_id: int, bars: List, timeframe: str = '1h') -> List[Dict[str, Any]]:
        """
        Processes the bar list and returns a list of database records.
        """
        if not bars:
            return []

        # 1. De-duplicate and Sort
        unique_bars = {b.date: b for b in bars}
        sorted_bars = sorted(unique_bars.values(), key=lambda x: x.date)

        # 2. Convert to DataFrame
        data = []
        for b in sorted_bars:
            dt = b.date
            # Attempt to normalize all datetimes to UTC to satisfy Pandas uniform DataFrame typing
            if hasattr(dt, 'tzinfo'):
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
            elif type(dt) is type(datetime.today().date()):
                dt = datetime.combine(dt, datetime.min.time()).replace(tzinfo=timezone.utc)

            data.append({
                'timestamp': dt, 
                'open': b.open, 
                'high': b.high, 
                'low': b.low, 
                'close': b.close, 
                'volume': int(b.volume or 0)
            })
        df = pd.DataFrame(data)

        # 3. Calculations
        # Daily return
        df['daily_return'] = df['close'].pct_change() * 100

        # Indicators (using indicators.py)
        if timeframe == '1h':
            df = indicators.calculate_daily_metrics_for_hourly(df)
        
        # NaN cleanup
        df = df.replace({np.nan: None})
        
        # 4. Convert to Save Format
        records = df.to_dict('records')
        # Date filtering (Instead of skipping today entirely, just skip future/unfinished hour)
        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.replace(minute=0, second=0, microsecond=0)
        
        save_data = []
        for r in records:
            # If timestamp is not timezone-aware (from pandas conversion), make it UTC
            ts = r['timestamp']
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            
            # Skip future or current (not yet closed) hour
            # Note: IBKR 'TRADES' data might give the open, close or start time of the bar.
            # Usually: 10:00 bar covers 10:00-11:00. IF timestamp is 10:00 and it's 10:30 now, this bar is not finished.
            # Those SMALLER than the current hour are completed.
            if ts >= current_hour:
                continue
                
            save_data.append({
                "instrument_id": instrument_id,
                "timestamp": r['timestamp'],
                "timeframe": timeframe,
                "open": r['open'], 
                "high": r['high'], 
                "low": r['low'], 
                "close": r['close'], 
                "volume": r['volume'],
                "ma_50": r['ma_50'], 
                "ma_200": r['ma_200'], 
                "rsi_14": r['rsi_14'],
                "daily_return": r['daily_return']
            })
            
        return save_data

market_processor = MarketDataProcessor()
