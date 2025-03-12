from pydantic import BaseModel

class AddTrackToLocalityRequest(BaseModel):
    locality_id: int
    spotify_track_id: str