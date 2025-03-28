import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.providers.deezer_service import DeezerService

@pytest.fixture
def mock_http_client():
    with patch('app.services.providers.deezer_service.HTTPClient') as mock:
        yield mock

@pytest.fixture
def deezer_service():
    service = DeezerService()
    service._instance = None  # Reset singleton for testing
    return service

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_success(deezer_service):
    mock_response = {
        "id": 123456,
        "isrc": "USRC12345678"
    }
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_deezer_id_by_isrc("USRC12345678")
        
        assert result == 123456
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_no_results(deezer_service):
    mock_response = None
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_deezer_id_by_isrc("USRC12345678")
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_rate_limit(deezer_service):
    mock_response = {
        "error": {
            "type": "QuotaExceededException",
            "message": "Rate limit exceeded",
            "code": 4
        }
    }
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_deezer_id_by_isrc("USRC12345678")
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_error(deezer_service):
    mock_response = {
        "error": {
            "type": "InvalidParameterException",
            "message": "Invalid ISRC"
        }
    }
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_deezer_id_by_isrc("invalid_isrc")
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_404_error(deezer_service):
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = HTTPException(status_code=404, detail="Not found")
        
        result = await deezer_service.fetch_deezer_id_by_isrc("nonexistent_isrc")
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_deezer_id_by_isrc_other_http_error(deezer_service):
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = HTTPException(status_code=500, detail="Internal server error")
        
        with pytest.raises(HTTPException) as exc_info:
            await deezer_service.fetch_deezer_id_by_isrc("error_isrc")
        
        assert exc_info.value.status_code == 500
        mock_handle_retry.assert_called_once()

def test_validate_rate_limit_body(deezer_service):
    # Test rate limit error
    rate_limit_response = {
        "error": {
            "message": "Quota limit exceeded",
            "code": 4
        }
    }
    assert deezer_service.retry_config.validate_rate_limit_body(rate_limit_response) is True

    # Test non-rate limit error
    other_error_response = {
        "error": {
            "message": "Invalid ISRC",
            "code": 1
        }
    }
    assert deezer_service.retry_config.validate_rate_limit_body(other_error_response) is False

    # Test non-error response
    success_response = {
        "id": 123456,
        "isrc": "USRC12345678"
    }
    assert deezer_service.retry_config.validate_rate_limit_body(success_response) is False

@pytest.mark.asyncio
async def test_fetch_preview_url_by_deezer_id_success(deezer_service):
    mock_response = {
        "id": 123456,
        "preview": "https://example.com/preview.mp3"
    }
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_preview_url_by_deezer_id(123456)
        
        assert result == "https://example.com/preview.mp3"
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_preview_url_by_deezer_id_no_preview(deezer_service):
    mock_response = {
        "id": 123456,
        "preview": None
    }
    
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await deezer_service.fetch_preview_url_by_deezer_id(123456)
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_preview_url_by_deezer_id_404_error(deezer_service):
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = HTTPException(status_code=404, detail="Not found")
        
        result = await deezer_service.fetch_preview_url_by_deezer_id(999999)
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_preview_url_by_deezer_id_other_http_error(deezer_service):
    with patch('app.services.providers.deezer_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = HTTPException(status_code=500, detail="Internal server error")
        
        with pytest.raises(HTTPException) as exc_info:
            await deezer_service.fetch_preview_url_by_deezer_id(123456)
        
        assert exc_info.value.status_code == 500
        mock_handle_retry.assert_called_once() 