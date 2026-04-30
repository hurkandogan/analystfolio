import yfinance as yf
import asyncio
import logging

logger = logging.getLogger("YahooClient")

class YahooFinanceClient:
    """
    Backup data source that activates when IBKR data is unavailable.
    """
    async def get_prices(self, symbol_map: dict[str, str]) -> dict[str, dict]:
        """
        Fetches prices according to the given {InternalKey: YahooTicker} map.
        E.g.: {'DXY': 'DX-Y.NYB', 'BTC': 'BTC-USD'}
        Return: {'DXY': {'price': 104.5, 'change_pct': 0.25}}
        """
        return await asyncio.to_thread(self._fetch_sync, symbol_map)

    def _fetch_sync(self, symbol_map: dict[str, str]) -> dict[str, dict]:
        results = {}
        for key, ticker_symbol in symbol_map.items():
            try:
                t = yf.Ticker(ticker_symbol)
                # Fetch 5 days of data to catch the previous close (for weekends etc.)
                hist = t.history(period="5d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    change_pct = 0.0
                    
                    if len(hist) >= 2:
                        prev_close = float(hist['Close'].iloc[-2])
                        if prev_close > 0:
                            change_pct = ((current_price - prev_close) / prev_close) * 100

                    results[key] = {
                        "price": current_price,
                        "change_pct": change_pct
                    }
            except Exception as e:
                logger.warning(f"Yahoo data fetch failed for {key} ({ticker_symbol}): {e}")
        return results

yahoo_client = YahooFinanceClient()