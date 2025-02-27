from pydantic import BaseModel, field_validator

class CompleteSpotifyRequest(BaseModel):
    username: str

    @field_validator('username')
    def validate_username(cls, v: str):
        if len(v) < 3:
            raise ValueError('must be at least 3 characters long')
        if len(v) > 20:
            raise ValueError('must be at most 20 characters long')
        if not v.replace('_', '').isalnum():
            raise ValueError('can only contain alphanumeric characters and underscores')
        return v