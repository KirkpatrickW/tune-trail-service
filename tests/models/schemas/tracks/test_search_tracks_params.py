import pytest
from pydantic import ValidationError

from app.models.schemas.tracks.search_tracks_params import SearchTracksParams

def test_valid_search_tracks_params():
    params = SearchTracksParams(q="valid search query")
    assert params.q == "valid search query"
    assert params.offset == 0  # Default value

def test_search_tracks_params_with_offset():
    params = SearchTracksParams(q="valid search query", offset=20)
    assert params.q == "valid search query"
    assert params.offset == 20

def test_empty_search_query():
    with pytest.raises(ValidationError) as exc_info:
        SearchTracksParams(q="")
    assert "must not be empty or only whitespace" in str(exc_info.value)

def test_whitespace_search_query():
    with pytest.raises(ValidationError) as exc_info:
        SearchTracksParams(q="   ")
    assert "must not be empty or only whitespace" in str(exc_info.value) 