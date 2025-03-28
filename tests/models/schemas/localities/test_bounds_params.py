import pytest
from pydantic import ValidationError

from app.models.schemas.localities.bounds_params import BoundsParams

def test_valid_bounds_params():
    params = BoundsParams(
        north=45.0,
        east=120.0,
        south=30.0,
        west=100.0
    )
    assert params.north == 45.0
    assert params.east == 120.0
    assert params.south == 30.0
    assert params.west == 100.0

def test_invalid_latitude_north():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=91.0,
            east=120.0,
            south=30.0,
            west=100.0
        )
    assert "must be between -90 and 90" in str(exc_info.value)

def test_invalid_latitude_south():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=45.0,
            east=120.0,
            south=-91.0,
            west=100.0
        )
    assert "must be between -90 and 90" in str(exc_info.value)

def test_invalid_longitude_east():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=45.0,
            east=181.0,
            south=30.0,
            west=100.0
        )
    assert "must be between -180 and 180" in str(exc_info.value)

def test_invalid_longitude_west():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=45.0,
            east=120.0,
            south=30.0,
            west=-181.0
        )
    assert "must be between -180 and 180" in str(exc_info.value)

def test_north_less_than_south():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=30.0,
            east=120.0,
            south=45.0,
            west=100.0
        )
    assert "north must be greater than south" in str(exc_info.value)

def test_east_less_than_west():
    with pytest.raises(ValidationError) as exc_info:
        BoundsParams(
            north=45.0,
            east=100.0,
            south=30.0,
            west=120.0
        )
    assert "east must be greater than west" in str(exc_info.value) 