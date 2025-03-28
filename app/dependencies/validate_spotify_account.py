from fastapi import HTTPException
from dependencies.validate_jwt import access_token_data_ctx

async def validate_spotify_account():
    access_token_data = access_token_data_ctx.get()

    if not access_token_data or not access_token_data["payload"].get("spotify_access_token"):
        raise HTTPException(status_code=409, detail="Spotify account must be linked")

    return