from pydantic import BaseModel
from .locality_input import LocalityInput
from .track_input import TrackInput

class LocalityTrackRequest(BaseModel):
    locality: LocalityInput
    track: TrackInput