import pandas as pd
import numpy as np

class TechnicalIndicators:
    @staticmethod
    def calculate_daily_metrics_for_hourly(df_hourly: pd.DataFrame) -> pd.DataFrame:
        """
        Takes hourly data, converts it to daily period, and calculates MA50, MA200, and RSI.
        Then maps these values back to hourly data (backfill).
        """
        if df_hourly.empty:
            return df_hourly

        # Calculate daily closes
        df_hourly['timestamp'] = pd.to_datetime(df_hourly['timestamp'])
        daily_closes = df_hourly.set_index('timestamp')['close'].resample('1D').last().dropna()
        
        # Calculate indicators (Daily basis)
        daily_ma_50 = daily_closes.rolling(window=50).mean()
        daily_ma_200 = daily_closes.rolling(window=200).mean()
        
        # RSI Calculation
        delta = daily_closes.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.ewm(com=13, adjust=False, min_periods=14).mean()
        ma_down = down.ewm(com=13, adjust=False, min_periods=14).mean()
        rs = ma_up / ma_down
        daily_rsi = 100 - (100 / (1 + rs))
        
        # Convert calculated values to dictionary using string dates for safe mapping
        # `daily_closes.index` has the date. We convert it to a string 'YYYY-MM-DD'
        ma_50_map = {k.strftime('%Y-%m-%d'): v for k, v in daily_ma_50.items()}
        ma_200_map = {k.strftime('%Y-%m-%d'): v for k, v in daily_ma_200.items()}
        rsi_map = {k.strftime('%Y-%m-%d'): v for k, v in daily_rsi.items()}
        
        # Map back to hourly data
        # Each hourly bar gets the indicator value from its strftime day string
        df_hourly['ma_50'] = df_hourly['timestamp'].apply(lambda x: ma_50_map.get(x.strftime('%Y-%m-%d')))
        df_hourly['ma_200'] = df_hourly['timestamp'].apply(lambda x: ma_200_map.get(x.strftime('%Y-%m-%d')))
        df_hourly['rsi_14'] = df_hourly['timestamp'].apply(lambda x: rsi_map.get(x.strftime('%Y-%m-%d')))
        
        return df_hourly

    @staticmethod
    def calculate_sma(series: pd.Series, window: int) -> pd.Series:
        """
        Calculates Simple Moving Average (SMA).
        """
        return series.rolling(window=window).mean()

indicators = TechnicalIndicators()