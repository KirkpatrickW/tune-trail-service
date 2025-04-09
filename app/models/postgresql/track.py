from sqlalchemy import BigInteger, Column, Integer, String, Text, UniqueConstraint, ARRAY, CheckConstraint, Text, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Track(Base):
    __tablename__ = 'tracks'

    track_id = Column(Integer, primary_key=True)
    isrc = Column(String(50), unique=True, nullable=False)
    spotify_id = Column(String(255), unique=True, nullable=False)
    deezer_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    artists = Column(ARRAY(Text), nullable=False)
    cover_small = Column(Text)
    cover_medium = Column(Text)
    cover_large = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)

    localities = relationship("LocalityTrack", back_populates="track")

    __table_args__ = (
        UniqueConstraint('isrc', 'spotify_id', 'deezer_id', name='unique_identifiers'),
        CheckConstraint('array_length(artists, 1) > 0', name='check_artists_not_empty'),
        CheckConstraint('deezer_id > 0', name='check_deezer_id_positive')
    )
