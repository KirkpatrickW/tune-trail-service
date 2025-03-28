import pytest
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from httpx import AsyncClient, ASGITransport
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.models.postgresql import User, UserSession, Locality, Track, LocalityTrack, LocalityTrackVote
from app.utils.jwt_helper import create_access_token
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import select


with patch('app.services.providers.overpass_service.OverpassService') as mock_overpass:
    with patch('app.services.providers.spotify_service.SpotifyService') as mock_spotify:
        with patch('app.services.providers.deezer_service.DeezerService') as mock_deezer:
            from app.routes.localities import overpass_service
            from app.routes.localities import spotify_service
            from app.routes.localities import deezer_service

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.localities import postgresql_client

    async def override_get_session():
        yield test_session

    # Dependencies will be the death of me
    app.dependency_overrides[postgresql_client.get_session] = override_get_session

    FastAPICache.init(InMemoryBackend())
    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture
def mock_overpass_service():
    instance = AsyncMock()
    instance.get_localities_by_bounds = AsyncMock()
    instance.get_localities_by_bounds.return_value = [
        {
            "locality_id": 123456,
            "name": "Test City",
            "latitude": 51.5074,
            "longitude": -0.1278
        },
        {
            "locality_id": 789012,
            "name": "Test Town",
            "latitude": 52.5200,
            "longitude": 13.4050
        }
    ]
    instance.get_locality_by_id = AsyncMock()
    instance.get_locality_by_id.return_value = {
        "locality_id": 123456,
        "name": "Test City",
        "latitude": 51.5074,
        "longitude": -0.1278
    }
    overpass_service.get_localities_by_bounds = instance.get_localities_by_bounds
    overpass_service.get_locality_by_id = instance.get_locality_by_id
    yield instance

@pytest.fixture
def mock_spotify_service():
    instance = AsyncMock()
    instance.get_track_by_id = AsyncMock()
    instance.get_track_by_id.return_value = {
        "spotify_id": "spotify123",
        "isrc": "test123",
        "name": "Test Track",
        "artists": ["Test Artist"],
        "cover": {
            "small": "www.smallimage.com",
            "medium": "www.mediumimage.com",
            "large": "www.largeimage.com"
        }
    }

    spotify_service.get_track_by_id = instance.get_track_by_id
    yield instance

@pytest.fixture
def mock_deezer_service():
    instance = AsyncMock()
    instance.fetch_deezer_id_by_isrc = AsyncMock()
    instance.fetch_deezer_id_by_isrc.return_value = 123456
    instance.fetch_preview_url_by_deezer_id = AsyncMock()
    instance.fetch_preview_url_by_deezer_id.return_value = "https://example.com/preview.mp3"
    deezer_service.fetch_deezer_id_by_isrc = instance.fetch_deezer_id_by_isrc
    deezer_service.fetch_preview_url_by_deezer_id = instance.fetch_preview_url_by_deezer_id
    yield instance

@pytest.fixture
def test_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )

@pytest.fixture
async def test_localities(test_session):
    """Create test localities in the database."""
    localities = [
        Locality(
            locality_id=123456,
            name="Test City",
            latitude=51.5074,
            longitude=-0.1278,
            total_tracks=0
        ),
        Locality(
            locality_id=789012,
            name="Test Town",
            latitude=52.5200,
            longitude=13.4050,
            total_tracks=0
        )
    ]
    test_session.add_all(localities)
    await test_session.commit()
    return localities

@pytest.fixture
async def test_tracks(test_session):
    """Create test tracks in the database."""
    tracks = [
        Track(
            track_id=1,
            isrc="test123",
            spotify_id="spotify123",
            deezer_id=123456,
            name="Test Track 1",
            artists=["Test Artist 1"],
            cover_large="large1.jpg"
        ),
        Track(
            track_id=2,
            isrc="test456",
            spotify_id="spotify456",
            deezer_id=789012,
            name="Test Track 2",
            artists=["Test Artist 2"],
            cover_large="large2.jpg"
        )
    ]
    test_session.add_all(tracks)
    await test_session.commit()
    return tracks

@pytest.fixture
async def test_users(test_session):
    """Create test users in the database."""
    users = [
        User(
            username="testuser1",
            hashed_password=b"hashed_password",
            is_oauth_account=False,
            is_admin=False
        ),
        User(
            username="testuser2",
            hashed_password=b"hashed_password",
            is_oauth_account=False,
            is_admin=False
        )
    ]
    test_session.add_all(users)
    await test_session.commit()
    return users

@pytest.fixture
async def test_locality_tracks(test_session, test_localities, test_tracks, test_users):
    """Create test locality tracks in the database."""
    locality_tracks = [
        LocalityTrack(
            locality_id=test_localities[0].locality_id,  # Test City
            track_id=test_tracks[0].track_id,
            user_id=test_users[0].user_id,
            total_votes=5
        ),
        LocalityTrack(
            locality_id=test_localities[0].locality_id,  # Test City
            track_id=test_tracks[1].track_id,
            user_id=test_users[1].user_id,
            total_votes=3
        )
    ]
    test_session.add_all(locality_tracks)
    await test_session.commit()
    return locality_tracks

@pytest.fixture
async def test_user_votes(test_session, test_locality_tracks, test_users):
    """Create test user votes in the database."""
    user_votes = [
        LocalityTrackVote(
            locality_track_id=test_locality_tracks[0].locality_track_id,
            user_id=test_users[0].user_id,
            vote=1
        )
    ]
    test_session.add_all(user_votes)
    await test_session.commit()
    return user_votes

@pytest.mark.asyncio
async def test_get_localities_success(test_client, test_session, mock_overpass_service, test_localities):
    """Test successful retrieval of localities."""
    response = await test_client.get(
        "/localities",
        params={
            "north": 53.0,  # North boundary (above Test Town at 52.5200)
            "east": 14.0,   # East boundary (east of Test Town at 13.4050)
            "south": 51.0,  # South boundary (below Test City at 51.5074)
            "west": -1.0    # West boundary (west of Test City at -0.1278)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Verify each locality has the correct GeoJSON Feature structure
    for locality in data:
        assert locality["type"] == "Feature"
        assert "properties" in locality
        assert "geometry" in locality
        assert locality["geometry"]["type"] == "Point"
        assert len(locality["geometry"]["coordinates"]) == 2  # [longitude, latitude]
        
        # Verify properties
        props = locality["properties"]
        assert "id" in props
        assert "name" in props
        assert "total_tracks" in props

@pytest.mark.asyncio
async def test_get_localities_invalid_latitude(test_client, test_session, mock_overpass_service, test_localities):
    """Test getting localities with invalid latitude."""
    response = await test_client.get(
        "/localities",
        params={
            "north": 91.0,  # Invalid latitude (> 90)
            "east": 14.0,
            "south": 51.0,
            "west": -1.0
        }
    )
    
    assert response.status_code == 422
    assert "Value error, must be between -90 and 90" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_get_localities_invalid_longitude(test_client, test_session, mock_overpass_service, test_localities):
    """Test getting localities with invalid longitude."""
    response = await test_client.get(
        "/localities",
        params={
            "north": 53.0,
            "east": 181.0,  # Invalid longitude (> 180)
            "south": 51.0,
            "west": -1.0
        }
    )
    
    assert response.status_code == 422
    assert "Value error, must be between -180 and 180" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_get_localities_north_less_than_south(test_client, test_session, mock_overpass_service, test_localities):
    """Test getting localities with north less than south."""
    response = await test_client.get(
        "/localities",
        params={
            "north": 51.0,  # Less than south
            "east": 14.0,
            "south": 53.0,  # Greater than north
            "west": -1.0
        }
    )
    
    assert response.status_code == 422
    assert "Value error, north must be greater than south" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_get_localities_east_less_than_west(test_client, test_session, mock_overpass_service, test_localities):
    """Test getting localities with east less than west."""
    response = await test_client.get(
        "/localities",
        params={
            "north": 53.0,
            "east": -1.0,   # Less than west
            "south": 51.0,
            "west": 14.0    # Greater than east
        }
    )
    
    assert response.status_code == 422
    assert "Value error, east must be greater than west" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_get_localities_empty_results(test_client, test_session, mock_overpass_service):
    """Test getting localities when no results are found in database or Overpass."""
    # Mock Overpass service to return empty list
    mock_overpass_service.get_localities_by_bounds.return_value = []
    
    response = await test_client.get(
        "/localities",
        params={
            "north": 53.0,
            "east": 14.0,
            "south": 51.0,
            "west": -1.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0  # Should return empty array when no localities found

@pytest.mark.asyncio
async def test_get_tracks_in_locality_unauthorized(test_client, test_session, test_localities, test_tracks, test_users, test_locality_tracks):
    """Test getting tracks from a locality as an unauthorized user."""
    response = await test_client.get(f"/localities/{test_localities[0].locality_id}/tracks")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert isinstance(data, list)
    assert len(data) == 2  # Should return both tracks
    
    # Verify each track has the correct structure
    for track in data:
        assert "track_id" in track
        assert "name" in track
        assert "artists" in track
        assert "cover" in track
        assert "total_votes" in track
        assert "user_vote" in track
        assert "username" in track
        
        # For unauthorized users, user_vote should be 0
        assert track["user_vote"] == 0
        
        # Verify cover object structure
        assert "small" in track["cover"]
        assert "medium" in track["cover"]
        assert "large" in track["cover"]
        
        # Verify certain fields are excluded
        assert "cover_small" not in track
        assert "cover_medium" not in track
        assert "cover_large" not in track
        assert "deezer_id" not in track
        assert "isrc" not in track

@pytest.mark.asyncio
async def test_get_tracks_in_locality_success(test_client, test_session, test_localities, test_tracks, test_users, test_locality_tracks, test_user_votes):
    """Test successful retrieval of tracks in a locality."""
    # Create a token for a user who has a track in the locality
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.get(
        f"/localities/{test_localities[0].locality_id}/tracks",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert isinstance(data, list)
    assert len(data) == 2  # Should return both tracks
    
    # Verify each track has the correct structure
    for track in data:
        assert "track_id" in track
        assert "name" in track
        assert "artists" in track
        assert "cover" in track
        assert "total_votes" in track
        assert "user_vote" in track
        assert "username" in track
        
        # Verify user_vote for the track the user voted on
        if track["track_id"] == test_tracks[0].track_id:
            assert track["user_vote"] == 1  # User voted up on this track
        else:
            assert track["user_vote"] == 0  # User hasn't voted on this track
        
        # Verify cover object structure
        assert "small" in track["cover"]
        assert "medium" in track["cover"]
        assert "large" in track["cover"]
        
        # Verify certain fields are excluded
        assert "cover_small" not in track
        assert "cover_medium" not in track
        assert "cover_large" not in track
        assert "deezer_id" not in track
        assert "isrc" not in track

@pytest.mark.asyncio
async def test_get_tracks_in_locality_no_tracks(test_client, test_session, test_localities, test_users):
    """Test getting tracks from a locality with no tracks."""
    # Create a token for a user
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.get(
        f"/localities/{test_localities[1].locality_id}/tracks",  # Test Town has no tracks
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

@pytest.mark.asyncio
async def test_get_tracks_in_locality_nonexistent(test_client, test_session, test_users):
    """Test getting tracks from a nonexistent locality."""
    # Create a token for a user
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.get(
        "/localities/999999/tracks",  # Nonexistent locality ID
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Locality not found"

@pytest.mark.asyncio
async def test_add_track_to_locality_existing_locality(test_client, test_session, test_localities, test_tracks, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a track to an existing locality."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        f"/localities/{test_localities[0].locality_id}/tracks/spotify123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"]  == "Successfully added Test Track 1 to Test City"

@pytest.mark.asyncio
async def test_add_track_to_locality_new_locality(test_client, test_session, mock_overpass_service, test_tracks, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a track to a new locality from Overpass."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Mock Overpass to return a new locality
    mock_overpass_service.get_locality_by_id.return_value = {
        "locality_id": 987654,
        "name": "New City",
        "latitude": 48.8566,
        "longitude": 2.3522
    }
    
    response = await test_client.put(
        "/localities/987654/tracks/spotify123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully added Test Track 1 to New City"

@pytest.mark.asyncio
async def test_add_track_to_locality_nonexistent_locality(test_client, test_session, mock_overpass_service, test_tracks, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a track to a nonexistent locality."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Mock Overpass to return None (locality not found)
    mock_overpass_service.get_locality_by_id.return_value = None
    
    response = await test_client.put(
        "/localities/999999/tracks/spotify123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Locality with ID 999999 not found in database or Overpass"

@pytest.mark.asyncio
async def test_add_track_to_locality_new_track(test_client, test_session, test_localities, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a new track to a locality."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Mock Spotify to return a new track
    mock_spotify_service.get_track_by_id.return_value = {
        "spotify_id": "new_spotify123",
        "isrc": "new123",
        "name": "New Track",
        "artists": ["New Artist"],
        "cover": {
            "small": "www.newsmallimage.com",
            "medium": "www.newmediumimage.com",
            "large": "www.newlargeimage.com"
        }
    }

    response = await test_client.put(
        f"/localities/{test_localities[0].locality_id}/tracks/new_spotify123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == 'Successfully added New Track to Test City'

@pytest.mark.asyncio
async def test_add_track_to_locality_nonexistent_track(test_client, test_session, test_localities, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a track that doesn't exist in Spotify."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Mock Spotify to return None (track not found)
    mock_spotify_service.get_track_by_id.return_value = None
    
    response = await test_client.put(
        f"/localities/{test_localities[0].locality_id}/tracks/nonexistent123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Track with Spotify ID nonexistent123 not found in database or Spotify"

@pytest.mark.asyncio
async def test_add_track_to_locality_no_deezer_match(test_client, test_session, test_localities, test_users, mock_spotify_service, mock_deezer_service):
    """Test adding a track that exists in Spotify but not in Deezer."""
    token = create_access_token(
        user_id=test_users[0].user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Mock Deezer to return None (no match found)
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = None
    
    response = await test_client.put(
        f"/localities/{test_localities[0].locality_id}/tracks/spotify123",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "ISRC with the value test123 not found in Deezer"

@pytest.mark.asyncio
async def test_add_track_to_locality_unauthorized(test_client, test_session, test_localities):
    """Test adding a track without authentication."""
    response = await test_client.put(
        f"/localities/{test_localities[0].locality_id}/tracks/spotify123"
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_tracks_for_localities_success(test_client, test_session, test_localities, test_tracks, test_users, test_locality_tracks, mock_deezer_service):
    """Test successful retrieval of tracks from localities within radius."""
    # Mock Deezer service to return preview URLs for both tracks
    mock_deezer_service.fetch_preview_url_by_deezer_id.side_effect = [
        "https://example.com/preview1.mp3",  # For first track
        "https://example.com/preview2.mp3"   # For second track
    ]
    
    # Test with coordinates near Test City (51.5074, -0.1278)
    response = await test_client.get(
        "/localities/tracks",
        params={
            "latitude": 51.5074,
            "longitude": -0.1278,
            "radius": 1000  # 1km radius
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert isinstance(data, list)
    assert len(data) == 1  # Only Test City should be within radius
    
    # Verify locality structure
    locality = data[0]
    assert locality["locality_id"] == test_localities[0].locality_id
    assert locality["name"] == "Test City"
    assert "tracks" in locality
    
    # Verify tracks structure
    tracks = locality["tracks"]
    assert len(tracks) == 2  # Both tracks from Test City
    
    # Verify track structure and preview URLs
    assert tracks[0]["preview_url"] == "https://example.com/preview1.mp3"
    assert tracks[1]["preview_url"] == "https://example.com/preview2.mp3"
    
    # Verify track structure
    for track in tracks:
        assert "track_id" in track
        assert "name" in track
        assert "artists" in track
        assert "cover" in track
        assert "preview_url" in track
        
        # Verify cover object structure
        assert "small" in track["cover"]
        assert "medium" in track["cover"]
        assert "large" in track["cover"]
        
        # Verify certain fields are excluded
        assert "cover_small" not in track
        assert "cover_medium" not in track
        assert "cover_large" not in track
        assert "spotify_id" not in track
        assert "deezer_id" not in track
        assert "isrc" not in track

@pytest.mark.asyncio
async def test_get_tracks_for_localities_no_preview_url(test_client, test_session, test_localities, test_tracks, test_users, test_locality_tracks, mock_deezer_service):
    """Test that tracks without preview URLs are excluded."""
    # Mock Deezer service to return None for all preview URLs
    mock_deezer_service.fetch_preview_url_by_deezer_id.return_value = None
    
    response = await test_client.get(
        "/localities/tracks",
        params={
            "latitude": 51.5074,
            "longitude": -0.1278,
            "radius": 1000
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert isinstance(data, list)
    assert len(data) == 1  # Only Test City should be within radius
    
    # Verify no tracks are returned since they have no preview URLs
    locality = data[0]
    assert locality["locality_id"] == test_localities[0].locality_id
    assert locality["name"] == "Test City"
    assert len(locality["tracks"]) == 0

@pytest.mark.asyncio
async def test_get_tracks_for_localities_no_localities_in_radius(test_client, test_session, test_localities, test_tracks, test_users, test_locality_tracks, mock_deezer_service):
    """Test when no localities are within the specified radius."""
    # Mock Deezer service to return preview URLs
    mock_deezer_service.fetch_preview_url_by_deezer_id.return_value = "https://example.com/preview.mp3"
    
    # Test with coordinates far from any test localities
    response = await test_client.get(
        "/localities/tracks",
        params={
            "latitude": 0.0,
            "longitude": 0.0,
            "radius": 1000  # 1km radius
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify empty response
    assert isinstance(data, list)
    assert len(data) == 0