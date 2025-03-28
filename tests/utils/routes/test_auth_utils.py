import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.routes.auth_utils import fetch_or_refresh_spotify_access_token_details
from app.utils.encryption_helper import encrypt_token

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_user_spotify_oauth_account_service():
    with patch('app.utils.routes.auth_utils.user_spotify_oauth_account_service') as mock:
        mock.get_spotify_oauth_account_by_user_id = AsyncMock()
        mock.update_oauth_tokens = AsyncMock()
        mock.delete_spotify_oauth_account_by_user_id = AsyncMock()
        yield mock

@pytest.fixture
def mock_user_service():
    with patch('app.utils.routes.auth_utils.user_service') as mock:
        mock.get_user_by_user_id = AsyncMock()
        yield mock

@pytest.fixture
def mock_user_session_service():
    with patch('app.utils.routes.auth_utils.user_session_service') as mock:
        mock.invalidate_all_user_sessions_by_user_id = AsyncMock()
        yield mock

@pytest.fixture
def mock_spotify_service():
    with patch('app.utils.routes.auth_utils.spotify_service') as mock:
        mock.renew_user_access_token = AsyncMock()
        yield mock

@pytest.mark.asyncio
async def test_fetch_or_refresh_spotify_access_token_details_no_account(
    mock_session,
    mock_user_spotify_oauth_account_service
):
    # No Spotify OAuth account exists
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.return_value = None

    spotify_access_token, spotify_subscription = await fetch_or_refresh_spotify_access_token_details(
        mock_session,
        user_id=1
    )

    assert spotify_access_token is None
    assert spotify_subscription is None
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.assert_called_once_with(
        mock_session,
        1
    )

@pytest.mark.asyncio
async def test_fetch_or_refresh_spotify_access_token_details_valid_token(mock_session, mock_user_spotify_oauth_account_service):
    # Spotify OAuth account exists with valid token
    encrypted_access_token = encrypt_token("valid_access_token")
    mock_oauth_account = MagicMock(
        encrypted_access_token=encrypted_access_token,
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        subscription="premium"
    )
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.return_value = mock_oauth_account

    spotify_access_token, spotify_subscription = await fetch_or_refresh_spotify_access_token_details(
        mock_session,
        user_id=1
    )

    assert spotify_access_token == "valid_access_token"
    assert spotify_subscription == "premium"
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.assert_called_once_with(
        mock_session,
        1
    )

@pytest.mark.asyncio
async def test_fetch_or_refresh_spotify_access_token_details_successful_refresh(mock_session, mock_user_spotify_oauth_account_service, mock_spotify_service):
    # Spotify OAuth account exists with expired token
    encrypted_refresh_token = encrypt_token("valid_refresh_token")
    mock_oauth_account = MagicMock(
        encrypted_refresh_token=encrypted_refresh_token,
        access_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        subscription="premium"
    )
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.return_value = mock_oauth_account

    # Mock successful token refresh
    mock_spotify_service.renew_user_access_token.return_value = {
        "access_token": "new_access_token",
        "expires_in": 3600,
        "subscription": "premium"
    }

    spotify_access_token, spotify_subscription = await fetch_or_refresh_spotify_access_token_details(
        mock_session,
        user_id=1
    )

    assert spotify_access_token == "new_access_token"
    assert spotify_subscription == "premium"
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.assert_called_once_with(
        mock_session,
        1
    )
    mock_spotify_service.renew_user_access_token.assert_called_once_with("valid_refresh_token")
    mock_user_spotify_oauth_account_service.update_oauth_tokens.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_or_refresh_spotify_access_token_details_failed_refresh_oauth_user(mock_session, mock_user_spotify_oauth_account_service, mock_spotify_service, mock_user_service, mock_user_session_service):
    # Spotify OAuth account exists with expired token
    encrypted_refresh_token = encrypt_token("valid_refresh_token")
    mock_oauth_account = MagicMock(
        encrypted_refresh_token=encrypted_refresh_token,
        access_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        subscription="premium"
    )
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.return_value = mock_oauth_account

    # Mock failed token refresh
    mock_spotify_service.renew_user_access_token.side_effect = Exception("Refresh failed")

    # Mock user is OAuth account
    mock_user = MagicMock(is_oauth_account=True)
    mock_user_service.get_user_by_user_id.return_value = mock_user

    with pytest.raises(HTTPException) as exc_info:
        await fetch_or_refresh_spotify_access_token_details(
            mock_session,
            user_id=1
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Failed to refresh Spotify access token"
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.assert_called_once_with(
        mock_session,
        1
    )
    mock_spotify_service.renew_user_access_token.assert_called_once_with("valid_refresh_token")
    mock_user_service.get_user_by_user_id.assert_called_once_with(mock_session, 1)
    mock_user_session_service.invalidate_all_user_sessions_by_user_id.assert_called_once_with(mock_session, 1)

@pytest.mark.asyncio
async def test_fetch_or_refresh_spotify_access_token_details_failed_refresh_non_oauth_user(mock_session, mock_user_spotify_oauth_account_service, mock_spotify_service, mock_user_service):
    # Spotify OAuth account exists with expired token
    encrypted_refresh_token = encrypt_token("valid_refresh_token")
    mock_oauth_account = MagicMock(
        encrypted_refresh_token=encrypted_refresh_token,
        access_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        subscription="premium"
    )
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.return_value = mock_oauth_account

    # Mock failed token refresh
    mock_spotify_service.renew_user_access_token.side_effect = Exception("Refresh failed")

    # Mock user is not OAuth account
    mock_user = MagicMock(is_oauth_account=False)
    mock_user_service.get_user_by_user_id.return_value = mock_user

    with pytest.raises(HTTPException) as exc_info:
        await fetch_or_refresh_spotify_access_token_details(
            mock_session,
            user_id=1
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Failed to refresh Spotify access token"
    mock_user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id.assert_called_once_with(
        mock_session,
        1
    )
    mock_spotify_service.renew_user_access_token.assert_called_once_with("valid_refresh_token")
    mock_user_service.get_user_by_user_id.assert_called_once_with(mock_session, 1)
    mock_user_spotify_oauth_account_service.delete_spotify_oauth_account_by_user_id.assert_called_once_with(mock_session, 1) 