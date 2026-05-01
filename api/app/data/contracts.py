from ib_async import Stock, Index, Contract, Option


class ContractFactory:
    """
    Central factory for creating IBKR contract objects.
    Eliminates repeated contract construction boilerplate across the codebase.
    """

    @staticmethod
    def stock(symbol: str, exchange: str = 'SMART', currency: str = 'USD') -> Stock:
        """Creates an IBKR equity/ETF contract."""
        return Stock(symbol, exchange, currency)

    @staticmethod
    def index(symbol: str, exchange: str, currency: str = 'USD') -> Index:
        """Creates an IBKR index contract."""
        return Index(symbol, exchange, currency)

    @staticmethod
    def from_config(info: dict) -> Contract:
        """
        Creates a generic IBKR contract from a config dict.

        Expected keys: symbol, secType, exchange, currency
        """
        c = Contract()
        c.symbol = info['symbol']
        c.secType = info['secType']
        c.exchange = info['exchange']
        c.currency = info['currency']
        return c

    @staticmethod
    def put_option(symbol: str, strike: float, expiry: str, exchange: str = 'SMART') -> Option:
        """Creates an IBKR put option contract.

        Args:
            symbol: Underlying symbol (e.g. 'AAPL')
            strike: Strike price
            expiry: Expiry date in YYYYMMDD format
            exchange: Option exchange — use value from reqSecDefOptParams, not 'SMART'
        """
        return Option(symbol, expiry, strike, 'P', exchange)

    @staticmethod
    def call_option(symbol: str, strike: float, expiry: str, exchange: str = 'SMART') -> Option:
        """Creates an IBKR call option contract.

        Args:
            symbol: Underlying symbol (e.g. 'AAPL')
            strike: Strike price
            expiry: Expiry date in YYYYMMDD format
            exchange: Option exchange — use value from reqSecDefOptParams, not 'SMART'
        """
        return Option(symbol, expiry, strike, 'C', exchange)
