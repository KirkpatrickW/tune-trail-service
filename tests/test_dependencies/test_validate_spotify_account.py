import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from app.dependencies.validate_spotify_account import validate_spotify_account

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
async def test_validate_spotify_account_success(mock_access_token_data):
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_access_token_data
    with patch('app.dependencies.validate_spotify_account.access_token_data_ctx', mock_ctx):
        # Should not raise any exception
        await validate_spotify_account()

@pytest.mark.asyncio
async def test_validate_spotify_account_no_token():
    data = {
        "payload": {
            "user_id": 1
        },
        "is_expired": False
    }
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = data
    with patch('app.dependencies.validate_spotify_account.access_token_data_ctx', mock_ctx):
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await validate_spotify_account()
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Spotify account must be linked."

@pytest.mark.asyncio
async def test_validate_spotify_account_no_context():
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = None
    with patch('app.dependencies.validate_spotify_account.access_token_data_ctx', mock_ctx):
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await validate_spotify_account()
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Spotify account must be linked." 