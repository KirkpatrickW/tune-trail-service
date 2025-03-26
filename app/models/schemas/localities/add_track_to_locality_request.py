from pydantic import BaseModel, field_validator

class AddTrackToLocalityRequest(BaseModel):
    locality_id: int
    spotify_track_id: str

    @field_validator('spotify_track_id')
    def validate_spotify_track_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('must not be empty')
        return v