import pytest
from sqlalchemy import select

from app.models.postgresql import LocalityTrack
from app.services.postgresql.locality_track_service import LocalityTrackService
from app.services.postgresql.locality_service import LocalityService
from app.services.postgresql.track_service import TrackService
from app.services.postgresql.user_service import UserService

@pytest.mark.asyncio
async def test_get_locality_track_by_locality_track_id(test_session):
    service = LocalityTrackService()
    user_service = UserService()
    locality_service = LocalityService()
    track_service = TrackService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Create test track
    track = await track_service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Add track to locality
    locality_track = LocalityTrack(
        locality_id=locality.locality_id,
        track_id=track.track_id,
        user_id=user.user_id,
        total_votes=0
    )
    test_session.add(locality_track)
    await test_session.flush()
    
    # Test getting the locality track
    result = await service.get_locality_track_by_locality_track_id(test_session, locality_track.locality_track_id)
    assert result.locality_track_id == locality_track.locality_track_id
    assert result.locality_id == locality.locality_id
    assert result.track_id == track.track_id
    assert result.user_id == user.user_id
    assert result.total_votes == 0
    
    # Test getting non-existent locality track
    non_existent = await service.get_locality_track_by_locality_track_id(test_session, 999)
    assert non_existent is None

@pytest.mark.asyncio
async def test_add_track_to_locality(test_session):
    service = LocalityTrackService()
    user_service = UserService()
    locality_service = LocalityService()
    track_service = TrackService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Create test track
    track = await track_service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Test adding track to locality
    await service.add_track_to_locality(test_session, locality.locality_id, track.track_id, user.user_id)
    
    # Verify track was saved to database
    result = await test_session.execute(
        select(LocalityTrack)
        .where(LocalityTrack.locality_id == locality.locality_id)
        .where(LocalityTrack.track_id == track.track_id)
    )
    saved_track = result.scalar_one()
    assert saved_track.locality_id == locality.locality_id
    assert saved_track.track_id == track.track_id
    assert saved_track.user_id == user.user_id
    assert saved_track.total_votes == 0
    
    # Test adding same track again (should not create duplicate)
    await service.add_track_to_locality(test_session, locality.locality_id, track.track_id, user.user_id)
    
    # Verify no duplicate was created
    result = await test_session.execute(
        select(LocalityTrack)
        .where(LocalityTrack.locality_id == locality.locality_id)
        .where(LocalityTrack.track_id == track.track_id)
    )
    saved_tracks = result.scalars().all()
    assert len(saved_tracks) == 1
    assert saved_tracks[0].locality_track_id == saved_track.locality_track_id

@pytest.mark.asyncio
async def test_add_track_to_locality_non_existent_locality(test_session):
    service = LocalityTrackService()
    user_service = UserService()
    track_service = TrackService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    
    # Create test track
    track = await track_service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Test adding track to non-existent locality
    with pytest.raises(Exception) as exc_info:
        await service.add_track_to_locality(test_session, 999, track.track_id, user.user_id)
    assert "Locality not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_add_track_to_locality_non_existent_track(test_session):
    service = LocalityTrackService()
    user_service = UserService()
    locality_service = LocalityService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Test adding non-existent track to locality
    with pytest.raises(Exception) as exc_info:
        await service.add_track_to_locality(test_session, locality.locality_id, 999, user.user_id)
    assert "Track not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_add_track_to_locality_non_existent_user(test_session):
    service = LocalityTrackService()
    locality_service = LocalityService()
    track_service = TrackService()
    
    # Create test data
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Create test track
    track = await track_service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Test adding track with non-existent user
    with pytest.raises(Exception) as exc_info:
        await service.add_track_to_locality(test_session, locality.locality_id, track.track_id, 999)
    assert "User not found" in str(exc_info.value) 