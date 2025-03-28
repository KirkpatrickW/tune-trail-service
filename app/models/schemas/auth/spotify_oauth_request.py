from pydantic import BaseModel, field_validator

class SpotifyOAuthRequest(BaseModel):
    auth_code: str

    @field_validator('auth_code')
    def validate_auth_code(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('must not be empty')
        return v
