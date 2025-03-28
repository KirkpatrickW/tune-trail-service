import pytest
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.postgresql import User, Track, Locality, LocalityTrack, UserSpotifyOauthAccount
from app.utils.jwt_helper import create_access_token
from httpx import AsyncClient
from httpx import ASGITransport

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.locality_tracks import postgresql_client

    async def override_get_session():
        yield test_session

    # Dependencies will be the death of me
    app.dependency_overrides[postgresql_client.get_session] = override_get_session

    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture
def test_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )

@pytest.fixture
async def test_data(test_session: AsyncSession):
    # Create test user
    user = User(
        user_id=1,
        username="test_user",
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    
    # Create test Spotify OAuth account
    spotify_account = UserSpotifyOauthAccount(
        user_id=1,
        provider_user_id="test_spotify_id",
        encrypted_access_token="test_spotify_token",
        encrypted_refresh_token="test_spotify_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    
    track = Track(
        track_id=1,
        isrc="TEST12345678",
        spotify_id="test_track_id",
        deezer_id=123456789,
        name="Test Track",
        artists=["Test Artist"],
        cover_small="http://test.com/small",
        cover_medium="http://test.com/medium",
        cover_large="http://test.com/large"
    )
    
    locality = Locality(
        locality_id=1,
        name="Test Locality",
        latitude=0.0,
        longitude=0.0,
        total_tracks=0
    )
    
    locality_track = LocalityTrack(
        locality_track_id=1,
        locality_id=1,
        track_id=1,
        user_id=1,
        total_votes=0
    )
    
    # Add to database
    test_session.add(user)
    test_session.add(spotify_account)
    test_session.add(track)
    test_session.add(locality)
    test_session.add(locality_track)
    await test_session.commit()
    
    yield {
        "user": user,
        "spotify_account": spotify_account,
        "track": track,
        "locality": locality,
        "locality_track": locality_track
    }

@pytest.mark.asyncio
async def test_vote_upvote_success(test_client, test_data, test_token):
    response = await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": 1},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully upvoted track"

@pytest.mark.asyncio
async def test_vote_downvote_success(test_client, test_data, test_token):
    response = await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": -1},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully downvoted track"

@pytest.mark.asyncio
async def test_vote_unvote_success(test_client, test_data, test_token):
    # First vote on the track
    await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": 1},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    # Then try to unvote
    response = await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": 0},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully unvoted track"

@pytest.mark.asyncio
async def test_vote_invalid_value(test_client, test_data, test_token):
    response = await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": 2},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 422
    assert "Value error, must be 1 (UPVOTE), -1 (DOWNVOTE), or 0 (UNVOTE)" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_vote_nonexistent_track(test_client, test_data, test_token):
    response = await test_client.patch(
        "/locality-tracks/999/vote",
        json={"vote_value": 1},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Track in locality not found"

@pytest.mark.asyncio
async def test_vote_missing_auth(test_client, test_data):
    response = await test_client.patch(
        "/locality-tracks/1/vote",
        json={"vote_value": 1}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"