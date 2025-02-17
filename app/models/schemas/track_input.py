from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Annotated, Optional
from urllib.parse import urlparse

class TrackInput(BaseModel):
    isrc: Annotated[str, Field(pattern=r'^[A-Z]{2}[A-Z0-9]{3}\d{7}$')]
    spotify_id: Annotated[str, Field(pattern=r'^[A-Za-z0-9]{22}$')]
    deezer_id: Annotated[int, Field(gt=0)]
    name: Annotated[str, Field(min_length=1, max_length=255)]
    artists: str
    cover_small: Optional[HttpUrl] = None
    cover_medium: Optional[HttpUrl] = None
    cover_large: HttpUrl
    preview_url: Optional[HttpUrl] = None

    @field_validator('artists')
    @classmethod
    def validate_artists(cls, v: str) -> str:
        artists = [a.strip() for a in v.split(',') if a.strip()]
        if not artists:
            raise ValueError('At least one artist required')
        return ', '.join(artists)
    

    @field_validator('cover_small', 'cover_medium', 'cover_large')
    @classmethod
    def validate_image_url(cls, v: Optional[HttpUrl], info):
        if v is None and info.field_name != 'cover_large':
            return v
            
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        parsed = urlparse(str(v))
        file_ext = parsed.path.lower().split('.')[-1]
        
        if f'.{file_ext}' not in allowed_extensions:
            raise ValueError(
                f"Invalid image format for {info.field_name}. "
                f"Allowed formats: {', '.join(allowed_extensions)}"
            )
        return v
    

    @field_validator('preview_url')
    @classmethod
    def validate_audio_url(cls, v: Optional[HttpUrl]):
        if v is None:
            return v
            
        allowed_extensions = {'.mp3', '.wav', '.ogg', '.aac'}
        parsed = urlparse(str(v))
        file_ext = parsed.path.lower().split('.')[-1]
        
        if f'.{file_ext}' not in allowed_extensions:
            raise ValueError(
                f"Invalid audio format. "
                f"Allowed formats: {', '.join(allowed_extensions)}"
            )
        return v