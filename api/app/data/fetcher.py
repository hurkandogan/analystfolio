import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Any
from ib_async import Stock, BarDataList
from sqlalchemy import select, func

from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.models.common import MarketDataCache
from app.data.repository import DataRepository

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    """
    Manages historical data fetching from IBKR.
    Includes Deep Scan and Gap Fill logic.
    """

    async def get_historical_bars(self, repo: DataRepository, instr, timeframe: str = '1h') -> Tuple[List, bool]:
        """
        Fetches necessary bars for the instrument.
        Decides whether Deep Scan is needed.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        is_deep_scan = self._check_deep_scan(instr, today)
        
        # Find existing data range in DB
        earliest_ts, latest_ts = await self._get_db_range(repo, instr.id, timeframe)
        
        # 0. Data Integrity Check (Split/Dividend Check)
        # If data exists, compare last 5 days close with IBKR.
        if latest_ts and not is_deep_scan:
            integrity_ok = await self._check_integrity(repo, instr, timeframe, latest_ts)
            if not integrity_ok:
                logger.warning(f"⚠️ {instr.symbol}: Data mismatch (Split/Dividend?) detected. Deep scan starting.")
                is_deep_scan = True

        fetch_queue = self._build_fetch_queue(is_deep_scan, today, earliest_ts, latest_ts)
        
        if not fetch_queue:
            return [], False

        all_bars = []
        contract = Stock(symbol=instr.symbol, exchange='SMART', currency='USD')
        
        for end_time, duration in fetch_queue:
            try:
                bars = await ibkr_client.ib.reqHistoricalDataAsync(
                    contract, endDateTime=end_time, durationStr=duration,
                    barSizeSetting='1 hour' if timeframe == '1h' else timeframe, 
                    whatToShow='TRADES', useRTH=True, formatDate=1
                )
                if bars:
                    all_bars.extend(bars)
                
                # Dynamic Protection against IBKR Pacing Violation
                # If requesting > 1 Month of data, sleep longer
                if 'Y' in duration or ('M' in duration and int(duration.split()[0]) > 1):
                    await asyncio.sleep(5.0)
                else:
                    await asyncio.sleep(1.0) 
            except Exception as e:
                error_str = str(e).lower()
                logger.error(f"Fetch Error {instr.symbol}: {e}")
                
                # Handle IBKR Error 162: Historical Market Data Service error message (Pacing Violation)
                if "162" in error_str or "pacing violation" in error_str:
                    logger.warning(f"🚨 Pacing Violation detected for {instr.symbol}. Sleeping 60 seconds to cool down IBKR.")
                    await asyncio.sleep(60.0)
                
                if is_deep_scan:
                    # Don't crash the whole bot, just skip this instrument's deep scan for now
                    logger.error(f"Deep scan failed for {instr.symbol}, skipping to next.")
                    break

        return all_bars, is_deep_scan

    def _check_deep_scan(self, instr, today) -> bool:
        """Determines whether a full scan will be performed one day a month based on the letters of the symbol."""
        refresh_day = (sum(ord(c) for c in instr.symbol) % 28) + 1
        return (today.day == refresh_day) and (not instr.updated_at or instr.updated_at.date() != today)

    async def _get_db_range(self, repo: DataRepository, instrument_id: int, timeframe: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        stmt_min = select(func.min(MarketDataCache.timestamp)).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == timeframe
        )
        earliest_ts = (await repo.session.execute(stmt_min)).scalar()
        
        stmt_max = select(func.max(MarketDataCache.timestamp)).where(
            MarketDataCache.instrument_id == instrument_id,
            MarketDataCache.timeframe == timeframe
        )
        latest_ts = (await repo.session.execute(stmt_max)).scalar()
        
        return earliest_ts, latest_ts

    def _build_fetch_queue(self, is_deep_scan: bool, today, earliest_ts, latest_ts) -> List[Tuple[str, str]]:
        fetch_queue = []
        
        if is_deep_scan:
            start_date = earliest_ts.date() if earliest_ts else (today - timedelta(days=365*2))
            current_cursor = today
            while current_cursor > start_date:
                days_diff = (current_cursor - start_date).days
                if days_diff <= 0: break
                
                duration = "1 Y"
                if days_diff < 365:
                    duration = f"{days_diff + 5} D"
                
                end_time = current_cursor.strftime('%Y%m%d %H:%M:%S')
                fetch_queue.append((end_time, duration))
                current_cursor -= timedelta(days=365)
        else:
            if not latest_ts:
                fetch_queue.append(('', '1 Y'))
            else:
                target_date = today - timedelta(days=1)
                while target_date.weekday() >= 5: 
                    target_date -= timedelta(days=1)
                
                if latest_ts.date() < target_date:
                    delta = (today - latest_ts.date()).days
                    fetch_queue.append(('', f"{min(delta + 2, 365)} D"))
                    
        return fetch_queue

    async def get_market_snapshot(self, instr) -> Optional[tuple[float, int]]:
        """
        Fetches real-time price and volume info for the instrument.
        Returns: (price, volume)
        """
        if not ibkr_client.is_connected():
            return None

        contract = Stock(symbol=instr.symbol, exchange='SMART', currency='USD')
        
        try:
            # Contract Qualify
            await ibkr_client.ib.qualifyContractsAsync(contract)
            
            # Request Ticker
            tickers = await ibkr_client.ib.reqTickersAsync(contract)
            if not tickers:
                return None
            
            ticker = tickers[0]
            
            # Price priority: Last > Close > Bid/Ask Mid
            price = ticker.marketPrice()
            if not price or price <= 0:
                price = ticker.close if ticker.close > 0 else 0
                
            volume = ticker.volume if ticker.volume else 0
            
            return price, volume

        except Exception as e:
            logger.error(f"Snapshot Error {instr.symbol}: {e}")
            return None

    async def _check_integrity(self, repo: DataRepository, instr, timeframe: str, latest_ts: datetime) -> bool:
        """
        Fetches last N bars from IBKR and compares with DB.
        If there is a significant price difference (2%+), returns False (Split/Dividend suspicion).
        """
        if not ibkr_client.is_connected():
            return True # No connection, no need to panic, continue with existing

        try:
            # 1. Fetch last 5 bars from DB
            # Note: Timezone awareness is important
            stmt = select(MarketDataCache).where(
                MarketDataCache.instrument_id == instr.id,
                MarketDataCache.timeframe == timeframe
            ).order_by(MarketDataCache.timestamp.desc()).limit(5)
            
            db_bars = (await repo.session.execute(stmt)).scalars().all()
            if not db_bars: 
                return True
            
            # Date of the last bar (we will request backwards from here via IBKR)
            end_date_str = latest_ts.strftime('%Y%m%d %H:%M:%S')
            
            # 2. Request data for the same date from IBKR (Duration = 1 W is enough for last 5 bars for hourly)
            contract = Stock(symbol=instr.symbol, exchange='SMART', currency='USD')
            
            # Request 2 days of data for validation (guaranteed to cover 5 bars in hourly)
            ib_bars = await ibkr_client.ib.reqHistoricalDataAsync(
                contract, endDateTime=end_date_str, durationStr='2 D',
                barSizeSetting='1 hour' if timeframe == '1h' else timeframe, 
                whatToShow='TRADES', useRTH=True, formatDate=1
            )
            
            if not ib_bars: return True

            # 3. Compare
            # Make DB bars a dict: {timestamp: close}
            db_map = {b.timestamp.replace(tzinfo=None) : b.close for b in db_bars} # replace in case IBKR returns naive
            
            mismatch_count = 0
            for ib_b in ib_bars:
                # If IBKR bar.date is not a datetime object, parse it
                # ib_async usually returns a datetime object
                ib_date = ib_b.date
                if isinstance(ib_date, datetime):
                     ib_date = ib_date.replace(tzinfo=None)
                
                if ib_date in db_map:
                    db_close = db_map[ib_date]
                    ib_close = ib_b.close
                    
                    if db_close == 0: continue
                    
                    diff_pct = abs(ib_close - db_close) / db_close
                    if diff_pct > 0.02: # 2% difference
                        logger.warning(f"Integrity Check Fail {instr.symbol} @ {ib_date}: DB={db_close}, IB={ib_close}")
                        mismatch_count += 1
            
            if mismatch_count > 0:
                return False # Integrity Failed
                
            return True

        except Exception as e:
            logger.error(f"Integrity check error {instr.symbol}: {e}")
            return True # Don't trigger deep scan on error, stay safe

    async def get_implied_volatility(self, instr, duration_days: int = 252) -> Optional[float]:
        """
        Queries 'OPTION_IMPLIED_VOLATILITY' data via IBKR.
        By default returns the latest IV info (float as percentage, e.g.: 0.25 => 25%).
        :param duration_days: (Backup) period if historical IV is desired for IV Rank.
        :return: Last IV (or None)
        """
        if not ibkr_client.is_connected():
            return None

        contract = Stock(symbol=instr.symbol, exchange='SMART', currency='USD')
        
        try:
            # We can just fetch the last 2 days of IV data and take the latest.
            # If you want to calculate IV Rank, we can fetch duration_days and find min-max
            # but min period is enough if the bot will look at "current" IV.
            
            # Note: For IV Rank (Annual), a 1-year IV history is usually needed.
            # If iv_rank in DB is insufficient, 252 D can be fetched here and rank formula applied:
            # IV Rank = 100 * (current_IV - min_IV) / (max_IV - min_IV)
            
            # For now, to avoid taxing IBKR with historical IV calculations,
            # we are only fetching today's/yesterday's IV value. (Rank = how much expensive)
            bars = await ibkr_client.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='5 D', # Guarantee we get at least 1 recent trading day
                barSizeSetting='1 day',
                whatToShow='OPTION_IMPLIED_VOLATILITY',
                useRTH=True,
                formatDate=1
            )
            
            if not bars:
                return None
            
            # The close price of an IV bar represents the Implied Volatility (e.g., 0.23 means 23%)
            latest_iv = bars[-1].close
            return latest_iv * 100.0 # Return as percentage (23.0)

        except Exception as e:
            logger.error(f"IV Fetch Error {instr.symbol}: {e}")
            return None

market_fetcher = MarketDataFetcher()
