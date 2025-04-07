import pytest
from pydantic import ValidationError

from app.models.schemas.search_params import SearchParams

def test_valid_search_params():
    params = SearchParams(q="valid search query")
    assert params.q == "valid search query"
    assert params.offset == 0  # Default value

def test_search_params_with_offset():
    params = SearchParams(q="valid search query", offset=20)
    assert params.q == "valid search query"
    assert params.offset == 20

def test_empty_search_query():
    with pytest.raises(ValidationError) as exc_info:
        SearchParams(q="")
    assert "must not be empty or only whitespace" in str(exc_info.value)

def test_whitespace_search_query():
    with pytest.raises(ValidationError) as exc_info:
        SearchParams(q="   ")
    assert "must not be empty or only whitespace" in str(exc_info.value) 