import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from app.dependencies.validate_admin import validate_admin

@pytest.fixture
def mock_admin_token_data():
    return {
        "payload": {
            "is_admin": True,
            "user_id": 1
        }
    }

@pytest.fixture
def mock_non_admin_token_data():
    return {
        "payload": {
            "is_admin": False,
            "user_id": 1
        }
    }

@pytest.mark.asyncio
async def test_validate_admin_success(mock_admin_token_data):
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_admin_token_data
    with patch('app.dependencies.validate_admin.access_token_data_ctx', mock_ctx):
        # Should not raise any exception
        await validate_admin()

@pytest.mark.asyncio
async def test_validate_admin_insufficient_permissions(mock_non_admin_token_data):
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_non_admin_token_data
    with patch('app.dependencies.validate_admin.access_token_data_ctx', mock_ctx):
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await validate_admin()
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Insufficient permissions"

@pytest.mark.asyncio
async def test_validate_admin_no_token_data():
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = None
    with patch('app.dependencies.validate_admin.access_token_data_ctx', mock_ctx):
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await validate_admin()
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Insufficient permissions" 