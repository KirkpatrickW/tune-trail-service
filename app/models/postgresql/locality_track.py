from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class LocalityTrack(Base):
    __tablename__ = 'locality_tracks'

    locality_id = Column(Integer, ForeignKey('localities.locality_id', ondelete='CASCADE'), primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.track_id', ondelete='CASCADE'), primary_key=True)