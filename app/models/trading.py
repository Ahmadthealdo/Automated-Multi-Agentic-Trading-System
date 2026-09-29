from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.models.base import Base

class TradingHistory(Base):
    __tablename__ = 'trading_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_name = Column(String)
    user_email = Column(String)
    user_phone = Column(String)
    ticker = Column(String)
    action = Column(String)
    risk_status = Column(String)
    stable_capital = Column(String)
    budget_allocation = Column(String)
    entry_price = Column(String)
    take_profit = Column(String)
    stop_loss = Column(String)
    justification = Column(Text)
    status = Column(String, default="RUNNING")
