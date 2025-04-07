from sqlalchemy import Column, BigInteger, String, Float, CheckConstraint, Index, Computed, Integer, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from .base import Base

class Locality(Base):
    __tablename__ = 'localities'

    locality_id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geog = Column(
        Geography(geometry_type='POINT', srid=4326),
        Computed("ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)", persisted=True),
        comment="Generated from coordinates"
    )
    total_tracks = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tracks = relationship("LocalityTrack", back_populates="locality")

    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90'),
        CheckConstraint('longitude BETWEEN -180 AND 180'),
        Index('localities_geog_gist', geog, postgresql_using='gist'),
    )