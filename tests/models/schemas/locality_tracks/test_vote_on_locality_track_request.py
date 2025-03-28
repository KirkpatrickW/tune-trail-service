import pytest
from pydantic import ValidationError

from app.models.schemas.locality_tracks.vote_on_locality_track_request import VoteOnTrackLocalityRequest

def test_valid_upvote():
    request = VoteOnTrackLocalityRequest(vote_value=1)
    assert request.vote_value == 1

def test_valid_downvote():
    request = VoteOnTrackLocalityRequest(vote_value=-1)
    assert request.vote_value == -1

def test_valid_unvote():
    request = VoteOnTrackLocalityRequest(vote_value=0)
    assert request.vote_value == 0

def test_invalid_vote_value():
    with pytest.raises(ValidationError) as exc_info:
        VoteOnTrackLocalityRequest(vote_value=2)  # Invalid value
    assert "must be 1 (UPVOTE), -1 (DOWNVOTE), or 0 (UNVOTE)" in str(exc_info.value) 