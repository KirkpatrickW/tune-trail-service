import pytest
from unittest.mock import AsyncMock, patch
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from httpx import AsyncClient, ASGITransport
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.models.postgresql import Track
from app.utils.jwt_helper import create_access_token

# Patch the services before importing the app
with patch('app.services.providers.spotify_service.SpotifyService') as mock_spotify:
    with patch('app.services.providers.deezer_service.DeezerService') as mock_deezer:
        from app.routes.tracks import spotify_service, deezer_service

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.tracks import postgresql_client

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
    instance.search_tracks = AsyncMock()
    instance.search_tracks.return_value = {
        "tracks": {
            "items": [],
            "total": 0
        }
    }
    spotify_service.get_track_by_id = instance.get_track_by_id
    spotify_service.search_tracks = instance.search_tracks
    yield instance

@pytest.fixture
def mock_deezer_service():
    instance = AsyncMock()
    instance.fetch_deezer_id_by_isrc = AsyncMock()
    instance.fetch_deezer_id_by_isrc.return_value = 123456
    deezer_service.fetch_deezer_id_by_isrc = instance.fetch_deezer_id_by_isrc
    yield instance

@pytest.fixture
def admin_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=True,
        spotify_access_token="test_spotify_token"
    )

@pytest.fixture
def regular_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )

@pytest.mark.asyncio
async def test_ban_track_success(test_client, test_session, admin_token, mock_spotify_service, mock_deezer_service):
    # Create a track to ban
    track = Track(
        track_id=1,
        isrc="TEST12345678",
        spotify_id="spotify_track_1",
        deezer_id=123456789,
        name="Test Track",
        artists=["Test Artist"],
        cover_small="http://test.com/small",
        cover_medium="http://test.com/medium",
        cover_large="http://test.com/large",
        is_banned=False
    )
    test_session.add(track)
    await test_session.commit()

    # Mock Spotify service to return the track
    mock_spotify_service.get_track_by_id.return_value = {
        "spotify_id": "spotify_track_1",
        "isrc": "TEST12345678",
        "name": "Test Track",
        "artists": ["Test Artist"],
        "cover": {
            "small": "http://test.com/small",
            "medium": "http://test.com/medium",
            "large": "http://test.com/large"
        }
    }

    response = await test_client.patch(
        "/tracks/spotify_track_1/ban",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully banned Test Track"

    # Verify track is banned in database
    await test_session.refresh(track)
    assert track.is_banned == True

@pytest.mark.asyncio
async def test_ban_track_unauthorized(test_client, regular_token):
    response = await test_client.patch(
        "/tracks/spotify_track_1/ban",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

@pytest.mark.asyncio
async def test_ban_track_not_found(test_client, admin_token, mock_spotify_service, mock_deezer_service):
    # Mock Spotify service to return no track
    mock_spotify_service.get_track_by_id.return_value = None
    
    response = await test_client.patch(
        "/tracks/nonexistent_id/ban",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Track with Spotify ID nonexistent_id not found in database or Spotify"

@pytest.mark.asyncio
async def test_unban_track_success(test_client, test_session, admin_token):
    # Create a banned track
    track = Track(
        track_id=1,
        isrc="TEST12345678",
        spotify_id="spotify_track_1",
        deezer_id=123456789,
        name="Test Track",
        artists=["Test Artist"],
        cover_small="http://test.com/small",
        cover_medium="http://test.com/medium",
        cover_large="http://test.com/large",
        is_banned=True
    )
    test_session.add(track)
    await test_session.commit()

    response = await test_client.patch(
        "/tracks/1/unban",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully unbanned Test Track"

    # Verify track is unbanned in database
    await test_session.refresh(track)
    assert track.is_banned == False

@pytest.mark.asyncio
async def test_unban_track_unauthorized(test_client, regular_token):
    response = await test_client.patch(
        "/tracks/1/unban",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

@pytest.mark.asyncio
async def test_unban_track_not_found(test_client, admin_token):
    response = await test_client.patch(
        "/tracks/999/unban",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Track not found"

@pytest.mark.asyncio
async def test_get_banned_tracks_success(test_client, test_session, admin_token):
    # Create some banned tracks
    tracks = [
        Track(
            track_id=1,
            isrc="TEST12345678",
            spotify_id="spotify_track_1",
            deezer_id=123456789,
            name="Banned Track 1",
            artists=["Test Artist 1"],
            cover_small="http://test.com/small1",
            cover_medium="http://test.com/medium1",
            cover_large="http://test.com/large1",
            is_banned=True
        ),
        Track(
            track_id=2,
            isrc="TEST87654321",
            spotify_id="spotify_track_2",
            deezer_id=987654321,
            name="Banned Track 2",
            artists=["Test Artist 2"],
            cover_small="http://test.com/small2",
            cover_medium="http://test.com/medium2",
            cover_large="http://test.com/large2",
            is_banned=True
        )
    ]
    for track in tracks:
        test_session.add(track)
    await test_session.commit()

    response = await test_client.get(
        "/tracks/banned",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Banned Track 1"
    assert data[1]["name"] == "Banned Track 2"
    assert all(track["is_banned"] for track in data)

@pytest.mark.asyncio
async def test_get_banned_tracks_unauthorized(test_client, regular_token):
    response = await test_client.get(
        "/tracks/banned",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

@pytest.mark.asyncio
async def test_get_banned_tracks_empty(test_client, test_session, admin_token):
    response = await test_client.get(
        "/tracks/banned",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_search_tracks_success(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify search response
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "external_ids": {"isrc": "TEST12345678"},
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large1"},
                            {"url": "http://test.com/medium1"},
                            {"url": "http://test.com/small1"}
                        ]
                    }
                },
                {
                    "id": "spotify_track_2",
                    "external_ids": {"isrc": "TEST87654321"},
                    "name": "Test Track 2",
                    "artists": [{"name": "Test Artist 2"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large2"},
                            {"url": "http://test.com/medium2"},
                            {"url": "http://test.com/small2"}
                        ]
                    }
                }
            ],
            "total": 2
        }
    }
    
    # Mock Deezer service to return IDs
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = 123456789
    
    response = await test_client.get("/tracks/search?q=test&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 2
    assert len(data["results"]) == 2
    assert data["next_offset"] == 20
    
    # Verify first track
    assert data["results"][0]["spotify_id"] == "spotify_track_1"
    assert data["results"][0]["deezer_id"] == 123456789
    assert data["results"][0]["isrc"] == "TEST12345678"
    assert data["results"][0]["name"] == "Test Track 1"
    assert data["results"][0]["artists"] == ["Test Artist 1"]
    assert data["results"][0]["cover"]["large"] == "http://test.com/large1"
    assert data["results"][0]["cover"]["medium"] == "http://test.com/medium1"
    assert data["results"][0]["cover"]["small"] == "http://test.com/small1"
    
    # Verify second track
    assert data["results"][1]["spotify_id"] == "spotify_track_2"
    assert data["results"][1]["deezer_id"] == 123456789
    assert data["results"][1]["isrc"] == "TEST87654321"
    assert data["results"][1]["name"] == "Test Track 2"
    assert data["results"][1]["artists"] == ["Test Artist 2"]
    assert data["results"][1]["cover"]["large"] == "http://test.com/large2"
    assert data["results"][1]["cover"]["medium"] == "http://test.com/medium2"
    assert data["results"][1]["cover"]["small"] == "http://test.com/small2"

@pytest.mark.asyncio
async def test_search_tracks_no_isrc(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify search response with a track that has no ISRC
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "external_ids": {},  # No ISRC
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large1"},
                            {"url": "http://test.com/medium1"},
                            {"url": "http://test.com/small1"}
                        ]
                    }
                }
            ],
            "total": 1
        }
    }
    
    # Mock Deezer service to return None
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = None
    
    response = await test_client.get("/tracks/search?q=test&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 1
    assert len(data["results"]) == 0  # Track should be skipped due to missing ISRC
    assert data["next_offset"] == 21  # Offset should be incremented

@pytest.mark.asyncio
async def test_search_tracks_no_deezer_id(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify search response
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",
                    "external_ids": {"isrc": "TEST12345678"},
                    "name": "Test Track 1",
                    "artists": [{"name": "Test Artist 1"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large1"},
                            {"url": "http://test.com/medium1"},
                            {"url": "http://test.com/small1"}
                        ]
                    }
                }
            ],
            "total": 1
        }
    }
    
    # Mock Deezer service to return None (no Deezer ID found)
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = None
    
    response = await test_client.get("/tracks/search?q=test&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 1
    assert len(data["results"]) == 0  # Track should be skipped due to missing Deezer ID
    assert data["next_offset"] == 21  # Offset should be incremented

@pytest.mark.asyncio
async def test_search_tracks_empty_response(test_client, mock_spotify_service, mock_deezer_service):
    # Mock Spotify search response with no results
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [],
            "total": 0
        }
    }
    
    # Mock Deezer service to return None
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = None
    
    response = await test_client.get("/tracks/search?q=nonexistent&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 0
    assert len(data["results"]) == 0
    assert data["next_offset"] == 20

@pytest.mark.asyncio
async def test_search_tracks_skip_banned_tracks(test_client, test_session, mock_spotify_service, mock_deezer_service):
    # Create a banned track in the database
    banned_track = Track(
        isrc="TEST12345678",
        spotify_id="spotify_track_1",
        deezer_id=123456789,
        name="Banned Track",
        artists=["Banned Artist"],
        cover_small="http://test.com/small",
        cover_medium="http://test.com/medium",
        cover_large="http://test.com/large",
        is_banned=True
    )
    test_session.add(banned_track)
    await test_session.commit()
    
    # Mock Spotify search response with a banned track and a regular track
    mock_spotify_service.search_tracks.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "spotify_track_1",  # This is the banned track
                    "external_ids": {"isrc": "TEST12345678"},
                    "name": "Banned Track",
                    "artists": [{"name": "Banned Artist"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large"},
                            {"url": "http://test.com/medium"},
                            {"url": "http://test.com/small"}
                        ]
                    }
                },
                {
                    "id": "spotify_track_2",  # This is a regular track
                    "external_ids": {"isrc": "TEST87654321"},
                    "name": "Regular Track",
                    "artists": [{"name": "Regular Artist"}],
                    "album": {
                        "images": [
                            {"url": "http://test.com/large2"},
                            {"url": "http://test.com/medium2"},
                            {"url": "http://test.com/small2"}
                        ]
                    }
                }
            ],
            "total": 2
        }
    }
    
    # Mock Deezer service to return IDs
    mock_deezer_service.fetch_deezer_id_by_isrc.return_value = 123456789
    
    response = await test_client.get("/tracks/search?q=test&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 2
    assert len(data["results"]) == 1  # Only one track should be returned (the non-banned one)
    assert data["next_offset"] == 21  # Offset should be incremented for the skipped banned track
    
    # Verify the returned track is the non-banned one
    assert data["results"][0]["spotify_id"] == "spotify_track_2"
    assert data["results"][0]["deezer_id"] == 123456789
    assert data["results"][0]["isrc"] == "TEST87654321"
    assert data["results"][0]["name"] == "Regular Track"
    assert data["results"][0]["artists"] == ["Regular Artist"]
    assert data["results"][0]["cover"]["large"] == "http://test.com/large2"
    assert data["results"][0]["cover"]["medium"] == "http://test.com/medium2"
    assert data["results"][0]["cover"]["small"] == "http://test.com/small2"