from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=True)  # Nullable for incomplete profile
    hashed_password = Column(BYTEA, nullable=True)  # Nullable for OAuth-only accounts
    is_oauth_account = Column(Boolean, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user_spotify_oauth_account = relationship("UserSpotifyOauthAccount", back_populates="user", uselist=False)
    user_sessions = relationship("UserSession", back_populates="user")
    locality_tracks = relationship("LocalityTrack", back_populates="user")
    locality_track_votes = relationship("LocalityTrackVote", back_populates="user")

    __table_args__ = (
        UniqueConstraint('username', name='unique_identifiers'),
    )