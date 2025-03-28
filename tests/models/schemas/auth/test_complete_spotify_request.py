import pytest
from pydantic import ValidationError

from app.models.schemas.auth.complete_spotify_request import CompleteSpotifyRequest

def test_valid_complete_spotify_request():
    request = CompleteSpotifyRequest(username="valid_user123")
    assert request.username == "valid_user123"

def test_username_too_short():
    with pytest.raises(ValidationError) as exc_info:
        CompleteSpotifyRequest(username="ab")
    assert "must be at least 3 characters long" in str(exc_info.value)

def test_username_too_long():
    with pytest.raises(ValidationError) as exc_info:
        CompleteSpotifyRequest(username="a" * 21)
    assert "must be at most 20 characters long" in str(exc_info.value)

def test_username_invalid_chars():
    with pytest.raises(ValidationError) as exc_info:
        CompleteSpotifyRequest(username="valid-user@123")
    assert "can only contain alphanumeric characters and underscores" in str(exc_info.value) 