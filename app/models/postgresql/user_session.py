from sqlalchemy import Column, Integer, Boolean, ForeignKey, TIMESTAMP, func, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from .base import Base

class UserSession(Base):
    __tablename__ = 'user_sessions'

    user_session_id = Column(pgUUID, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_invalidated = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="user_sessions", passive_deletes=True)