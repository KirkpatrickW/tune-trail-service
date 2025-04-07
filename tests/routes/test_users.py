import pytest
from unittest.mock import AsyncMock, patch
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from httpx import AsyncClient, ASGITransport
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.models.postgresql import User
from app.utils.jwt_helper import create_access_token
from sqlalchemy import text

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.users import postgresql_client

    async def override_get_session():
        yield test_session

    # Dependencies will be the death of me
    app.dependency_overrides[postgresql_client.get_session] = override_get_session

    FastAPICache.init(InMemoryBackend())
    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture
def admin_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=True,
        spotify_access_token="test_spotify_token"
    )

@pytest.fixture
def regular_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )

@pytest.mark.asyncio
async def test_search_users_success(test_client, test_session, admin_token):
    # Create test users
    users = []
    for i in range(5):
        user = User(
            user_id=i+1,
            username=f"testuser{i}",
            is_oauth_account=False,
            is_admin=False
        )
        test_session.add(user)
        users.append(user)
    
    # Add some users with different usernames
    other_users = []
    for i in range(3):
        user = User(
            user_id=i+10,
            username=f"otheruser{i}",
            is_oauth_account=False,
            is_admin=False
        )
        test_session.add(user)
        other_users.append(user)
    
    await test_session.commit()
    
    # Test searching for users with "test" in username
    response = await test_client.get(
        "/users/search?q=test&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 5
    assert len(data["users"]) == 5
    assert data["next_offset"] is None  # No more results
    
    # Test searching with offset
    response = await test_client.get(
        "/users/search?q=test&offset=3",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 5
    assert len(data["users"]) == 2
    assert data["next_offset"] is None  # No more results
    
    # Test searching for users with "other" in username
    response = await test_client.get(
        "/users/search?q=other&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 3
    assert len(data["users"]) == 3
    assert data["next_offset"] is None  # No more results

@pytest.mark.asyncio
async def test_search_users_unauthorized(test_client, regular_token):
    # Test that regular users cannot search for users
    response = await test_client.get(
        "/users/search?q=test&offset=0",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

@pytest.mark.asyncio
async def test_search_users_not_authenticated(test_client):
    # Test that unauthenticated users cannot search for users
    response = await test_client.get("/users/search?q=test&offset=0")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_search_users_empty_results(test_client, test_session, admin_token):
    # Test searching for non-existent users
    response = await test_client.get(
        "/users/search?q=nonexistent&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_matching_results"] == 0
    assert len(data["users"]) == 0
    assert data["next_offset"] is None

@pytest.mark.asyncio
async def test_delete_user_success(test_client, test_session, admin_token):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Delete the user
    response = await test_client.delete(
        f"/users/{user.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully deleted user"
    
    # Verify user no longer exists in database
    result = await test_session.execute(text(f"SELECT * FROM users WHERE user_id = {user.user_id}"))
    assert result.fetchone() is None

@pytest.mark.asyncio
async def test_delete_user_unauthorized(test_client, test_session, regular_token):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Test that regular users cannot delete users
    response = await test_client.delete(
        f"/users/{user.user_id}",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
    
    # Verify user still exists in database
    result = await test_session.execute(text(f"SELECT * FROM users WHERE user_id = {user.user_id}"))
    assert result.fetchone() is not None

@pytest.mark.asyncio
async def test_delete_user_not_authenticated(test_client, test_session):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Test that unauthenticated users cannot delete users
    response = await test_client.delete(f"/users/{user.user_id}")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"
    
    # Verify user still exists in database
    result = await test_session.execute(text(f"SELECT * FROM users WHERE user_id = {user.user_id}"))
    assert result.fetchone() is not None

@pytest.mark.asyncio
async def test_delete_user_not_found(test_client, admin_token):
    # Test deleting a non-existent user
    response = await test_client.delete(
        "/users/999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

@pytest.mark.asyncio
async def test_invalidate_user_sessions_success(test_client, test_session, admin_token):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Invalidate user sessions
    response = await test_client.patch(
        f"/users/{user.user_id}/invalidate-session",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == f"Successfully invalidated all sessions for {user.username}"

@pytest.mark.asyncio
async def test_invalidate_user_sessions_unauthorized(test_client, test_session, regular_token):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Test that regular users cannot invalidate sessions
    response = await test_client.patch(
        f"/users/{user.user_id}/invalidate-session",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

@pytest.mark.asyncio
async def test_invalidate_user_sessions_not_authenticated(test_client, test_session):
    # Create a test user
    user = User(
        user_id=1,
        username="testuser",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Test that unauthenticated users cannot invalidate sessions
    response = await test_client.patch(f"/users/{user.user_id}/invalidate-session")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_invalidate_user_sessions_not_found(test_client, admin_token):
    # Test invalidating sessions for a non-existent user
    response = await test_client.patch(
        "/users/999/invalidate-session",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found" 