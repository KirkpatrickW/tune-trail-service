from pydantic import BaseModel

class Bounds(BaseModel):
    north: float
    south: float
    east: float
    west: float