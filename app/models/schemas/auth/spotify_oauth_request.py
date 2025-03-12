from pydantic import BaseModel

class SpotifyOAuthRequest(BaseModel):
    auth_code: str
