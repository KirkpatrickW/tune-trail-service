import pytest
from sqlalchemy import select
from fastapi import HTTPException

from app.models.postgresql import Track, LocalityTrack, User
from app.services.postgresql.track_service import TrackService
from app.services.postgresql.user_service import UserService
from app.services.postgresql.locality_service import LocalityService

@pytest.mark.asyncio
async def test_add_new_track(test_session):
    service = TrackService()
    
    # Test adding a new track
    isrc = "test123"
    spotify_id = "spotify123"
    deezer_id = 123456
    name = "Test Track"
    artists = ["Test Artist"]
    cover_large = "large.jpg"
    cover_medium = "medium.jpg"
    cover_small = "small.jpg"
    
    track = await service.add_new_track(
        test_session,
        isrc=isrc,
        spotify_id=spotify_id,
        deezer_id=deezer_id,
        name=name,
        artists=artists,
        cover_large=cover_large,
        cover_medium=cover_medium,
        cover_small=cover_small
    )
    
    assert track.track_id is not None
    assert track.isrc == isrc
    assert track.spotify_id == spotify_id
    assert track.deezer_id == deezer_id
    assert track.name == name
    assert track.artists == artists
    assert track.cover_large == cover_large
    assert track.cover_medium == cover_medium
    assert track.cover_small == cover_small
    
    # Verify track was saved to database
    result = await test_session.execute(select(Track).where(Track.track_id == track.track_id))
    saved_track = result.scalar_one()
    assert saved_track.track_id == track.track_id
    assert saved_track.isrc == track.isrc
    assert saved_track.spotify_id == track.spotify_id
    assert saved_track.deezer_id == track.deezer_id
    assert saved_track.name == track.name
    assert saved_track.artists == track.artists
    assert saved_track.cover_large == track.cover_large
    assert saved_track.cover_medium == track.cover_medium
    assert saved_track.cover_small == track.cover_small

@pytest.mark.asyncio
async def test_add_new_track_duplicate(test_session):
    service = TrackService()
    
    # Create a test track
    isrc = "test123"
    spotify_id = "spotify123"
    deezer_id = 123456
    name = "Test Track"
    artists = ["Test Artist"]
    cover_large = "large.jpg"
    
    await service.add_new_track(
        test_session,
        isrc=isrc,
        spotify_id=spotify_id,
        deezer_id=deezer_id,
        name=name,
        artists=artists,
        cover_large=cover_large
    )
    
    # Try to add the same track again
    with pytest.raises(Exception) as exc_info:
        await service.add_new_track(
            test_session,
            isrc=isrc,
            spotify_id=spotify_id,
            deezer_id=deezer_id,
            name=name,
            artists=artists,
            cover_large=cover_large
        )
    assert "Track already exists" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_track_by_track_id(test_session):
    service = TrackService()
    
    # Create a test track
    isrc = "test123"
    spotify_id = "spotify123"
    deezer_id = 123456
    name = "Test Track"
    artists = ["Test Artist"]
    cover_large = "large.jpg"
    
    track = await service.add_new_track(
        test_session,
        isrc=isrc,
        spotify_id=spotify_id,
        deezer_id=deezer_id,
        name=name,
        artists=artists,
        cover_large=cover_large
    )
    
    # Test getting the track
    found_track = await service.get_track_by_track_id(test_session, track.track_id)
    assert found_track.track_id == track.track_id
    assert found_track.isrc == track.isrc
    assert found_track.spotify_id == track.spotify_id
    assert found_track.deezer_id == track.deezer_id
    assert found_track.name == track.name
    assert found_track.artists == track.artists
    assert found_track.cover_large == track.cover_large
    
    # Test getting non-existent track
    non_existent_track = await service.get_track_by_track_id(test_session, 999)
    assert non_existent_track is None

@pytest.mark.asyncio
async def test_get_track_by_spotify_id(test_session):
    service = TrackService()
    
    # Create a test track
    isrc = "test123"
    spotify_id = "spotify123"
    deezer_id = 123456
    name = "Test Track"
    artists = ["Test Artist"]
    cover_large = "large.jpg"
    
    track = await service.add_new_track(
        test_session,
        isrc=isrc,
        spotify_id=spotify_id,
        deezer_id=deezer_id,
        name=name,
        artists=artists,
        cover_large=cover_large
    )
    
    # Test getting the track
    found_track = await service.get_track_by_spotify_id(test_session, spotify_id)
    assert found_track.track_id == track.track_id
    assert found_track.isrc == track.isrc
    assert found_track.spotify_id == track.spotify_id
    assert found_track.deezer_id == track.deezer_id
    assert found_track.name == track.name
    assert found_track.artists == track.artists
    assert found_track.cover_large == track.cover_large
    
    # Test getting non-existent track
    non_existent_track = await service.get_track_by_spotify_id(test_session, "nonexistent")
    assert non_existent_track is None

@pytest.mark.asyncio
async def test_get_tracks_in_locality(test_session):
    service = TrackService()
    user_service = UserService()
    locality_service = LocalityService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Create test tracks
    track1 = await service.add_new_track(
        test_session,
        isrc="test1",
        spotify_id="spotify1",
        deezer_id=1,
        name="Track 1",
        artists=["Artist 1"],
        cover_large="large1.jpg"
    )
    
    track2 = await service.add_new_track(
        test_session,
        isrc="test2",
        spotify_id="spotify2",
        deezer_id=2,
        name="Track 2",
        artists=["Artist 2"],
        cover_large="large2.jpg"
    )
    
    # Add tracks to locality
    locality_track1 = LocalityTrack(
        locality_id=locality.locality_id,
        track_id=track1.track_id,
        user_id=user.user_id,
        total_votes=2
    )
    locality_track2 = LocalityTrack(
        locality_id=locality.locality_id,
        track_id=track2.track_id,
        user_id=user.user_id,
        total_votes=1
    )
    test_session.add(locality_track1)
    test_session.add(locality_track2)
    await test_session.flush()
    
    # Test getting tracks in locality
    tracks = await service.get_tracks_in_locality(test_session, locality.locality_id)
    assert len(tracks) == 2
    
    # Verify track attributes
    assert tracks[0].track_id == track1.track_id  # Should be first due to higher votes
    assert tracks[0].total_votes == 2
    assert tracks[0].username == user.username
    assert tracks[0].user_id == user.user_id
    
    assert tracks[1].track_id == track2.track_id
    assert tracks[1].total_votes == 1
    assert tracks[1].username == user.username
    assert tracks[1].user_id == user.user_id
    
    # Test getting tracks for non-existent locality
    with pytest.raises(HTTPException) as exc_info:
        await service.get_tracks_in_locality(test_session, 999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Locality not found"

@pytest.mark.asyncio
async def test_get_all_banned_tracks(test_session):
    service = TrackService()
    
    # Create test tracks
    track1 = await service.add_new_track(
        test_session,
        isrc="test1",
        spotify_id="spotify1",
        deezer_id=1,
        name="Track 1",
        artists=["Artist 1"],
        cover_large="large1.jpg"
    )
    
    track2 = await service.add_new_track(
        test_session,
        isrc="test2",
        spotify_id="spotify2",
        deezer_id=2,
        name="Track 2",
        artists=["Artist 2"],
        cover_large="large2.jpg"
    )
    
    # Ban track1
    track1.is_banned = True
    await test_session.flush()
    
    # Get all banned tracks
    banned_tracks = await service.get_all_banned_tracks(test_session)
    
    # Verify results
    assert len(banned_tracks) == 1
    assert banned_tracks[0].track_id == track1.track_id
    assert banned_tracks[0].is_banned == True
    assert track2.track_id not in [t.track_id for t in banned_tracks]

@pytest.mark.asyncio
async def test_ban_track_by_track_id(test_session):
    service = TrackService()
    
    # Create a test track
    track = await service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Ban the track
    banned_track = await service.ban_track_by_track_id(test_session, track.track_id)
    
    # Verify the track is banned
    assert banned_track.is_banned == True
    
    # Try to ban a non-existent track
    with pytest.raises(HTTPException) as exc_info:
        await service.ban_track_by_track_id(test_session, 999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Track not found"
    
    # Try to ban an already banned track
    banned_track = await service.ban_track_by_track_id(test_session, track.track_id)
    assert banned_track.is_banned == True  # Should still be banned

@pytest.mark.asyncio
async def test_unban_track_by_track_id(test_session):
    service = TrackService()
    
    # Create a test track
    track = await service.add_new_track(
        test_session,
        isrc="test123",
        spotify_id="spotify123",
        deezer_id=123456,
        name="Test Track",
        artists=["Test Artist"],
        cover_large="large.jpg"
    )
    
    # Ban the track first
    track.is_banned = True
    await test_session.flush()
    
    # Unban the track
    unbanned_track = await service.unban_track_by_track_id(test_session, track.track_id)
    
    # Verify the track is unbanned
    assert unbanned_track.is_banned == False
    
    # Try to unban a non-existent track
    with pytest.raises(HTTPException) as exc_info:
        await service.unban_track_by_track_id(test_session, 999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Track not found"
    
    # Try to unban an already unbanned track
    unbanned_track = await service.unban_track_by_track_id(test_session, track.track_id)
    assert unbanned_track.is_banned == False  # Should still be unbanned 