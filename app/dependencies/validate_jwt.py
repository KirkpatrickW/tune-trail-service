from fastapi import HTTPException, Request
from utils.jwt_helper import decode_access_token
import contextvars

access_token_data_ctx = contextvars.ContextVar("access_token_data", default=None)

async def validate_jwt_allow_unauthenticated(request: Request):
    return await validate_jwt(request, allow_unauthenticated=True)


async def validate_jwt(request: Request, allow_unauthenticated: bool = False):
    try:
        access_token_data = await decode_access_token(request)
    except HTTPException as e:
        if e.status_code == 403 and allow_unauthenticated:
            return
        
        raise e

    if access_token_data["is_expired"]:
        raise HTTPException(status_code=401, detail="Token has expired.")

    access_token_data_ctx.set(access_token_data)

    return