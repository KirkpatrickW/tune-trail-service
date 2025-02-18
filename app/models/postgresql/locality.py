from sqlalchemy import Column, Integer, String, Float, CheckConstraint, Index, Computed
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from .base import Base

class Locality(Base):
    __tablename__ = 'localities'

    locality_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geog = Column(
        Geography(geometry_type='POINT', srid=4326),
        Computed("ST_SetSRID(ST_MakePoint(latitude, longitude), 4326)", persisted=True),
        comment="Generated from coordinates"
    )

    tracks = relationship("Track", secondary="locality_tracks", back_populates="localities")

    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90'),
        CheckConstraint('longitude BETWEEN -180 AND 180'),
        Index('localities_geog_gist', geog, postgresql_using='gist'),
    )
