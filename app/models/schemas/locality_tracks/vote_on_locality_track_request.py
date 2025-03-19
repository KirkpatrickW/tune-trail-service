from enum import Enum
from pydantic import BaseModel, field_validator

class VoteValueEnum(Enum):
    UPVOTE = 1
    DOWNVOTE = -1
    UNVOTE = 0


class VoteOnTrackLocalityRequest(BaseModel):
    vote_value: VoteValueEnum

    @field_validator('vote_value')
    def validate_vote_value(cls, v):
        if v not in VoteValueEnum:
            raise ValueError('vote_value must be 1 (UPVOTE), -1 (DOWNVOTE), or 0 (UNVOTE)')
        return v
