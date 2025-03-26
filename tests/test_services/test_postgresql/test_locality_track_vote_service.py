import pytest
from sqlalchemy import select

from app.models.postgresql import LocalityTrack, LocalityTrackVote
from app.models.schemas.locality_tracks.vote_on_locality_track_request import VoteValueEnum
from app.services.postgresql.locality_track_vote_service import LocalityTrackVoteService
from app.services.postgresql.locality_track_service import LocalityTrackService
from app.services.postgresql.user_service import UserService
from app.services.postgresql.locality_service import LocalityService
from app.services.postgresql.track_service import TrackService

@pytest.mark.asyncio
async def test_vote_locality_track(test_session):
    service = LocalityTrackVoteService()
    user_service = UserService()
    locality_service = LocalityService()
    track_service = TrackService()
    locality_track_service = LocalityTrackService()
    
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
    
    # Test upvoting
    vote = await service.vote_locality_track(test_session, locality_track.locality_track_id, user.user_id, VoteValueEnum.UPVOTE)
    assert vote.locality_track_id == locality_track.locality_track_id
    assert vote.user_id == user.user_id
    assert vote.vote == VoteValueEnum.UPVOTE.value
    
    # Verify vote was saved to database
    result = await test_session.execute(
        select(LocalityTrackVote)
        .where(LocalityTrackVote.locality_track_id == locality_track.locality_track_id)
        .where(LocalityTrackVote.user_id == user.user_id)
    )
    saved_vote = result.scalar_one()
    assert saved_vote.vote == VoteValueEnum.UPVOTE.value
    
    # Test downvoting (should update existing vote)
    vote = await service.vote_locality_track(test_session, locality_track.locality_track_id, user.user_id, VoteValueEnum.DOWNVOTE)
    assert vote.vote == VoteValueEnum.DOWNVOTE.value
    
    # Verify vote was updated in database
    result = await test_session.execute(
        select(LocalityTrackVote)
        .where(LocalityTrackVote.locality_track_id == locality_track.locality_track_id)
        .where(LocalityTrackVote.user_id == user.user_id)
    )
    saved_vote = result.scalar_one()
    await test_session.refresh(saved_vote)  # Refresh the vote object to get the latest value
    assert saved_vote.vote == VoteValueEnum.DOWNVOTE.value

@pytest.mark.asyncio
async def test_vote_locality_track_invalid_vote(test_session):
    service = LocalityTrackVoteService()
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
    
    # Test invalid vote value
    with pytest.raises(Exception) as exc_info:
        await service.vote_locality_track(test_session, locality_track.locality_track_id, user.user_id, VoteValueEnum.UNVOTE)
    assert "Invalid vote value" in str(exc_info.value)

@pytest.mark.asyncio
async def test_vote_locality_track_non_existent_track(test_session):
    service = LocalityTrackVoteService()
    user_service = UserService()
    
    # Create test user
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    
    # Test voting on non-existent track
    with pytest.raises(Exception) as exc_info:
        await service.vote_locality_track(test_session, 999, user.user_id, VoteValueEnum.UPVOTE)
    assert "Track in locality not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_vote_locality_track_non_existent_user(test_session):
    service = LocalityTrackVoteService()
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
    
    # Add track to locality with a real user
    user_service = UserService()
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality_track = LocalityTrack(
        locality_id=locality.locality_id,
        track_id=track.track_id,
        user_id=user.user_id,
        total_votes=0
    )
    test_session.add(locality_track)
    await test_session.flush()
    
    # Test voting with non-existent user
    with pytest.raises(Exception) as exc_info:
        await service.vote_locality_track(test_session, locality_track.locality_track_id, 999, VoteValueEnum.UPVOTE)
    assert "User not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_unvote_locality_track(test_session):
    service = LocalityTrackVoteService()
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
    
    # Add a vote
    await service.vote_locality_track(test_session, locality_track.locality_track_id, user.user_id, VoteValueEnum.UPVOTE)
    
    # Test unvoting
    await service.unvote_locality_track(test_session, locality_track.locality_track_id, user.user_id)
    
    # Verify vote was removed from database
    result = await test_session.execute(
        select(LocalityTrackVote)
        .where(LocalityTrackVote.locality_track_id == locality_track.locality_track_id)
        .where(LocalityTrackVote.user_id == user.user_id)
    )
    saved_vote = result.scalar_one_or_none()
    assert saved_vote is None

@pytest.mark.asyncio
async def test_unvote_locality_track_non_existent_vote(test_session):
    service = LocalityTrackVoteService()
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
    
    # Test unvoting non-existent vote
    with pytest.raises(Exception) as exc_info:
        await service.unvote_locality_track(test_session, locality_track.locality_track_id, user.user_id)
    assert "Vote on track in locality not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_locality_track_vote_by_user_id_and_locality_track_id(test_session):
    service = LocalityTrackVoteService()
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
    
    # Add a vote
    await service.vote_locality_track(test_session, locality_track.locality_track_id, user.user_id, VoteValueEnum.UPVOTE)
    
    # Test getting the vote
    vote = await service.get_locality_track_vote_by_user_id_and_locality_track_id(test_session, locality_track.locality_track_id, user.user_id)
    assert vote.locality_track_id == locality_track.locality_track_id
    assert vote.user_id == user.user_id
    assert vote.vote == VoteValueEnum.UPVOTE.value
    
    # Test getting non-existent vote
    non_existent_vote = await service.get_locality_track_vote_by_user_id_and_locality_track_id(test_session, locality_track.locality_track_id, 999)
    assert non_existent_vote is None

@pytest.mark.asyncio
async def test_get_all_locality_track_votes_by_user_id_and_locality_id(test_session):
    service = LocalityTrackVoteService()
    user_service = UserService()
    locality_service = LocalityService()
    track_service = TrackService()
    
    # Create test data
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    locality = await locality_service.add_new_locality(test_session, locality_id=1, name="Test Locality", latitude=0.0, longitude=0.0)
    
    # Create test tracks
    track1 = await track_service.add_new_track(
        test_session,
        isrc="test1",
        spotify_id="spotify1",
        deezer_id=1,
        name="Track 1",
        artists=["Artist 1"],
        cover_large="large1.jpg"
    )
    
    track2 = await track_service.add_new_track(
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
        total_votes=0
    )
    locality_track2 = LocalityTrack(
        locality_id=locality.locality_id,
        track_id=track2.track_id,
        user_id=user.user_id,
        total_votes=0
    )
    test_session.add(locality_track1)
    test_session.add(locality_track2)
    await test_session.flush()
    
    # Add votes
    await service.vote_locality_track(test_session, locality_track1.locality_track_id, user.user_id, VoteValueEnum.UPVOTE)
    await service.vote_locality_track(test_session, locality_track2.locality_track_id, user.user_id, VoteValueEnum.DOWNVOTE)
    
    # Test getting all votes
    votes = await service.get_all_locality_track_votes_by_user_id_and_locality_id(test_session, locality.locality_id, user.user_id)
    assert len(votes) == 2
    
    # Verify vote attributes
    vote1 = next(v for v in votes if v.locality_track_id == locality_track1.locality_track_id)
    assert vote1.vote == VoteValueEnum.UPVOTE.value
    
    vote2 = next(v for v in votes if v.locality_track_id == locality_track2.locality_track_id)
    assert vote2.vote == VoteValueEnum.DOWNVOTE.value
    
    # Test getting votes for non-existent locality
    non_existent_votes = await service.get_all_locality_track_votes_by_user_id_and_locality_id(test_session, 999, user.user_id)
    assert len(non_existent_votes) == 0 