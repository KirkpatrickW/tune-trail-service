from pydantic import BaseModel, field_validator, model_validator

class BoundsParams(BaseModel):
    north: float
    east: float
    south: float
    west: float

    @field_validator('north', 'south')
    def validate_latitude(cls, v: float):
        if not -90 <= v <= 90:
            raise ValueError('must be between -90 and 90')
        return v

    @field_validator('east', 'west')
    def validate_longitude(cls, v: float):
        if not -180 <= v <= 180:
            raise ValueError('must be between -180 and 180')
        return v

    @model_validator(mode='after')
    def validate_north_south(cls, values):
        north = values.north
        south = values.south
        if north <= south:
            raise ValueError('north must be greater than south')
        return values

    @model_validator(mode='after')
    def validate_east_west(cls, values):
        east = values.east
        west = values.west
        if east <= west:
            raise ValueError('east must be greater than west')
        return values