from sqlalchemy import Column, BigInteger, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class LocalityTrack(Base):
    __tablename__ = 'locality_tracks'

    locality_track_id = Column(Integer, primary_key=True, autoincrement=True)
    locality_id = Column(BigInteger, ForeignKey('localities.locality_id', ondelete='CASCADE'), nullable=False)
    track_id = Column(Integer, ForeignKey('tracks.track_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    total_votes = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    locality = relationship("Locality", back_populates="tracks")
    track = relationship("Track", back_populates="localities")
    user = relationship("User", back_populates="locality_tracks")
    locality_track_votes = relationship("LocalityTrackVote", back_populates="locality_track")
