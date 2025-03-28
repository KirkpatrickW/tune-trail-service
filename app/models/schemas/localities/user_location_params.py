from pydantic import BaseModel, field_validator, model_validator, ValidationError

class UserLocationParams(BaseModel):
    latitude: float
    longitude: float
    radius: float

    @field_validator('latitude')
    def validate_latitude(cls, v: float):
        if not -90 <= v <= 90:
            raise ValueError('must be between -90 and 90')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v: float):
        if not -180 <= v <= 180:
            raise ValueError('must be between -180 and 180')
        return v

    @field_validator('radius')
    def validate_radius(cls, v: float):
        if v < 100:
            raise ValueError('must be greater than 100 meters')
        if v > 10000:
            raise ValueError('must be less than or equal to 10,000 meters')
        return v