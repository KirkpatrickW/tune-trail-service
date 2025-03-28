import pytest
from pydantic import ValidationError

from app.models.schemas.localities.user_location_params import UserLocationParams

def test_valid_user_location_params():
    params = UserLocationParams(
        latitude=45.0,
        longitude=120.0,
        radius=1000.0
    )
    assert params.latitude == 45.0
    assert params.longitude == 120.0
    assert params.radius == 1000.0

def test_invalid_latitude():
    with pytest.raises(ValidationError) as exc_info:
        UserLocationParams(
            latitude=91.0,  # Invalid latitude
            longitude=120.0,
            radius=1000.0
        )
    assert "must be between -90 and 90" in str(exc_info.value)

def test_invalid_longitude():
    with pytest.raises(ValidationError) as exc_info:
        UserLocationParams(
            latitude=45.0,
            longitude=181.0,  # Invalid longitude
            radius=1000.0
        )
    assert "must be between -180 and 180" in str(exc_info.value)

def test_radius_too_small():
    with pytest.raises(ValidationError) as exc_info:
        UserLocationParams(
            latitude=45.0,
            longitude=120.0,
            radius=50.0  # Too small radius
        )
    assert "must be greater than 100 meters" in str(exc_info.value)

def test_radius_too_large():
    with pytest.raises(ValidationError) as exc_info:
        UserLocationParams(
            latitude=45.0,
            longitude=120.0,
            radius=11000.0  # Too large radius
        )
    assert "must be less than or equal to 10,000 meters" in str(exc_info.value)

def test_edge_cases():
    # Test minimum valid values
    params_min = UserLocationParams(
        latitude=-90.0,
        longitude=-180.0,
        radius=100.0
    )
    assert params_min.latitude == -90.0
    assert params_min.longitude == -180.0
    assert params_min.radius == 100.0

    # Test maximum valid values
    params_max = UserLocationParams(
        latitude=90.0,
        longitude=180.0,
        radius=10000.0
    )
    assert params_max.latitude == 90.0
    assert params_max.longitude == 180.0
    assert params_max.radius == 10000.0 