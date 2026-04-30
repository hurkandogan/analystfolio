import asyncio
import logging
from typing import Dict, Any, Tuple
from ib_async import Index, Forex, Crypto, Stock, Contract, Commodity, Future

from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.yahoo_client import yahoo_client
from app.infrastructure.kraken_client import kraken_client

logger = logging.getLogger(__name__)

class SentimentFetcher:
    """
    Collects necessary data for Market Sentiment analysis from different sources (Kraken, IBKR, Yahoo).
    Manages fail-over logic (e.g., fallback to Yahoo if IBKR is unavailable) here.
    """
    
    # Constants
    YAHOO_MAP = {
        "VIX": "^VIX",
        "VXN": "^VXN",
        "SPX": "^GSPC",
        "NDX": "^NDX",
        "DAX": "^GDAXI",
        "US10Y": "^TNX",
        "GOLD": "GC=F",
        "DXY": "DX-Y.NYB",
        "BTC": "BTC-USD"
    }

    TARGET_KEYS = ["VIX", "VXN", "SPX", "NDX", "DAX", "US10Y", "GOLD", "DXY", "BTC"]

    async def fetch_all(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Fetches all market data.
        Return: (market_data, market_changes)
        """
        market_data = {}
        market_changes = {}

        # 1. KRAKEN (BTC)
        await self._fetch_kraken_btc(market_data, market_changes)

        # 2. IBKR (Indices & Commodities)
        await self._fetch_ibkr_data(market_data, market_changes)

        # 3. YAHOO (Fallback)
        await self._fetch_yahoo_fallback(market_data, market_changes)

        return market_data, market_changes

    async def _fetch_kraken_btc(self, data: Dict, changes: Dict):
        try:
            btc_ticker = await kraken_client.get_ticker("XBTUSD")
            if btc_ticker:
                price = float(btc_ticker['c'][0])
                open_price = float(btc_ticker['o'])
                
                data["BTC"] = price
                if open_price > 0:
                    changes["BTC"] = ((price - open_price) / open_price) * 100
                logger.info(f"✅ KRAKEN [BTC]: {price}")
        except Exception as e:
            logger.warning(f"⚠️ Kraken BTC fetch failed: {e}")

    async def _fetch_ibkr_data(self, data: Dict, changes: Dict):
        if not ibkr_client.is_connected():
            return

        # IBKR Contract Definitions
        contracts = {
            "VIX": Index('VIX', 'CBOE'),
            "VXN": Index('VXN', 'CBOE'),
            "SPX": Index('SPX', 'CBOE'),
            "NDX": Index('NDX', 'NASDAQ'),
            "DAX": Index('DAX', 'EUREX', currency='EUR'),
            "US10Y": Index('TNX', 'CBOE'), 
            "GOLD": Commodity('XAUUSD'),
        }

        # If not received from Kraken, try BTC from IBKR
        if "BTC" not in data:
            contracts["BTC"] = Crypto('BTC', 'PAXOS', 'USD')

        ib = ibkr_client.ib
        
        for name, contract in contracts.items():
            if name in data: continue # Skip if already exists (e.g., BTC)

            try:
                # Qualify
                try:
                    await asyncio.wait_for(ib.qualifyContractsAsync(contract), timeout=5)
                except Exception:
                    continue

                # Snapshot
                tickers = await asyncio.wait_for(ib.reqTickersAsync(contract), timeout=5)
                if not tickers: continue
                
                t = tickers[0]
                price = t.marketPrice()
                
                if price and price > 0:
                    data[name] = price
                    if t.close and t.close > 0:
                        changes[name] = ((price - t.close) / t.close) * 100
                    logger.info(f"✅ IBKR [{name}]: {price}")
                elif t.close and t.close > 0:
                    data[name] = t.close
                    logger.warning(f"⚠️ IBKR [{name}] Market Closed. Using Close: {t.close}")
                
            except Exception as e:
                # logger.debug(f"IBKR fetch error for {name}: {e}")
                pass
            
            # Rate limit protection
            await asyncio.sleep(0.1)

    async def _fetch_yahoo_fallback(self, data: Dict, changes: Dict):
        missing_map = {}
        for key in self.TARGET_KEYS:
            if key not in data and key in self.YAHOO_MAP:
                missing_map[key] = self.YAHOO_MAP[key]
        
        if missing_map:
            logger.info(f"⚠️ Fetching missing data from Yahoo: {list(missing_map.keys())}")
            try:
                results = await yahoo_client.get_prices(missing_map)
                for key, val in results.items():
                    if val['price'] and val['price'] > 0:
                        data[key] = val['price']
                        changes[key] = val['change_pct']
                        logger.info(f"✅ YAHOO [{key}]: {val['price']}")
            except Exception as e:
                logger.error(f"Yahoo fallback failed: {e}")

sentiment_fetcher = SentimentFetcher()
