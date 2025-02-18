from typing import Annotated
from pydantic import BaseModel, Field, model_validator

class BoundsRequest(BaseModel):
    north: Annotated[float, Field(ge=-90, le=90, description="Northern boundary latitude (must be ≥ -90 and ≤ 90)")]
    south: Annotated[float, Field(ge=-90, le=90, description="Southern boundary latitude (must be ≥ -90 and ≤ 90)")]
    east: Annotated[float, Field(ge=-180, le=180, description="Eastern boundary longitude (must be ≥ -180 and ≤ 180)")]
    west: Annotated[float, Field(ge=-180, le=180, description="Western boundary longitude (must be ≥ -180 and ≤ 180)")]

    @model_validator(mode="after")
    def check_bounds_logic(self):
        if self.north <= self.south:
            raise ValueError("'north' must be greater than 'south'")
        if self.east <= self.west:
            raise ValueError("'east' must be greater than 'west'")
        return self