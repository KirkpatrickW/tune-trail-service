import pytest
from fastapi import HTTPException, Request
from unittest.mock import AsyncMock, patch

from app.dependencies.validate_jwt import validate_jwt, validate_jwt_allow_unauthenticated, access_token_data_ctx

@pytest.fixture
def mock_request():
    return AsyncMock(spec=Request)

@pytest.fixture
def mock_access_token_data():
    return {
        "payload": {
            "spotify_access_token": "test_token",
            "user_id": 1
        },
        "is_expired": False
    }

@pytest.mark.asyncio
async def test_validate_jwt_success(mock_request, mock_access_token_data):
    with patch('app.dependencies.validate_jwt.decode_access_token') as mock_decode:
        mock_decode.return_value = mock_access_token_data
        
        # Should not raise any exception
        await validate_jwt(mock_request)
        
        # Verify the context was set
        assert access_token_data_ctx.get() == mock_access_token_data

@pytest.mark.asyncio
async def test_validate_jwt_expired(mock_request):
    with patch('app.dependencies.validate_jwt.decode_access_token') as mock_decode:
        mock_decode.return_value = {
            "payload": {},
            "is_expired": True
        }
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await validate_jwt(mock_request)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token has expired."

@pytest.mark.asyncio
async def test_validate_jwt_allow_unauthenticated_success(mock_request):
    with patch('app.dependencies.validate_jwt.decode_access_token') as mock_decode:
        mock_decode.side_effect = HTTPException(status_code=403, detail="Invalid token")
        
        # Should not raise any exception
        await validate_jwt_allow_unauthenticated(mock_request)

@pytest.mark.asyncio
async def test_validate_jwt_allow_unauthenticated_other_error(mock_request):
    with patch('app.dependencies.validate_jwt.decode_access_token') as mock_decode:
        mock_decode.side_effect = HTTPException(status_code=400, detail="Bad request")
        
        # Should raise the original exception
        with pytest.raises(HTTPException) as exc_info:
            await validate_jwt_allow_unauthenticated(mock_request)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Bad request" 