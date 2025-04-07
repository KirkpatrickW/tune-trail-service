import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.utils.routes.track_utils import get_or_create_track
from app.models.postgresql import Track

@pytest.fixture
def mock_spotify_track():
    return {
        "isrc": "TEST12345678",
        "name": "Test Track",
        "artists": ["Test Artist"],
        "cover": {
            "large": "large.jpg",
            "medium": "medium.jpg",
            "small": "small.jpg"
        }
    }

@pytest.mark.asyncio
async def test_get_or_create_track_existing(test_session):
    # Create a test track in the database
    track = Track(
        isrc="TEST12345678",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg",
        cover_medium="medium.jpg",
        cover_small="small.jpg"
    )
    test_session.add(track)
    await test_session.flush()

    # Mock the track service to return our test track
    with patch('app.utils.routes.track_utils.track_service.get_track_by_spotify_id', new_callable=AsyncMock) as mock_get_track:
        mock_get_track.return_value = track
        
        # Call the function
        result = await get_or_create_track(test_session, "spotify123")
        
        # Verify the result
        assert result.track_id == track.track_id
        assert result.spotify_id == "spotify123"
        
        # Verify track service was called
        mock_get_track.assert_called_once_with(test_session, "spotify123")

@pytest.mark.asyncio
async def test_get_or_create_track_new(test_session, mock_spotify_track):
    # Mock the services
    with patch('app.utils.routes.track_utils.track_service.get_track_by_spotify_id', new_callable=AsyncMock) as mock_get_track, \
         patch('app.utils.routes.track_utils.spotify_service.get_track_by_id', new_callable=AsyncMock) as mock_spotify, \
         patch('app.utils.routes.track_utils.deezer_service.fetch_deezer_id_by_isrc', new_callable=AsyncMock) as mock_deezer, \
         patch('app.utils.routes.track_utils.track_service.add_new_track', new_callable=AsyncMock) as mock_add_track:
        
        # Setup mock returns
        mock_get_track.return_value = None
        mock_spotify.return_value = mock_spotify_track
        mock_deezer.return_value = 123456
        mock_add_track.return_value = Track(
            isrc="TEST12345678",
            spotify_id="spotify123",
            deezer_id=123456,
            name="Test Track",
            artists=["Test Artist"],
            cover_large="large.jpg",
            cover_medium="medium.jpg",
            cover_small="small.jpg"
        )
        
        # Call the function
        result = await get_or_create_track(test_session, "spotify123")
        
        # Verify the result
        assert result.spotify_id == "spotify123"
        assert result.isrc == "TEST12345678"
        assert result.deezer_id == 123456
        
        # Verify all services were called
        mock_get_track.assert_called_once_with(test_session, "spotify123")
        mock_spotify.assert_called_once_with("spotify123")
        mock_deezer.assert_called_once_with("TEST12345678")
        mock_add_track.assert_called_once_with(
            test_session,
            "TEST12345678",
            "spotify123",
            123456,
            "Test Track",
            ["Test Artist"],
            "large.jpg",
            "medium.jpg",
            "small.jpg"
        )

@pytest.mark.asyncio
async def test_get_or_create_track_spotify_not_found(test_session):
    # Mock the services
    with patch('app.utils.routes.track_utils.track_service.get_track_by_spotify_id', new_callable=AsyncMock) as mock_get_track, \
         patch('app.utils.routes.track_utils.spotify_service.get_track_by_id', new_callable=AsyncMock) as mock_spotify:
        
        # Setup mock returns
        mock_get_track.return_value = None
        mock_spotify.return_value = None
        
        # Call the function and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_track(test_session, "spotify123")
        
        # Verify the error
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Track with Spotify ID spotify123 not found in database or Spotify"

@pytest.mark.asyncio
async def test_get_or_create_track_deezer_not_found(test_session, mock_spotify_track):
    # Mock the services
    with patch('app.utils.routes.track_utils.track_service.get_track_by_spotify_id', new_callable=AsyncMock) as mock_get_track, \
         patch('app.utils.routes.track_utils.spotify_service.get_track_by_id', new_callable=AsyncMock) as mock_spotify, \
         patch('app.utils.routes.track_utils.deezer_service.fetch_deezer_id_by_isrc', new_callable=AsyncMock) as mock_deezer:
        
        # Setup mock returns
        mock_get_track.return_value = None
        mock_spotify.return_value = mock_spotify_track
        mock_deezer.return_value = None
        
        # Call the function and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_track(test_session, "spotify123")
        
        # Verify the error
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "ISRC with the value TEST12345678 not found in Deezer" 