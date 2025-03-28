import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.postgresql import User, UserSpotifyOauthAccount
from app.services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from app.services.postgresql.user_service import UserService

@pytest.mark.asyncio
async def test_add_new_user_with_spotify_oauth_account(test_session):
    service = UserSpotifyOAuthAccountService()
    
    # Test adding a new user with Spotify OAuth account
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    user, oauth_account = await service.add_new_user_with_spotify_oauth_account(
        test_session,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    assert user.user_id is not None
    assert user.is_oauth_account is True
    assert oauth_account.user_id == user.user_id
    assert oauth_account.provider_user_id == provider_user_id
    assert oauth_account.subscription == "premium"
    assert oauth_account.encrypted_access_token == encrypted_access_token
    assert oauth_account.encrypted_refresh_token == encrypted_refresh_token
    assert oauth_account.access_token_expires_at > datetime.now(timezone.utc)
    
    # Verify user and OAuth account were saved to database
    result = await test_session.execute(select(User).where(User.user_id == user.user_id))
    saved_user = result.scalar_one()
    assert saved_user.user_id == user.user_id
    assert saved_user.is_oauth_account == user.is_oauth_account
    assert saved_user.is_admin == user.is_admin
    
    result = await test_session.execute(select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user.user_id))
    saved_oauth_account = result.scalar_one()
    assert saved_oauth_account.user_id == oauth_account.user_id
    assert saved_oauth_account.provider_user_id == oauth_account.provider_user_id
    assert saved_oauth_account.subscription == oauth_account.subscription
    assert saved_oauth_account.encrypted_access_token == oauth_account.encrypted_access_token
    assert saved_oauth_account.encrypted_refresh_token == oauth_account.encrypted_refresh_token
    assert saved_oauth_account.access_token_expires_at == oauth_account.access_token_expires_at

@pytest.mark.asyncio
async def test_add_spotify_oauth_account_to_existing_user(test_session):
    user_service = UserService()
    oauth_service = UserSpotifyOAuthAccountService()
    
    # Create a test user
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    
    # Test adding Spotify OAuth account to existing user
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    oauth_account = await oauth_service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    assert oauth_account.user_id == user.user_id
    assert oauth_account.provider_user_id == provider_user_id
    assert oauth_account.subscription == "premium"
    assert oauth_account.encrypted_access_token == encrypted_access_token
    assert oauth_account.encrypted_refresh_token == encrypted_refresh_token
    assert oauth_account.access_token_expires_at > datetime.now(timezone.utc)
    
    # Verify OAuth account was saved to database
    result = await test_session.execute(select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user.user_id))
    saved_oauth_account = result.scalar_one()
    assert saved_oauth_account.user_id == oauth_account.user_id
    assert saved_oauth_account.provider_user_id == oauth_account.provider_user_id
    assert saved_oauth_account.subscription == oauth_account.subscription
    assert saved_oauth_account.encrypted_access_token == oauth_account.encrypted_access_token
    assert saved_oauth_account.encrypted_refresh_token == oauth_account.encrypted_refresh_token
    assert saved_oauth_account.access_token_expires_at == oauth_account.access_token_expires_at

@pytest.mark.asyncio
async def test_get_spotify_oauth_account_by_user_id(test_session):
    user_service = UserService()
    oauth_service = UserSpotifyOAuthAccountService()
    
    # Create a test user with Spotify OAuth account
    user = await user_service.add_new_user(test_session, is_oauth_account=True)
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    oauth_account = await oauth_service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Test getting the OAuth account
    found_account = await oauth_service.get_spotify_oauth_account_by_user_id(test_session, user.user_id)
    assert found_account == oauth_account
    
    # Test getting non-existent account
    non_existent_account = await oauth_service.get_spotify_oauth_account_by_user_id(test_session, 999)
    assert non_existent_account is None

@pytest.mark.asyncio
async def test_get_spotify_oauth_account_by_provider_user_id(test_session):
    user_service = UserService()
    oauth_service = UserSpotifyOAuthAccountService()
    
    # Create a test user with Spotify OAuth account
    user = await user_service.add_new_user(test_session, is_oauth_account=True)
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    oauth_account = await oauth_service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Test getting the OAuth account
    found_account = await oauth_service.get_spotify_oauth_account_by_provider_user_id(test_session, provider_user_id)
    assert found_account == oauth_account
    
    # Test getting non-existent account
    non_existent_account = await oauth_service.get_spotify_oauth_account_by_provider_user_id(test_session, "nonexistent")
    assert non_existent_account is None

@pytest.mark.asyncio
async def test_update_oauth_tokens(test_session):
    service = UserSpotifyOAuthAccountService()
    user_service = UserService()
    
    # Create a test user with Spotify OAuth account
    user = await user_service.add_new_user(test_session, is_oauth_account=True)
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    oauth_account = await service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Test updating tokens with new refresh token
    new_subscription = "free"
    new_encrypted_access_token = "new_encrypted_token"
    new_encrypted_refresh_token = "new_encrypted_refresh"
    new_expires_in_seconds = 7200
    
    updated_account = await service.update_oauth_tokens(
        test_session,
        user.user_id,
        new_subscription,
        new_encrypted_access_token,
        new_expires_in_seconds,
        new_encrypted_refresh_token
    )
    
    assert updated_account.subscription == "free"
    assert updated_account.encrypted_access_token == new_encrypted_access_token
    assert updated_account.encrypted_refresh_token == new_encrypted_refresh_token
    assert updated_account.access_token_expires_at > datetime.now(timezone.utc)
    
    # Test updating tokens without new refresh token
    new_encrypted_access_token = "another_encrypted_token"
    new_expires_in_seconds = 1800
    
    updated_account = await service.update_oauth_tokens(
        test_session,
        user.user_id,
        new_subscription,
        new_encrypted_access_token,
        new_expires_in_seconds
    )
    
    assert updated_account.subscription == "free"
    assert updated_account.encrypted_access_token == new_encrypted_access_token
    assert updated_account.encrypted_refresh_token == new_encrypted_refresh_token  # Should remain unchanged
    assert updated_account.access_token_expires_at > datetime.now(timezone.utc)

@pytest.mark.asyncio
async def test_delete_spotify_oauth_account_by_user_id(test_session):
    user_service = UserService()
    oauth_service = UserSpotifyOAuthAccountService()
    
    # Create a test user with Spotify OAuth account
    user = await user_service.add_new_user(test_session, is_oauth_account=True)
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    oauth_account = await oauth_service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Test deleting the OAuth account
    await oauth_service.delete_spotify_oauth_account_by_user_id(test_session, user.user_id)
    
    # Verify account was deleted from database
    result = await test_session.execute(select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user.user_id))
    assert result.scalar_one_or_none() is None
    
    # Test deleting non-existent account
    with pytest.raises(Exception) as exc_info:
        await oauth_service.delete_spotify_oauth_account_by_user_id(test_session, 999)
    assert "Spotify OAuth account not found for this user" in str(exc_info.value)

@pytest.mark.asyncio
async def test_add_new_user_with_spotify_oauth_account_existing_account(test_session):
    service = UserSpotifyOAuthAccountService()
    
    # Create first user with Spotify OAuth account
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    await service.add_new_user_with_spotify_oauth_account(
        test_session,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Try to create another user with the same Spotify account
    with pytest.raises(Exception) as exc_info:
        await service.add_new_user_with_spotify_oauth_account(
            test_session,
            provider_user_id,
            subscription,
            encrypted_access_token,
            encrypted_refresh_token,
            access_token_expires_in_seconds
        )
    assert "This Spotify account is already associated with a user" in str(exc_info.value)

@pytest.mark.asyncio
async def test_add_spotify_oauth_account_to_existing_user_errors(test_session):
    service = UserSpotifyOAuthAccountService()
    
    # Test adding to non-existent user
    with pytest.raises(Exception) as exc_info:
        await service.add_spotify_oauth_account_to_existing_user(
            test_session,
            999,  # Non-existent user ID
            "spotify123",
            "premium",
            "encrypted_token",
            "encrypted_refresh",
            3600
        )
    assert "User not found" in str(exc_info.value)
    
    # Create a test user
    user_service = UserService()
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    
    # Create another user with the same Spotify account
    provider_user_id = "spotify123"
    subscription = "premium"
    encrypted_access_token = "encrypted_token"
    encrypted_refresh_token = "encrypted_refresh"
    access_token_expires_in_seconds = 3600
    
    await service.add_new_user_with_spotify_oauth_account(
        test_session,
        provider_user_id,
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Try to add the same Spotify account to our test user
    with pytest.raises(Exception) as exc_info:
        await service.add_spotify_oauth_account_to_existing_user(
            test_session,
            user.user_id,
            provider_user_id,
            subscription,
            encrypted_access_token,
            encrypted_refresh_token,
            access_token_expires_in_seconds
        )
    assert "This Spotify account is already associated with a user" in str(exc_info.value)
    
    # Add a different Spotify account to our test user
    await service.add_spotify_oauth_account_to_existing_user(
        test_session,
        user.user_id,
        "spotify456",
        subscription,
        encrypted_access_token,
        encrypted_refresh_token,
        access_token_expires_in_seconds
    )
    
    # Try to add another Spotify account to the same user
    with pytest.raises(Exception) as exc_info:
        await service.add_spotify_oauth_account_to_existing_user(
            test_session,
            user.user_id,
            "spotify789",
            subscription,
            encrypted_access_token,
            encrypted_refresh_token,
            access_token_expires_in_seconds
        )
    assert "A Spotify account is already linked to this user" in str(exc_info.value)

@pytest.mark.asyncio
async def test_update_oauth_tokens_non_existent_account(test_session):
    service = UserSpotifyOAuthAccountService()
    
    # Try to update tokens for non-existent account
    with pytest.raises(Exception) as exc_info:
        await service.update_oauth_tokens(
            test_session,
            999,  # Non-existent user ID
            "premium",
            "encrypted_token",
            3600,
            "encrypted_refresh"
        )
    assert "Spotify OAuth account not found for this user" in str(exc_info.value) 