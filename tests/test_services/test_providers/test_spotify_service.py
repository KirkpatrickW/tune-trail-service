import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.services.providers.spotify_service import SpotifyService

@pytest.fixture
def mock_http_client():
    with patch('app.services.providers.spotify_service.HTTPClient') as mock:
        yield mock

@pytest.fixture
def mock_user_service():
    with patch('app.services.providers.spotify_service.UserService') as mock:
        yield mock

@pytest.fixture
def mock_user_spotify_oauth_account_service():
    with patch('app.services.providers.spotify_service.UserSpotifyOAuthAccountService') as mock:
        yield mock

@pytest.fixture
def mock_user_session_service():
    with patch('app.services.providers.spotify_service.UserSessionService') as mock:
        yield mock

@pytest.fixture
def spotify_service():
    service = SpotifyService()
    service._instance = None  # Reset singleton for testing
    return service

@pytest.mark.asyncio
async def test_fetch_app_access_token_success(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    mock_response = {
        "access_token": "test_token",
        "expires_in": 3600
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await spotify_service.fetch_app_access_token()
        
        assert result == "test_token"
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_app_access_token_cached(spotify_service):
    mock_response = {
        "access_token": "test_token",
        "expires_in": 3600
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        # First call to set the cache
        await spotify_service.fetch_app_access_token()
        
        # Reset the mock to verify it's not called again
        mock_handle_retry.reset_mock()
        
        # Second call should use cache
        result = await spotify_service.fetch_app_access_token()
        
        assert result == "test_token"
        mock_handle_retry.assert_not_called()  # Should not be called again

@pytest.mark.asyncio
async def test_fetch_app_access_token_error(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = HTTPException(status_code=500, detail="API Error")
        
        with pytest.raises(RuntimeError) as exc_info:
            await spotify_service.fetch_app_access_token()
        
        assert str(exc_info.value) == "Failed to obtain Spotify app access token."
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_and_handle_oauth_token_success(spotify_service):
    mock_token_response = {
        "access_token": "test_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "scope": "user-read-email"
    }
    mock_profile_response = {
        "id": "test_user_id",
        "product": "premium"
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = [mock_token_response, mock_profile_response]
        
        result = await spotify_service.fetch_and_handle_oauth_token("test_code")
        
        assert result == {
            "provider_user_id": "test_user_id",
            "subscription": "premium",
            "access_token": "test_token",
            "refresh_token": "test_refresh_token",
            "expires_in_seconds": 3600
        }
        assert mock_handle_retry.call_count == 2  # Called for both token and user profile

@pytest.mark.asyncio
async def test_renew_user_access_token_success(spotify_service):
    mock_token_response = {
        "access_token": "new_token",
        "expires_in": 3600,
        "scope": "user-read-email"
    }
    mock_profile_response = {
        "id": "test_user_id",
        "product": "premium"
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.side_effect = [mock_token_response, mock_profile_response]
        
        result = await spotify_service.renew_user_access_token("test_refresh_token")
        
        assert result == {
            "access_token": "new_token",
            "expires_in_seconds": 3600,
            "subscription": "premium"
        }
        assert mock_handle_retry.call_count == 2  # Called for both token and user profile

@pytest.mark.asyncio
async def test_get_user_profile_success(spotify_service):
    mock_response = {
        "id": "test_user_id",
        "display_name": "Test User",
        "email": "test@example.com",
        "product": "premium"
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry:
        mock_handle_retry.return_value = mock_response
        
        result = await spotify_service.get_user_profile("test_token")
        
        assert result == mock_response
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_search_tracks_success(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    mock_token_response = {
        "access_token": "test_token",
        "expires_in": 3600
    }
    mock_search_response = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Test Track",
                    "artists": [{"name": "Test Artist"}],
                    "external_ids": {"isrc": "test_isrc"},
                    "album": {
                        "images": [
                            {"url": "large.jpg", "width": 640},
                            {"url": "medium.jpg", "width": 300},
                            {"url": "small.jpg", "width": 64}
                        ]
                    }
                }
            ]
        }
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry, \
         patch.object(spotify_service, 'fetch_app_access_token', new_callable=AsyncMock) as mock_fetch_token:
        mock_fetch_token.return_value = "test_token"
        mock_handle_retry.return_value = mock_search_response
        
        result = await spotify_service.search_tracks("test query", 0, 10)
        
        assert result == mock_search_response
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_track_by_id_success(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    mock_track_response = {
        "id": "track1",
        "name": "Test Track",
        "artists": [{"name": "Test Artist"}],
        "external_ids": {"isrc": "test_isrc"},
        "album": {
            "images": [
                {"url": "large.jpg", "width": 640},
                {"url": "medium.jpg", "width": 300},
                {"url": "small.jpg", "width": 64}
            ]
        }
    }
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry, \
         patch.object(spotify_service, 'fetch_app_access_token', new_callable=AsyncMock) as mock_fetch_token:
        mock_fetch_token.return_value = "test_token"
        mock_handle_retry.return_value = mock_track_response
        
        result = await spotify_service.get_track_by_id("track1")
        
        assert result == {
            "spotify_id": "track1",
            "isrc": "test_isrc",
            "name": "Test Track",
            "artists": ["Test Artist"],
            "cover": {
                "small": "small.jpg",
                "medium": "medium.jpg",
                "large": "large.jpg"
            }
        }
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_track_by_id_not_found(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry, \
         patch.object(spotify_service, 'fetch_app_access_token', new_callable=AsyncMock) as mock_fetch_token:
        mock_fetch_token.return_value = "test_token"
        mock_handle_retry.side_effect = HTTPException(status_code=404, detail="Track not found")
        
        result = await spotify_service.get_track_by_id("nonexistent_track")
        
        assert result is None
        mock_handle_retry.assert_called_once()

@pytest.mark.asyncio
async def test_get_track_by_id_error(spotify_service):
    # Reset the cached token to force a new fetch
    spotify_service.app_token = {"access_token": None, "expires_at": 0}
    
    with patch('app.services.providers.spotify_service.handle_retry', new_callable=AsyncMock) as mock_handle_retry, \
         patch.object(spotify_service, 'fetch_app_access_token', new_callable=AsyncMock) as mock_fetch_token:
        mock_fetch_token.return_value = "test_token"
        mock_handle_retry.side_effect = HTTPException(status_code=500, detail="Internal server error")
        
        with pytest.raises(HTTPException) as exc_info:
            await spotify_service.get_track_by_id("error_track")
        
        assert exc_info.value.status_code == 500
        mock_handle_retry.assert_called_once() 