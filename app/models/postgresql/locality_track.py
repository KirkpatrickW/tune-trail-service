from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class LocalityTrack(Base):
    __tablename__ = 'locality_tracks'

    locality_id = Column(Integer, ForeignKey('localities.locality_id', ondelete='CASCADE'), primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.track_id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)

    user = relationship("User", back_populates="locality_tracks")