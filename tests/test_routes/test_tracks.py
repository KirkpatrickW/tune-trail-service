import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler

# Patch the services before importing the app
with patch('app.services.providers.spotify_service.SpotifyService') as mock_spotify:
    with patch('app.services.providers.deezer_service.DeezerService') as mock_deezer:
        from app.main import app
        from app.routes.tracks import spotify_service, deezer_service

@pytest.fixture
def mock_spotify_service():
    instance = AsyncMock()
    instance.search_tracks = AsyncMock()
    instance.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "external_ids": {"isrc": "TEST12345678"},
                    "album": {
                        "images": [
                            {"url": "large_url", "width": 640},
                            {"url": "medium_url", "width": 300},
                            {"url": "small_url", "width": 64}
                        ]
                    }
                }
            ],
            "total": 1
        }
    }
    spotify_service.search_tracks = instance.search_tracks
    yield instance

@pytest.fixture
def mock_deezer_service():
    instance = AsyncMock()
    instance.fetch_deezer_id_by_isrc = AsyncMock()
    instance.fetch_deezer_id_by_isrc.return_value = "deezer_track_1"
    deezer_service.fetch_deezer_id_by_isrc = instance.fetch_deezer_id_by_isrc
    yield instance

@pytest.fixture
def test_client():
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FastAPICache.init(InMemoryBackend())

    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)

    client = TestClient(app, raise_server_exceptions=False)
    return client

@pytest.fixture(autouse=True)
async def cleanup_cache():
    try:
        yield
    finally:
        from fastapi_cache import FastAPICache
        await FastAPICache.clear()

def test_search_tracks_success(test_client, mock_spotify_service, mock_deezer_service):
    response = test_client.get("/tracks/search?q=test&offset=0")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["spotify_id"] == "spotify_track_1"
    assert data["results"][0]["deezer_id"] == "deezer_track_1"
    assert data["results"][0]["isrc"] == "TEST12345678"
    assert data["results"][0]["name"] == "Test Track 1"
    assert data["results"][0]["artists"] == ["Test Artist 1"]
    assert data["results"][0]["cover"]["large"] == "large_url"
    assert data["results"][0]["cover"]["medium"] == "medium_url"
    assert data["results"][0]["cover"]["small"] == "small_url"
    assert data["next_offset"] == 20
    assert data["total_matching_results"] == 1

    # Verify service calls
    mock_spotify_service.search_tracks.assert_called_once_with("test", 0, 20)
    mock_deezer_service.fetch_deezer_id_by_isrc.assert_called_once_with("TEST12345678")

def test_search_tracks_no_isrc(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify response with no ISRC
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "external_ids": {},  # No ISRC
                    "album": {
                        "images": [
                            {"url": "large_url", "width": 640},
                            {"url": "medium_url", "width": 300},
                            {"url": "small_url", "width": 64}
                        ]
                    }
                }
            ],
            "total": 1
        }
    }

    response = test_client.get("/tracks/search?q=test&offset=0")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0  # No results because track has no ISRC
    assert data["next_offset"] == 21  # Incremented because we skipped one track
    assert data["total_matching_results"] == 1

    # Verify service calls
    mock_spotify_service.search_tracks.assert_called_once_with("test", 0, 20)
    mock_deezer_service.fetch_deezer_id_by_isrc.assert_not_called()

def test_search_tracks_no_deezer_id(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify response
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "external_ids": {"isrc": "TEST12345678"},
                    "album": {
                        "images": [
                            {"url": "large_url", "width": 640},
                            {"url": "medium_url", "width": 300},
                            {"url": "small_url", "width": 64}
                        ]
                    }
                }
            ],
            "total": 1
        }
    }

    # Mock Deezer response with no ID
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = None

    response = test_client.get("/tracks/search?q=test&offset=0")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0  # No results because track has no Deezer ID
    assert data["next_offset"] == 21  # Incremented because we skipped one track
    assert data["total_matching_results"] == 1

    # Verify service calls
    mock_spotify_service.search_tracks.assert_called_once_with("test", 0, 20)
    mock_deezer_service.fetch_deezer_id_by_isrc.assert_called_once_with("TEST12345678")

def test_search_tracks_empty_query(test_client):
    response = test_client.get("/tracks/search?q=&offset=0")
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"][0]["msg"] == "Value error, must not be empty or only whitespace"

def test_search_tracks_whitespace_query(test_client):
    response = test_client.get("/tracks/search?q=   &offset=0")
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"][0]["msg"] == "Value error, must not be empty or only whitespace"