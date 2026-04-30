from sqlalchemy import Column, Integer, String, Date, Boolean, Time, Text
from app.infrastructure.database import Base

class ExchangeCalendar(Base):
    __tablename__ = 'exchange_calendar'
    __table_args__ = {'schema': 'common'}

    id = Column(Integer, primary_key=True)
    exchange = Column(String, nullable=False, index=True)  # e.g., "NYSE", "NASDAQ", "BIST"
    date = Column(Date, nullable=False, index=True)
    is_open = Column(Boolean, default=True, nullable=False)
    open_time = Column(Time, nullable=True) # Override default open time if needed
    close_time = Column(Time, nullable=True) # Override default close time if needed
    note = Column(Text, nullable=True) # Reason for holiday or early close (e.g., "Christmas")

    def __repr__(self):
        return f"<ExchangeCalendar(exchange='{self.exchange}', date='{self.date}', is_open={self.is_open})>"
