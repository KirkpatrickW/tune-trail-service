import re
from pydantic import BaseModel, field_validator, ValidationInfo
from typing import List
from urllib.parse import urlparse

OVERPASS_MAX_ID = 2**64 - 1

class CoverUrls(BaseModel):
    small: str = None
    medium: str = None
    large: str

    @field_validator('small', 'medium', 'large')
    def validate_image_url(cls, v: str, info: ValidationInfo):
        if v is None and info.field_name != 'large':
            return v

        allowed_domains = {"i.scdn.co"}
        parsed = urlparse(v)
        if parsed.netloc not in allowed_domains:
            raise ValueError(f"invalid domain. Allowed domains: {allowed_domains}")

        return v


class TrackInput(BaseModel):
    isrc: str
    spotify_id: str
    deezer_id: int
    name: str
    artists: List[str]
    cover: CoverUrls
    preview_url: str = None

    @field_validator('isrc')
    def validate_isrc(cls, v: str):
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$', v):
            raise ValueError("invalid ISRC format")
        return v

    @field_validator('spotify_id')
    def validate_spotify_id(cls, v: str):
        if not re.match(r'^[A-Za-z0-9]{22}$', v):
            raise ValueError("invalid Spotify ID format")
        return v

    @field_validator('deezer_id')
    def validate_deezer_id(cls, v: int):
        if v <= 0:
            raise ValueError("must be greater than 0")
        return v

    @field_validator('name')
    def validate_name(cls, v: str):
        if len(v) < 1 or len(v) > 255:
            raise ValueError("must be between 1 and 255 characters")
        return v

    @field_validator('artists')
    def validate_artists(cls, v: List[str]):
        if len(v) < 1:
            raise ValueError("at least one artist must be provided")
        return v

    @field_validator('preview_url')
    def validate_audio_url(cls, v: str):
        if v is None:
            return v

        allowed_domains = {"cdnt-preview.dzcdn.net"}
        parsed = urlparse(v)
        if parsed.netloc not in allowed_domains:
            raise ValueError(f"invalid domain. Allowed domains: {allowed_domains}")

        return v

class LocalityInput(BaseModel):
    locality_id: int
    name: str
    latitude: float
    longitude: float

    @field_validator('locality_id')
    def validate_locality_id(cls, v: int):
        if v <= 1 or v > OVERPASS_MAX_ID:
            raise ValueError(f"must be greater than 1 and less than or equal to {OVERPASS_MAX_ID}")
        return v

    @field_validator('name')
    def validate_name(cls, v: str):
        if len(v) < 2 or len(v) > 255:
            raise ValueError("must be between 2 and 255 characters")
        return v

    @field_validator('latitude')
    def validate_latitude(cls, v: float):
        if v < -90 or v > 90:
            raise ValueError("must be between -90 and 90")
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v: float):
        if v < -180 or v > 180:
            raise ValueError("must be between -180 and 180")
        return v


class LocalityTrackRequest(BaseModel):
    locality: LocalityInput
    track: TrackInput