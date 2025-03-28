import pytest
from pydantic import ValidationError

from app.models.schemas.auth.spotify_oauth_request import SpotifyOAuthRequest

def test_valid_spotify_oauth_request():
    request = SpotifyOAuthRequest(auth_code="valid_auth_code")
    assert request.auth_code == "valid_auth_code"

def test_empty_auth_code():
    with pytest.raises(ValidationError) as exc_info:
        SpotifyOAuthRequest(auth_code="")
    assert "must not be empty" in str(exc_info.value)

def test_whitespace_auth_code():
    with pytest.raises(ValidationError) as exc_info:
        SpotifyOAuthRequest(auth_code="   ")
    assert "must not be empty" in str(exc_info.value) 