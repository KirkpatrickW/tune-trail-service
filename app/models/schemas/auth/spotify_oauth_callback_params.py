from pydantic import BaseModel, model_validator
from enum import Enum

class SpotifyOAuthType(str, Enum):
    CONNECT = "connect"
    LINK = "link"

class SpotifyOAuthCallbackParams(BaseModel):
    code: str
    state: str
    type: SpotifyOAuthType
    jwt_token: str | None

    @model_validator(mode='before')
    def validate_state(cls, values):
        state = values.get("state")
        if state:
            parts = state.split("|")
            if len(parts) != 2:
                raise ValueError("invalid format. Expected 'type|jwt_token'")
            values["type"] = SpotifyOAuthType(parts[0])
            values["jwt_token"] = parts[1] if parts[1] != "None" else None
        return values
