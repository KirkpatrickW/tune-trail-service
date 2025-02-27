from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
import jwt

SECRET_KEY = "tunetrail_secret"
ALGORITHM = "HS256"

def create_access_token(user_id: str, user_session_id: str, spotify_access_token: str = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        { 
            "user_id": user_id,
            "user_session_id": user_session_id,
            "spotify_access_token": spotify_access_token,
            "exp": expire
        }, 
        SECRET_KEY, 
        algorithm=ALGORITHM)


def decode_access_token(authorization: HTTPAuthorizationCredentials = Security(HTTPBearer()), token_override: str | None = None):
    token = token_override if token_override else authorization.credentials
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        is_expired = False
    except jwt.ExpiredSignatureError:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        is_expired = True
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return { "is_expired": is_expired, "payload": payload }