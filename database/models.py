from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, BigInteger, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

# =============================================================================
# 1. COMMON SCHEMA (Shared Data)
# =============================================================================

class Instrument(Base):
    """
    Master table for all tradeable assets.
    Example: AAPL, BTC, EURUSD
    """
    __tablename__ = 'instruments'
    __table_args__ = {"schema": "common"}

    id = Column(Integer, primary_key=True)
    con_id = Column(Integer, unique=True, nullable=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=True)
    sector = Column(String(150), nullable=True)
    industry = Column(String(150), nullable=True)
    data_role = Column(String(50), default="TRADE")  # TRADE(AAPL, TSLA), MACRO(VIX, DXY, US10Y), ETF(XLK, XLE)
    sec_type = Column(String(10), default='STK')  # e.g., STK, OPT, FUT, CRYPTO
    currency = Column(String(5), default="USD")
    exchange = Column(String(20), default="SMART")
    last_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True))

    watchlist_items = relationship("Watchlist", back_populates="instrument")

class Watchlist(Base):
    """
    Your personalized watchlist settings.
    """
    __tablename__ = 'watchlist'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)
    priority = Column(Integer, default=0)  # Lower number = higher priority
    note = Column(Text, nullable=True)
    tags = Column(String(100), nullable=True) # TECH, GROWTH
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    instrument = relationship("Instrument", back_populates="watchlist_items")


class MarketDataCache(Base):
    """
    Historical data storage to speed up analysis.
    Stores OHLCV (Open, High, Low, Close, Volume) data.
    """
    __tablename__ = 'market_data_cache'
    __table_args__ = {'schema': 'common'}

    id = Column(BigInteger, primary_key=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)

    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

    # Useful to know which timeframe this data belongs to (e.g., '1min', '1hour', '1day')
    timeframe = Column(String(10), nullable=False)

class FundamentalCache(Base):
    """
    Company fundamentals stored for quick access.
    Generally stored daily.
    """
    __tablename__ = 'fundamental_cache'
    __table_args__ = {'schema': 'common'}

    id = Column(BigInteger, primary_key=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)

    pe_ratio = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    div_yield = Column(Float, nullable=True)

    # Store additional fundamental data as JSON
    # {"roe": 15.2, "debt_to_equity": 0.5, "sector_avg_pe": 20.1}
    details = Column(JSON, nullable=True)

class SystemLog(Base):
    """
    Application logs stored in DB for easy display in UI.
    """
    __tablename__ = 'system_logs'
    __table_args__ = {'schema': 'common'}

    id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String(10))  # INFO, WARNING, ERROR
    module = Column(String(50)) # e.g., 'IB_Connection', 'Strategy_Bot'
    message = Column(Text)

# =============================================================================
# 2. ABSTRACT TABLES (Templates for Paper/Live)
# =============================================================================

class OrderMixin:
    """
    Template for Orders. 
    Both Paper and Live schemas will use this structure.
    """
    id = Column(BigInteger, primary_key=True)
    ib_order_id = Column(Integer)
    symbol = Column(String(20))
    action = Column(String(4)) # BUY / SELL
    total_quantity = Column(Float)
    order_type = Column(String(10)) # LMT, MKT
    lmt_price = Column(Float, nullable=True)
    status = Column(String(20)) # Filled, Submitted, Cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PositionMixin:
    """
    Template for Positions.
    """
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    position = Column(Float) # Number of shares (+ Long, - Short)
    avg_cost = Column(Float)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

# =============================================================================
# 3. PAPER TRADING SCHEMA
# =============================================================================
class PaperOrder(OrderMixin, Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'paper'}

class PaperPosition(PositionMixin, Base):
    __tablename__ = 'positions'
    __table_args__ = {'schema': 'paper'}

# =============================================================================
# 4. LIVE TRADING SCHEMA (PROD)
# =============================================================================
class LiveOrder(OrderMixin, Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'live'}

class LivePosition(PositionMixin, Base):
    __tablename__ = 'positions'
    __table_args__ = {'schema': 'live'}

# =============================================================================
# DATABASE SETUP FUNCTION
# =============================================================================
def init_db():
    from sqlalchemy import text

    engine = create_engine("postgresql://postgres@localhost:5432/analystfolio_db")

    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS common"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS paper"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS live"))
        conn.commit()
    
    Base.metadata.create_all(engine)
    print("✅ Database schemas and tables created successfully.")

    return engine