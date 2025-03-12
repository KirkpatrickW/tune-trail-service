from fastapi import HTTPException
from fastapi import Depends
from utils.jwt_helper import decode_access_token
import contextvars

access_token_data_ctx = contextvars.ContextVar("access_token_data", default=None)

async def validate_jwt(access_token_data: dict = Depends(decode_access_token)):
    if access_token_data["is_expired"]:
        raise HTTPException(status_code=401, detail="Token has expired.")
    
    access_token_data_ctx.set(access_token_data)

    return