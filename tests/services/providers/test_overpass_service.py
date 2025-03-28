import pytest
from unittest.mock import AsyncMock, patch

from app.services.providers.overpass_service import OverpassService

@pytest.fixture
def mock_http_client():
    with patch('app.services.providers.overpass_service.HTTPClient') as mock:
        yield mock

@pytest.fixture
def overpass_service():
    service = OverpassService()
    service._instance = None  # Reset singleton for testing
    return service

@pytest.mark.asyncio
async def test_get_localities_by_bounds_success(overpass_service):
    mock_response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.8566,
                "lon": 2.3522,
                "tags": {
                    "name": "Paris",
                    "place": "city"
                }
            },
            {
                "id": 2,
                "lat": 51.5074,
                "lon": -0.1278,
                "tags": {
                    "name": "London",
                    "place": "city"
                }
            }
        ]
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_localities_by_bounds(48.8566, 2.3522, 51.5074, -0.1278)
        
        assert len(result) == 2
        assert result[0] == {
            "locality_id": 1,
            "name": "Paris",
            "latitude": 48.8566,
            "longitude": 2.3522
        }
        assert result[1] == {
            "locality_id": 2,
            "name": "London",
            "latitude": 51.5074,
            "longitude": -0.1278
        }
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_localities_by_bounds_no_results(overpass_service):
    mock_response = {
        "elements": []
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_localities_by_bounds(0, 0, 0, 0)
        
        assert len(result) == 0
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_localities_by_bounds_missing_name(overpass_service):
    mock_response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.8566,
                "lon": 2.3522,
                "tags": {
                    "place": "city"
                }
            }
        ]
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_localities_by_bounds(0, 0, 0, 0)
        
        assert len(result) == 0
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_locality_by_id_success(overpass_service):
    mock_response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.8566,
                "lon": 2.3522,
                "tags": {
                    "name": "Paris",
                    "place": "city"
                }
            }
        ]
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_locality_by_id(1)
        
        assert result == {
            "locality_id": 1,
            "name": "Paris",
            "latitude": 48.8566,
            "longitude": 2.3522
        }
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_locality_by_id_not_found(overpass_service):
    mock_response = {
        "elements": []
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_locality_by_id(999)
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_locality_by_id_missing_name(overpass_service):
    mock_response = {
        "elements": [
            {
                "id": 1,
                "lat": 48.8566,
                "lon": 2.3522,
                "tags": {
                    "place": "city"
                }
            }
        ]
    }
    
    with patch('app.services.providers.overpass_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await overpass_service.get_locality_by_id(1)
        
        assert result is None
        mock_handle_retry.assert_called_once() 