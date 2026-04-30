import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MarketDataValidator:
    """
    Class that validates market data before saving to the database.
    Prevents corrupt or illogical data from entering the system.
    """

    @staticmethod
    def validate_bars(symbol: str, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validates the bar list and returns ONLY the valid ones.
        """
        valid_bars = []
        now = datetime.now(timezone.utc)

        for bar in data_list:
            is_valid = True
            errors = []

            # 1. Timestamp Check (No future data allowed)
            if bar['timestamp'] > now:
                is_valid = False
                errors.append(f"Future timestamp: {bar['timestamp']}")

            # 2. Price Check (Cannot be 0 or negative)
            prices = [bar['open'], bar['high'], bar['low'], bar['close']]
            if any(p <= 0 for p in prices if p is not None):
                is_valid = False
                errors.append(f"Zero or negative price found: {prices}")

            # 3. Logical OHLC Relationship
            # High must be highest, Low must be lowest
            if bar['high'] is not None and bar['low'] is not None:
                if bar['high'] < bar['low']:
                    is_valid = False
                    errors.append(f"High ({bar['high']}) is lower than Low ({bar['low']})")
                
                if bar['open'] is not None:
                    if bar['open'] > bar['high'] or bar['open'] < bar['low']:
                        is_valid = False
                        errors.append(f"Open ({bar['open']}) out of High-Low range")
                
                if bar['close'] is not None:
                    if bar['close'] > bar['high'] or bar['close'] < bar['low']:
                        is_valid = False
                        errors.append(f"Close ({bar['close']}) out of High-Low range")

            # 4. Volume Check (Cannot be negative, can be 0)
            if bar['volume'] is not None and bar['volume'] < 0:
                is_valid = False
                errors.append(f"Negative volume: {bar['volume']}")

            if is_valid:
                valid_bars.append(bar)
            else:
                logger.warning(f"⚠️ Validation FAILED for {symbol} at {bar['timestamp']}: {', '.join(errors)}")

        return valid_bars

market_validator = MarketDataValidator()
