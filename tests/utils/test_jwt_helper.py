import pytest
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from app.utils.jwt_helper import create_access_token, decode_access_token
import jwt

def test_create_access_token():
    # Test token creation with all parameters
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = True
    spotify_access_token = "spotify_token_123"
    
    token = create_access_token(user_id, user_session_id, is_admin, spotify_access_token)
    
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_without_spotify():
    # Test token creation without spotify token
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = False
    
    token = create_access_token(user_id, user_session_id, is_admin)
    
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_with_empty_spotify():
    # Test token creation with empty spotify token
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = False
    
    token = create_access_token(user_id, user_session_id, is_admin, "")
    
    assert isinstance(token, str)
    assert len(token) > 0

def test_create_access_token_with_none_spotify():
    # Test token creation with None spotify token
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = False
    
    token = create_access_token(user_id, user_session_id, is_admin, None)
    
    assert isinstance(token, str)
    assert len(token) > 0

@pytest.mark.asyncio
async def test_decode_access_token_success():
    # Create a valid token
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = True
    token = create_access_token(user_id, user_session_id, is_admin)
    
    # Mock the request and credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = token
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        result = await decode_access_token(MagicMock(spec=Request))
        
        assert isinstance(result, dict)
        assert "is_expired" in result
        assert "payload" in result
        assert result["payload"]["user_id"] == user_id
        assert result["payload"]["user_session_id"] == user_session_id
        assert result["payload"]["is_admin"] == is_admin
        assert not result["is_expired"]
        assert "exp" in result["payload"]
        assert isinstance(result["payload"]["exp"], int)

@pytest.mark.asyncio
async def test_decode_access_token_no_auth():
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await decode_access_token(MagicMock(spec=Request))
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Not authenticated"

@pytest.mark.asyncio
async def test_decode_access_token_invalid():
    # Mock request with invalid token
    mock_credentials = MagicMock()
    mock_credentials.credentials = "invalid_token"
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        with pytest.raises(HTTPException) as exc_info:
            await decode_access_token(MagicMock(spec=Request))
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

@pytest.mark.asyncio
async def test_decode_access_token_expired():
    # Create an expired token by manually creating one with a past expiration
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = True
    
    # Create a token with expiration in the past
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {
        "user_id": user_id,
        "user_session_id": user_session_id,
        "is_admin": is_admin,
        "exp": expire
    }
    
    # Manually create an expired token
    token = jwt.encode(payload, "tunetrail_secret", algorithm="HS256")
    
    # Mock the request and credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = token
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        result = await decode_access_token(MagicMock(spec=Request))
        
        assert result["is_expired"] is True
        assert result["payload"]["user_id"] == user_id
        assert result["payload"]["user_session_id"] == user_session_id
        assert result["payload"]["is_admin"] == is_admin

@pytest.mark.asyncio
async def test_decode_access_token_malformed():
    # Mock request with malformed token (not a valid JWT)
    mock_credentials = MagicMock()
    mock_credentials.credentials = "not.a.valid.jwt"
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        with pytest.raises(HTTPException) as exc_info:
            await decode_access_token(MagicMock(spec=Request))
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

@pytest.mark.asyncio
async def test_decode_access_token_empty():
    # Mock request with empty token
    mock_credentials = MagicMock()
    mock_credentials.credentials = ""
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        with pytest.raises(HTTPException) as exc_info:
            await decode_access_token(MagicMock(spec=Request))
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token"

@pytest.mark.asyncio
async def test_decode_access_token_with_spotify():
    # Test decoding a token that includes a Spotify token
    user_id = "test_user_123"
    user_session_id = "session_123"
    is_admin = False
    spotify_token = "spotify_token_123"
    
    token = create_access_token(user_id, user_session_id, is_admin, spotify_token)
    
    # Mock the request and credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = token
    
    with patch('app.utils.jwt_helper.http_bearer', new_callable=AsyncMock) as mock_bearer:
        mock_bearer.return_value = mock_credentials
        
        result = await decode_access_token(MagicMock(spec=Request))
        
        assert result["payload"]["spotify_access_token"] == spotify_token
        assert not result["is_expired"] 