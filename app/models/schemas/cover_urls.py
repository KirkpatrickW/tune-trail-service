from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
from urllib.parse import urlparse

class CoverUrls(BaseModel):
    small: Optional[HttpUrl] = None
    medium: Optional[HttpUrl] = None
    large: HttpUrl

    @field_validator('small', 'medium', 'large')
    @classmethod
    def validate_image_url(cls, v: Optional[HttpUrl], info):
        if v is None and info.field_name != 'large':
            return v

        allowed_domains = {"i.scdn.co"}
        parsed = urlparse(str(v))
        if parsed.netloc not in allowed_domains:
            raise ValueError(f"Invalid domain for {info.field_name}: {parsed.netloc}")

        return v