from sqlalchemy import Column, Integer, SmallInteger, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from .base import Base
from sqlalchemy.sql import func

class LocalityTrackVote(Base):
    __tablename__ = 'locality_track_votes'

    locality_track_id = Column(Integer, ForeignKey('locality_tracks.locality_track_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    vote = Column(SmallInteger, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    locality_track = relationship("LocalityTrack", back_populates="locality_track_votes", passive_deletes=True)
    user = relationship("User", back_populates="locality_track_votes", passive_deletes=True)