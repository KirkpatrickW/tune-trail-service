from pydantic import BaseModel

class SpotifyOAuthRequest(BaseModel):
    code: str
    redirect_uri: str
