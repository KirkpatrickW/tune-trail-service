from datetime import datetime, timedelta, timezone
import jwt

from fastapi import Security, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "tunetrail_secret"
ALGORITHM = "HS256"

http_bearer = HTTPBearer(auto_error=False)

def create_access_token(user_id: str, user_session_id: str, is_admin: bool, spotify_access_token: str = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        { 
            "user_id": user_id,
            "user_session_id": user_session_id,
            "is_admin": is_admin,
            "spotify_access_token": spotify_access_token,
            "exp": expire
        }, 
        SECRET_KEY, 
        algorithm=ALGORITHM)


async def decode_access_token(request: Request):
    authorisation: HTTPAuthorizationCredentials = await http_bearer(request)
    if not authorisation:
        raise HTTPException(status_code=403, detail="Not authenticated")

    token = authorisation.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        is_expired = False
    except jwt.ExpiredSignatureError:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        is_expired = True
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return { "is_expired": is_expired, "payload": payload }