import pytest
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from httpx import AsyncClient, BasicAuth
from httpx import ASGITransport
from app.models.postgresql import User, UserSpotifyOauthAccount, UserSession
from app.utils.jwt_helper import create_access_token, SECRET_KEY, ALGORITHM
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
import jwt

with patch('app.services.providers.spotify_service.SpotifyService') as mock_spotify:
    from app.routes.auth import spotify_service

@pytest.fixture
def mock_spotify_service():
    instance = AsyncMock()
    instance.fetch_and_handle_oauth_token = AsyncMock()
    instance.renew_user_access_token = AsyncMock()
    instance.fetch_and_handle_oauth_token.return_value = {
        "provider_user_id": "new_provider_user_id",
        "subscription": "free",
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in_seconds": 3600
    }
    instance.renew_user_access_token.return_value = {
        "access_token": "renewed_access_token",
        "expires_in_seconds": 3600,
        "subscription": "premium"
    }
    spotify_service.fetch_and_handle_oauth_token = instance.fetch_and_handle_oauth_token
    spotify_service.renew_user_access_token = instance.renew_user_access_token
    yield instance

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.auth import postgresql_client

    async def override_get_session():
        yield test_session

    # Dependencies will be the death of me
    app.dependency_overrides[postgresql_client.get_session] = override_get_session

    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()

@pytest.fixture
def test_token():
    return create_access_token(
        user_id=1,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )

@pytest.mark.asyncio
async def test_register_success(test_client, test_session):
    register_data = {
        "username": "newuser",
        "password": "Strongpassword123!"
    }
    
    response = await test_client.post("/auth/register", json=register_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    
    # Verify user was created in database
    user = await test_session.get(User, 1)  # First user should have ID 1
    assert user is not None
    assert user.username == register_data["username"]
    assert user.is_oauth_account is False
    assert user.is_admin is False

@pytest.mark.asyncio
async def test_register_duplicate_username(test_client, test_session):
    register_data = {
        "username": "duplicateuser",
        "password": "Strongpassword123!"
    }
    await test_client.post("/auth/register", json=register_data)
    
    # Try to register another user with same username
    duplicate_data = {
        "username": "duplicateuser",
        "password": "Strongpassword456!"
    }
    response = await test_client.post("/auth/register", json=duplicate_data)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"

@pytest.mark.asyncio
async def test_register_invalid_password(test_client, test_session):
    register_data = {
        "username": "newuser",
        "password": "weak"  # Too short
    }
    
    response = await test_client.post("/auth/register", json=register_data)
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("password" in error["loc"] and "must be at least 8 characters long" in error["msg"] for error in error_detail)

@pytest.mark.asyncio
async def test_register_missing_fields(test_client, test_session):
    # Missing password
    response = await test_client.post("/auth/register", json={"username": "newuser"})
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("password" in error["loc"] and "Field required" in error["msg"] for error in error_detail)
    
    # Missing username
    response = await test_client.post("/auth/register", json={"password": "Strongpassword123!"})
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("username" in error["loc"] and "Field required" in error["msg"] for error in error_detail)

@pytest.mark.asyncio
async def test_login_success(test_client, test_session):
    # First register a user
    register_data = {
        "username": "loginuser",
        "password": "Strongpassword123!"
    }
    await test_client.post("/auth/register", json=register_data)
    
    # Try to login
    response = await test_client.post(
        "/auth/login",
        auth=BasicAuth("loginuser", "Strongpassword123!")
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None

@pytest.mark.asyncio
async def test_login_invalid_username(test_client, test_session):
    response = await test_client.post(
        "/auth/login",
        auth=BasicAuth("nonexistentuser", "Strongpassword123!")
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Bad Username"

@pytest.mark.asyncio
async def test_login_wrong_password(test_client, test_session):
    # First register a user
    register_data = {
        "username": "wrongpassuser",
        "password": "Strongpassword123!"
    }
    await test_client.post("/auth/register", json=register_data)
    
    # Try to login with wrong password
    response = await test_client.post(
        "/auth/login",
        auth=BasicAuth("wrongpassuser", "Wrongpassword123!")
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Bad Password"

@pytest.mark.asyncio
async def test_login_missing_credentials(test_client, test_session):
    response = await test_client.post("/auth/login")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_login_oauth_user(test_client, test_session):
    # Create an OAuth user
    oauth_user = User(
        username="oauthuser",
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(oauth_user)
    await test_session.commit()
    
    # Try to login with password
    response = await test_client.post(
        "/auth/login",
        auth=BasicAuth("oauthuser", "Strongpassword123!")
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "This account was created using Spotify OAuth. Please log in with Spotify"

@pytest.mark.asyncio
async def test_connect_spotify_new_user(test_client, test_session, mock_spotify_service):
    response = await test_client.put("/auth/connect-spotify", json={"auth_code": "test_auth_code"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    
    # Get user_id from the token
    user_id = data["user_details"]["user_id"]
    
    # Verify user was created in database
    user = await test_session.get(User, user_id)
    assert user is not None
    assert user.username == None # Must set username later # From mock_spotify_service
    assert user.is_oauth_account is True
    assert user.is_admin is False
    
    # Verify Spotify account was created
    result = await test_session.execute(
        select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user_id)
    )
    spotify_account = result.scalar_one_or_none()
    assert spotify_account is not None
    assert spotify_account.user_id == user_id
    assert spotify_account.provider_user_id == "new_provider_user_id"
    assert spotify_account.subscription == "free"  # From mock_spotify_service

@pytest.mark.asyncio
async def test_connect_spotify_existing_oauth_user(test_client, test_session, mock_spotify_service):
    # Create an existing OAuth user
    oauth_user = User(
        username="test_spotify_id",
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(oauth_user)
    await test_session.commit()
    
    response = await test_client.put("/auth/connect-spotify", json={"auth_code": "test_auth_code"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None

@pytest.mark.asyncio
async def test_connect_spotify_existing_password_user(test_client, test_session, mock_spotify_service):
    # Create an existing password user with Spotify account
    password_user = User(
        username="test_spotify_id",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(password_user)
    await test_session.commit()
    
    spotify_account = UserSpotifyOauthAccount(
        user_id=password_user.user_id,
        provider_user_id="new_provider_user_id",
        encrypted_access_token="test_access_token",
        encrypted_refresh_token="test_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    test_session.add(spotify_account)
    await test_session.commit()
    
    response = await test_client.put("/auth/connect-spotify", json={"auth_code": "test_auth_code"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "This Spotify account is linked to a non-OAuth account"

@pytest.mark.asyncio
async def test_connect_spotify_missing_code(test_client, test_session, mock_spotify_service):
    response = await test_client.put("/auth/connect-spotify", json={})
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("auth_code" in error["loc"] and "Field required" in error["msg"] for error in error_detail)

@pytest.mark.asyncio
async def test_link_spotify_success(test_client, test_session, mock_spotify_service):
    # Create a regular user
    user = User(
        username="linkuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token for the actual user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Link Spotify account
    response = await test_client.put(
        "/auth/link-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"auth_code": "test_auth_code"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_details"]["spotify_subscription"] == "free"
    
    # Verify Spotify account was created
    result = await test_session.execute(
        select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user.user_id)
    )
    spotify_account = result.scalar_one_or_none()
    assert spotify_account is not None
    assert spotify_account.user_id == user.user_id
    assert spotify_account.provider_user_id == "new_provider_user_id"
    assert spotify_account.subscription == "free"

@pytest.mark.asyncio
async def test_link_spotify_existing_spotify_account(test_client, test_session, mock_spotify_service):
    # Create a user with existing Spotify account
    user = User(
        username="existinguser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    spotify_account = UserSpotifyOauthAccount(
        user_id=user.user_id,
        provider_user_id="existing_spotify_id",
        encrypted_access_token="test_access_token",
        encrypted_refresh_token="test_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    test_session.add(spotify_account)
    await test_session.commit()
    
    # Create a token for the actual user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/link-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"auth_code": "test_auth_code"}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "A Spotify account is already linked to this user"

@pytest.mark.asyncio
async def test_link_spotify_missing_code(test_client, test_session, mock_spotify_service, test_token):
    response = await test_client.put(
        "/auth/link-spotify",
        headers={"Authorization": f"Bearer {test_token}"},
        json={}
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("auth_code" in error["loc"] and "Field required" in error["msg"] for error in error_detail)

@pytest.mark.asyncio
async def test_link_spotify_missing_auth(test_client, test_session, mock_spotify_service):
    response = await test_client.put(
        "/auth/link-spotify",
        json={"auth_code": "test_auth_code"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_link_spotify_account_already_linked_to_other_user(test_client, test_session, mock_spotify_service):
    # Create first user with Spotify account
    first_user = User(
        username="firstuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(first_user)
    await test_session.commit()
    
    first_spotify = UserSpotifyOauthAccount(
        user_id=first_user.user_id,
        provider_user_id="existing_spotify_id",
        encrypted_access_token="test_access_token",
        encrypted_refresh_token="test_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    test_session.add(first_spotify)
    await test_session.commit()
    
    # Create second user
    second_user = User(
        username="seconduser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(second_user)
    await test_session.commit()
    
    # Mock Spotify service to return the same provider_user_id as first user
    mock_spotify_service.fetch_and_handle_oauth_token.return_value = {
        "provider_user_id": "existing_spotify_id",  # Same as first user's Spotify account
        "subscription": "free",
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in_seconds": 3600
    }
    
    # Create a token for the second user
    token = create_access_token(
        user_id=second_user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/link-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"auth_code": "test_auth_code"}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "This Spotify account is already associated with a user"

@pytest.mark.asyncio
async def test_complete_spotify_success(test_client, test_session, mock_spotify_service):
    # Create a new OAuth user without username
    user = User(
        username=None,
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token for the actual user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Set username
    response = await test_client.put(
        "/auth/complete-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "newusername"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_details"]["username"] == "newusername"
    
    # Verify user was updated in database
    await test_session.refresh(user)
    updated_user = await test_session.get(User, user.user_id)
    assert updated_user.username == "newusername"

@pytest.mark.asyncio
async def test_complete_spotify_existing_username(test_client, test_session, mock_spotify_service):
    # Create a user with the username we'll try to use
    existing_user = User(
        username="existinguser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(existing_user)
    await test_session.commit()
    
    # Create a new OAuth user without username
    oauth_user = User(
        username=None,
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(oauth_user)
    await test_session.commit()
    
    # Create a token for the OAuth user
    token = create_access_token(
        user_id=oauth_user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/complete-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "existinguser"}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already taken"

@pytest.mark.asyncio
async def test_complete_spotify_missing_username(test_client, test_session, mock_spotify_service):
    # Create a new OAuth user without username
    user = User(
        username=None,
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token for the actual user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/complete-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={}
    )
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("username" in error["loc"] and "Field required" in error["msg"] for error in error_detail)

@pytest.mark.asyncio
async def test_complete_spotify_missing_auth(test_client, test_session, mock_spotify_service):
    response = await test_client.put(
        "/auth/complete-spotify",
        json={"username": "newusername"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_complete_spotify_non_oauth_user(test_client, test_session, mock_spotify_service):
    # Create a regular password user
    user = User(
        username="passworduser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token for the user without Spotify access token
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token=None
    )
    
    response = await test_client.put(
        "/auth/complete-spotify",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "newusername"}
    )
    
    assert response.status_code == 409
    assert response.json()["detail"] == "Spotify account must be linked"

@pytest.mark.asyncio
async def test_unlink_spotify_success(test_client, test_session, mock_spotify_service):
    # Create a user with Spotify account
    user = User(
        username="unlinkuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    spotify_account = UserSpotifyOauthAccount(
        user_id=user.user_id,
        provider_user_id="test_spotify_id",
        encrypted_access_token="test_access_token",
        encrypted_refresh_token="test_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    test_session.add(spotify_account)
    await test_session.commit()
    
    # Create a token for the user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Unlink Spotify account
    response = await test_client.delete(
        "/auth/unlink-spotify",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_details"]["spotify_subscription"] is None
    
    # Verify Spotify account was deleted
    result = await test_session.execute(
        select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user.user_id)
    )
    spotify_account = result.scalar_one_or_none()
    assert spotify_account is None

@pytest.mark.asyncio
async def test_unlink_spotify_no_spotify_account(test_client, test_session, mock_spotify_service):
    # Create a user without Spotify account
    user = User(
        username="nospotifyuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token for the user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.delete(
        "/auth/unlink-spotify",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Spotify OAuth account not found for this user"

@pytest.mark.asyncio
async def test_unlink_spotify_missing_auth(test_client, test_session, mock_spotify_service):
    response = await test_client.delete("/auth/unlink-spotify")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_unlink_spotify_oauth_user(test_client, test_session, mock_spotify_service):
    # Create an OAuth user with Spotify account
    user = User(
        username="oauthuser",
        hashed_password=None,
        is_oauth_account=True,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    spotify_account = UserSpotifyOauthAccount(
        user_id=user.user_id,
        provider_user_id="test_spotify_id",
        encrypted_access_token="test_access_token",
        encrypted_refresh_token="test_refresh_token",
        access_token_expires_at=datetime.fromtimestamp(1234567890, tz=timezone.utc),
        subscription="premium"
    )
    test_session.add(spotify_account)
    await test_session.commit()
    
    # Create a token for the user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="test_session",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.delete(
        "/auth/unlink-spotify",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot unlink Spotify from an OAuth account"

@pytest.mark.asyncio
async def test_logout_success(test_client, test_session):
    # Create a user
    user = User(
        username="logoutuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a user session
    user_session = UserSession(
        user_id=user.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_invalidated=False
    )
    test_session.add(user_session)
    await test_session.commit()
    
    # Create a token for the user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id=str(user_session.user_session_id),
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Logout
    response = await test_client.put(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    
    # Verify user session was invalidated
    await test_session.refresh(user_session)
    assert user_session is not None
    assert user_session.is_invalidated is True

@pytest.mark.asyncio
async def test_logout_missing_auth(test_client, test_session):
    response = await test_client.put("/auth/logout")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_logout_nonexistent_session(test_client, test_session):
    # Create a user
    user = User(
        username="nonexistentsessionuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token with a nonexistent session ID (valid UUID format)
    token = create_access_token(
        user_id=user.user_id,
        user_session_id="123e4567-e89b-12d3-a456-426614174000",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

def create_expired_access_token(user_id: int, user_session_id: str, is_admin: bool = False, spotify_access_token: str = None):
    payload = {
        "user_id": user_id,  # Keep as integer
        "user_session_id": user_session_id,
        "is_admin": is_admin,
        "spotify_access_token": spotify_access_token,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5)  # Token expired 5 minutes ago
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@pytest.mark.asyncio
async def test_refresh_token_success(test_client, test_session):# Create a user
    user = User(
        username="refreshuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a user session
    user_session = UserSession(
        user_id=user.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_invalidated=False
    )
    test_session.add(user_session)
    await test_session.commit()
    
    # Create an expired token for the user
    token = create_expired_access_token(
        user_id=user.user_id,
        user_session_id=str(user_session.user_session_id),
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    # Refresh token
    response = await test_client.put(
        "/auth/refresh-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] is not None
    assert data["user_details"] is not None
    
    # Verify session expiry was updated
    await test_session.refresh(user_session)
    assert user_session.expires_at > datetime.now(timezone.utc) + timedelta(days=6)  # Should be at least 7 days from now

@pytest.mark.asyncio
async def test_refresh_token_missing_auth(test_client, test_session):
    response = await test_client.put("/auth/refresh-token")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_refresh_token_nonexistent_session(test_client, test_session):
    # Create a user
    user = User(
        username="nonexistentsessionuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a token with a nonexistent session ID (valid UUID format)
    token = create_expired_access_token(
        user_id=user.user_id,
        user_session_id="123e4567-e89b-12d3-a456-426614174000",
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/refresh-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session"

@pytest.mark.asyncio
async def test_refresh_token_invalidated_session(test_client, test_session):
    # Create a user
    user = User(
        username="invalidatedsessionuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create an invalidated user session
    user_session = UserSession(
        user_id=user.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_invalidated=True
    )
    test_session.add(user_session)
    await test_session.commit()
    
    # Create a token for the user
    token = create_expired_access_token(
        user_id=user.user_id,
        user_session_id=str(user_session.user_session_id),
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/refresh-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session"

@pytest.mark.asyncio
async def test_refresh_token_expired_session(test_client, test_session):
    # Create a user
    user = User(
        username="expiredsessionuser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create an expired user session
    user_session = UserSession(
        user_id=user.user_id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired yesterday
        is_invalidated=False
    )
    test_session.add(user_session)
    await test_session.commit()
    
    # Create a token for the user
    token = create_expired_access_token(
        user_id=user.user_id,
        user_session_id=str(user_session.user_session_id),
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/refresh-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Session expired"

@pytest.mark.asyncio
async def test_refresh_token_not_expired(test_client, test_session):
    # Create a user
    user = User(
        username="nonexpireduser",
        hashed_password=b"hashed_password",
        is_oauth_account=False,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    
    # Create a user session
    user_session = UserSession(
        user_id=user.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_invalidated=False
    )
    test_session.add(user_session)
    await test_session.commit()
    
    # Create a non-expired token for the user
    token = create_access_token(
        user_id=user.user_id,
        user_session_id=str(user_session.user_session_id),
        is_admin=False,
        spotify_access_token="test_spotify_token"
    )
    
    response = await test_client.put(
        "/auth/refresh-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Token is still valid, refresh not needed"