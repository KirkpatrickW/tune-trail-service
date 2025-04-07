from fastapi import HTTPException
from dependencies.validate_jwt import access_token_data_ctx

async def validate_admin():
    access_token_data = access_token_data_ctx.get()

    if not access_token_data or access_token_data["payload"].get("is_admin") == False:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return