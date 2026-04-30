from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, BigInteger, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from app.infrastructure.database import Base

# =============================================================================
# SCHEMA: COMMON (Signals)
# =============================================================================

class TradeSignal(Base):
    __tablename__ = 'trade_signals'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey('common.instruments.id'))
    bot_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    signal_price = Column(Float)
    support_level = Column(Float)
    resistance_level = Column(Float)
    reason = Column(String)
    signal_data = Column(JSON, nullable=True)
    
    score = Column(Float, default=0.0)
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    buy_price = Column(Float, nullable=True)
    sell_price = Column(Float, nullable=True)
    status = Column(String, default="OPEN")
    
    instrument = relationship("app.infrastructure.models.common.Instrument", back_populates="signals")

class PremiumWatchlist(Base):
    __tablename__ = 'premium_watchlist'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    source = Column(String(20), default="Auto") # 'Auto' or 'Manual'
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    fundamental_score = Column(Float, nullable=True)
    current_state = Column(String(20), default="Watching") # 'Watching', 'Alert', 'Action'
    is_active = Column(Boolean, default=True) # Soft delete flag

# =============================================================================
# ABSTRACT MIXINS (Templates)
# =============================================================================

class OrderMixin:
    """Common template for Live and Paper tables"""
    id = Column(BigInteger, primary_key=True)
    ib_order_id = Column(Integer)
    symbol = Column(String(20))
    action = Column(String(4)) # BUY / SELL
    total_quantity = Column(Float)
    order_type = Column(String(10)) # LMT, MKT
    lmt_price = Column(Float, nullable=True)
    status = Column(String(20)) # Filled, Submitted
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PositionMixin:
    """Common template for Live and Paper positions"""
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    position = Column(Float)
    avg_cost = Column(Float)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# SCHEMA: PAPER
# =============================================================================

class PaperOrder(OrderMixin, Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'paper'}

class PaperPosition(PositionMixin, Base):
    __tablename__ = 'positions'
    __table_args__ = {'schema': 'paper'}


# =============================================================================
# SCHEMA: LIVE
# =============================================================================

class LiveOrder(OrderMixin, Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'live'}

class LivePosition(PositionMixin, Base):
    __tablename__ = 'positions'
    __table_args__ = {'schema': 'live'}