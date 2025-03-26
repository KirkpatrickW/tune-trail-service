import pytest
from pydantic import ValidationError

from app.models.schemas.localities.add_track_to_locality_request import AddTrackToLocalityRequest

def test_valid_add_track_to_locality_request():
    request = AddTrackToLocalityRequest(
        locality_id=1,
        spotify_track_id="valid_spotify_id"
    )
    assert request.locality_id == 1
    assert request.spotify_track_id == "valid_spotify_id"

def test_empty_spotify_track_id():
    with pytest.raises(ValidationError) as exc_info:
        AddTrackToLocalityRequest(
            locality_id=1,
            spotify_track_id=""
        )
    assert "must not be empty" in str(exc_info.value)

def test_whitespace_spotify_track_id():
    with pytest.raises(ValidationError) as exc_info:
        AddTrackToLocalityRequest(
            locality_id=1,
            spotify_track_id="   "
        )
    assert "must not be empty" in str(exc_info.value) 