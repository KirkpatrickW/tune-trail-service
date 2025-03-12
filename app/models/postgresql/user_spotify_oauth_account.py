from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from .base import Base

class UserSpotifyOauthAccount(Base):
    __tablename__ = 'user_spotify_oauth_accounts'

    user_spotify_oauth_account_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    provider_user_id = Column(String(255), nullable=False, unique=True)
    encrypted_access_token = Column(Text)
    encrypted_refresh_token = Column(Text)
    access_token_expires_at = Column(TIMESTAMP(timezone=True))
    subscription = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_spotify_oauth_account")

    __table_args__ = (
        UniqueConstraint('provider_user_id', 'user_id', name='unique_identifiers'),
    )