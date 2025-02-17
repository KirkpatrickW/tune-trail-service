from pydantic import BaseModel
from .locality_input import LocalityInput
from .track_input import TrackInput

class TrackLocalityRequest(BaseModel):
    locality: LocalityInput
    track: TrackInput