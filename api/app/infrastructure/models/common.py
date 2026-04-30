from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, ForeignKey, BigInteger, Text, PrimaryKeyConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.infrastructure.database import Base

# =============================================================================
# SCHEMA: COMMON
# =============================================================================

class Instrument(Base):
    __tablename__ = 'instruments'
    __table_args__ = {"schema": "common"}

    id = Column(Integer, primary_key=True)
    con_id = Column(Integer, unique=True, nullable=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=True)
    sector = Column(String(150), nullable=True)
    industry = Column(String(150), nullable=True)
    data_role = Column(String(50), default="TRADE") 
    sec_type = Column(String(10), default='STK')
    currency = Column(String(5), default="USD")
    exchange = Column(String(20), default="SMART")
    last_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) # Auto-update added
    watchlist_items = relationship("Watchlist", back_populates="instrument")
    signals = relationship("TradeSignal", back_populates="instrument")


class Watchlist(Base):
    __tablename__ = 'watchlist'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)
    priority = Column(Integer, default=0)
    note = Column(Text, nullable=True)
    tags = Column(String(100), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    instrument = relationship("Instrument", back_populates="watchlist_items")


class MarketDataCache(Base):
    __tablename__ = 'market_data_cache'
    __table_args__ = (
        PrimaryKeyConstraint('instrument_id', 'timestamp', 'timeframe'),
        {'schema': 'common'}
    )

    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String(10), nullable=False) 

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

    ma_50 = Column(Float, nullable=True)
    ma_200 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    daily_return = Column(Float, nullable=True)


class FundamentalCache(Base):
    __tablename__ = 'fundamental_cache'
    __table_args__ = {'schema': 'common'}

    id = Column(BigInteger, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'), nullable=False)
    date = Column(Date, nullable=False)

    pe_ratio = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    div_yield = Column(Float, nullable=True)
    price_to_book = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    roic = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    recommendation_mean = Column(Float, nullable=True)
    current_iv = Column(Float, nullable=True)
    iv_rank = Column(Float, nullable=True)

    # --- New Metrics ---
    debt_to_equity = Column(Float, nullable=True)
    revenue_growth = Column(Float, nullable=True)
    price_to_sales = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)
    inst_ownership = Column(Float, nullable=True) # Percentage held by institutions
    inst_count = Column(Integer, nullable=True)     # Number of institutions
    operating_cash_flow = Column(BigInteger, nullable=True) 

    fundamental_score = Column(Float, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)


class MarketSentiment(Base):
    __tablename__ = 'market_sentiment'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # --- Key Indicators ---
    vix = Column(Float, nullable=True)           # Volatility Index
    us10y = Column(Float, nullable=True)         # US 10 Year Treasury Yield
    dxy = Column(Float, nullable=True)           # US Dollar Index
    put_call_ratio = Column(Float, nullable=True) # CBOE Put/Call Ratio
    
    # --- Major Indices & Assets (Prices) ---
    spx = Column(Float, nullable=True)           # S&P 500
    ndx = Column(Float, nullable=True)           # NASDAQ 100
    dax = Column(Float, nullable=True)           # DAX 40 (Europe)
    btc_usd = Column(Float, nullable=True)       # Bitcoin
    xau_usd = Column(Float, nullable=True)       # Gold

    # --- Calculated Sentiment ---
    risk_score = Column(Integer, default=50)     # 0 (Extreme Fear) - 100 (Extreme Greed)
    sentiment_label = Column(String(50))         # e.g. "Fear", "Neutral", "Greed"
    is_trading_allowed = Column(Boolean, default=True) # Master switch for other bots
    
    # Details used in calculation (e.g., SPX MA200 value etc.)
    details = Column(JSON, nullable=True)