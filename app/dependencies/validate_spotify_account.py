from fastapi import HTTPException
from dependencies.validate_jwt import access_token_data_ctx

async def validate_spotify_account():
    access_token_data = access_token_data_ctx.get()

    if "spotify_access_token" not in access_token_data["payload"]:
        raise HTTPException(status_code=409, detail="Spotify account must be linked.")

    return