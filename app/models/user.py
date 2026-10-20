from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.models.base import Base

class SystemUser(Base):
    __tablename__ = 'system_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    verified_phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
