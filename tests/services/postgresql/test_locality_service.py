import pytest
from sqlalchemy import select

from app.models.postgresql import Locality
from app.services.postgresql.locality_service import LocalityService

@pytest.mark.asyncio
async def test_get_locality_by_locality_id(test_session):
    service = LocalityService()
    
    # Create test locality
    locality = await service.add_new_locality(
        test_session,
        locality_id=1,
        name="Test Locality",
        latitude=0.0,
        longitude=0.0
    )
    
    # Test getting the locality
    result = await service.get_locality_by_locality_id(test_session, locality.locality_id)
    assert result.locality_id == locality.locality_id
    assert result.name == "Test Locality"
    assert result.latitude == 0.0
    assert result.longitude == 0.0
    assert result.total_tracks == 0
    
    # Test getting non-existent locality
    non_existent = await service.get_locality_by_locality_id(test_session, 999)
    assert non_existent is None

@pytest.mark.asyncio
async def test_add_new_locality(test_session):
    service = LocalityService()
    
    # Test adding new locality
    locality = await service.add_new_locality(
        test_session,
        locality_id=1,
        name="Test Locality",
        latitude=0.0,
        longitude=0.0
    )
    
    # Verify locality was saved to database
    result = await test_session.execute(
        select(Locality)
        .where(Locality.locality_id == locality.locality_id)
    )
    saved_locality = result.scalar_one()
    assert saved_locality.locality_id == 1
    assert saved_locality.name == "Test Locality"
    assert saved_locality.latitude == 0.0
    assert saved_locality.longitude == 0.0
    assert saved_locality.total_tracks == 0
    
    # Test adding locality with same ID (should fail)
    with pytest.raises(Exception) as exc_info:
        await service.add_new_locality(
            test_session,
            locality_id=1,  # Same ID
            name="Another Locality",
            latitude=1.0,
            longitude=1.0
        )
    assert "Locality already exists" in str(exc_info.value)
    
    # Verify original locality wasn't modified
    result = await test_session.execute(
        select(Locality)
        .where(Locality.locality_id == 1)
    )
    saved_locality = result.scalar_one()
    assert saved_locality.name == "Test Locality"
    assert saved_locality.latitude == 0.0
    assert saved_locality.longitude == 0.0

@pytest.mark.asyncio
async def test_add_new_locality_invalid_coordinates(test_session):
    service = LocalityService()
    
    # Test adding locality with invalid latitude (> 90)
    with pytest.raises(Exception) as exc_info:
        await service.add_new_locality(
            test_session,
            locality_id=1,
            name="Invalid Locality",
            latitude=91.0,  # Invalid latitude
            longitude=0.0
        )
    error_msg = str(exc_info.value)
    if "Original exception was:" in error_msg:
        error_msg = error_msg.split("Original exception was:")[1]
    assert "violates check constraint" in error_msg
    assert "localities_latitude_check" in error_msg
    
    # Test adding locality with invalid latitude (< -90)
    with pytest.raises(Exception) as exc_info:
        await service.add_new_locality(
            test_session,
            locality_id=1,
            name="Invalid Locality",
            latitude=-91.0,  # Invalid latitude
            longitude=0.0
        )
    error_msg = str(exc_info.value)
    if "Original exception was:" in error_msg:
        error_msg = error_msg.split("Original exception was:")[1]
    assert "violates check constraint" in error_msg
    assert "localities_latitude_check" in error_msg
    
    # Test adding locality with invalid longitude (> 180)
    with pytest.raises(Exception) as exc_info:
        await service.add_new_locality(
            test_session,
            locality_id=1,
            name="Invalid Locality",
            latitude=0.0,
            longitude=181.0  # Invalid longitude
        )
    error_msg = str(exc_info.value)
    if "Original exception was:" in error_msg:
        error_msg = error_msg.split("Original exception was:")[1]
    assert "violates check constraint" in error_msg
    assert "localities_latitude_check" in error_msg
    
    # Test adding locality with invalid longitude (< -180)
    with pytest.raises(Exception) as exc_info:
        await service.add_new_locality(
            test_session,
            locality_id=1,
            name="Invalid Locality",
            latitude=0.0,
            longitude=-181.0  # Invalid longitude
        )
    error_msg = str(exc_info.value)
    if "Original exception was:" in error_msg:
        error_msg = error_msg.split("Original exception was:")[1]
    assert "violates check constraint" in error_msg
    assert "localities_latitude_check" in error_msg

@pytest.mark.asyncio
async def test_get_localities_by_bounds(test_session):
    service = LocalityService()
    
    # Create test localities
    localities = [
        await service.add_new_locality(test_session, 1, "Locality 1", 0.0, 0.0),    # Center
        await service.add_new_locality(test_session, 2, "Locality 2", 1.0, 1.0),    # Northeast
        await service.add_new_locality(test_session, 3, "Locality 3", -1.0, -1.0),  # Southwest
        await service.add_new_locality(test_session, 4, "Locality 4", 2.0, 2.0),    # Outside bounds
    ]
    
    # Test getting localities within bounds
    result = await service.get_localities_by_bounds(
        test_session,
        north=1.5,   # Include Locality 2
        east=1.5,    # Include Locality 2
        south=-1.5,  # Include Locality 3
        west=-1.5    # Include Locality 3
    )
    
    # Verify results
    assert len(result) == 3  # Should include Localities 1, 2, and 3
    locality_ids = {loc.locality_id for loc in result}
    assert locality_ids == {1, 2, 3}  # Should not include Locality 4
    
    # Test getting localities with no matches
    empty_result = await service.get_localities_by_bounds(
        test_session,
        north=0.5,   # Only include part of Locality 1
        east=0.5,    # Only include part of Locality 1
        south=0.0,   # Only include part of Locality 1
        west=0.0     # Only include part of Locality 1
    )
    assert len(empty_result) == 1  # Locality 1 intersects with these bounds
    assert empty_result[0].locality_id == 1  # Should be Locality 1 