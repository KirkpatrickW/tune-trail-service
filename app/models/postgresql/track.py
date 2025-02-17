from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class Track(Base):
    __tablename__ = 'tracks'

    track_id = Column(Integer, primary_key=True)
    isrc = Column(String(50), unique=True)
    spotify_id = Column(String(255), unique=True)
    deezer_id = Column(String(255), unique=True)
    name = Column(String(255), nullable=False)
    artists = Column(Text, nullable=False)
    cover_small = Column(String(255))
    cover_medium = Column(String(255))
    cover_large = Column(String(255), nullable=False)
    preview_url = Column(String(255), nullable=False)

    localities = relationship("Locality", secondary="locality_tracks", back_populates="tracks")

    __table_args__ = (
        UniqueConstraint('isrc', 'spotify_id', 'deezer_id', name='unique_identifiers'),
    )
