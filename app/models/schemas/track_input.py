from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Annotated, Optional, List
from urllib.parse import urlparse
from .cover_urls import CoverUrls

class TrackInput(BaseModel):
    isrc: Annotated[str, Field(pattern=r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$')]
    spotify_id: Annotated[str, Field(pattern=r'^[A-Za-z0-9]{22}$')]
    deezer_id: Annotated[int, Field(gt=0)]
    name: Annotated[str, Field(min_length=1, max_length=255)]
    artists: Annotated[List[str], Field(min_length=1)]
    cover: CoverUrls
    preview_url: Optional[HttpUrl] = None

    @field_validator('preview_url')
    @classmethod
    def validate_audio_url(cls, v: Optional[HttpUrl]):
        if v is None:
            return v

        allowed_domains = {"cdnt-preview.dzcdn.net"}
        parsed = urlparse(str(v))
        if parsed.netloc not in allowed_domains:
            raise ValueError(f"Invalid domain for audio: {parsed.netloc}")

        return v