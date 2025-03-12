from pydantic import BaseModel, field_validator

class SearchTracksParams(BaseModel):
    q: str
    offset: int = 0

    @field_validator("q")
    def validate_q(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or only whitespace")
        return v