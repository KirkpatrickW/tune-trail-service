from pydantic import BaseModel, Field
from typing import Annotated

OVERPASS_MAX_ID = 2**64 - 1

class LocalityInput(BaseModel):
    locality_id: Annotated[int, Field(gt=1, le=OVERPASS_MAX_ID, description="Valid Overpass API ID (64-bit unsigned integer)")]
    name: Annotated[str, Field(min_length=2, max_length=255)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]