import pytest
from sqlalchemy import select

from app.models.postgresql import User
from app.services.postgresql.user_service import UserService

@pytest.mark.asyncio
async def test_add_new_user(test_session):
    service = UserService()
    
    # Test adding a new user
    user = await service.add_new_user(test_session, is_oauth_account=False)
    assert user.user_id is not None
    assert user.is_oauth_account is False
    assert user.username is None
    assert user.hashed_password is None
    assert user.is_admin is False
    
    # Verify user was saved to database
    result = await test_session.execute(select(User).where(User.user_id == user.user_id))
    saved_user = result.scalar_one()
    assert saved_user.user_id == user.user_id
    assert saved_user.is_oauth_account == user.is_oauth_account
    assert saved_user.username == user.username
    assert saved_user.hashed_password == user.hashed_password
    assert saved_user.is_admin == user.is_admin

@pytest.mark.asyncio
async def test_add_new_oauth_user(test_session):
    service = UserService()
    
    # Test adding a new OAuth user
    user = await service.add_new_user(test_session, is_oauth_account=True)
    assert user.user_id is not None
    assert user.is_oauth_account is True
    assert user.username is None
    assert user.hashed_password is None
    assert user.is_admin is False
    
    # Verify user was saved to database
    result = await test_session.execute(select(User).where(User.user_id == user.user_id))
    saved_user = result.scalar_one()
    assert saved_user.user_id == user.user_id
    assert saved_user.is_oauth_account == user.is_oauth_account
    assert saved_user.username == user.username
    assert saved_user.hashed_password == user.hashed_password
    assert saved_user.is_admin == user.is_admin

@pytest.mark.asyncio
async def test_add_new_user_with_username(test_session):
    service = UserService()
    
    # Test adding a new user with username
    username = "testuser"
    user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
    assert user.user_id is not None
    assert user.username == username
    assert user.is_oauth_account is False
    
    # Verify user was saved to database
    result = await test_session.execute(select(User).where(User.user_id == user.user_id))
    saved_user = result.scalar_one()
    assert saved_user.username == username
    
    # Test adding another user with the same username
    with pytest.raises(Exception) as exc_info:
        await service.add_new_user(test_session, username=username, is_oauth_account=False)
    assert "Username already taken" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_user_by_user_id(test_session):
    service = UserService()
    
    # Create a test user
    user = await service.add_new_user(test_session, is_oauth_account=False)
    
    # Test getting the user
    found_user = await service.get_user_by_user_id(test_session, user.user_id)
    assert found_user.user_id == user.user_id
    assert found_user.is_oauth_account == user.is_oauth_account
    assert found_user.username == user.username
    assert found_user.hashed_password == user.hashed_password
    assert found_user.is_admin == user.is_admin
    
    # Test getting non-existent user
    non_existent_user = await service.get_user_by_user_id(test_session, 999)
    assert non_existent_user is None

@pytest.mark.asyncio
async def test_get_user_by_username(test_session):
    service = UserService()
    
    # Create a test user with username
    username = "testuser"
    user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
    
    # Test getting the user
    found_user = await service.get_user_by_username(test_session, username)
    assert found_user.user_id == user.user_id
    assert found_user.username == username
    assert found_user.is_oauth_account == user.is_oauth_account
    assert found_user.hashed_password == user.hashed_password
    assert found_user.is_admin == user.is_admin
    
    # Test getting non-existent user
    non_existent_user = await service.get_user_by_username(test_session, "nonexistent")
    assert non_existent_user is None

@pytest.mark.asyncio
async def test_set_oauth_account_username(test_session):
    service = UserService()
    
    # Create a test OAuth user
    user = await service.add_new_user(test_session, is_oauth_account=True)
    
    # Test setting username
    username = "testuser"
    updated_user = await service.set_oauth_account_username(test_session, user.user_id, username)
    assert updated_user.username == username
    
    # Verify update in database
    result = await test_session.execute(select(User).where(User.user_id == user.user_id))
    saved_user = result.scalar_one()
    assert saved_user.username == username
    
    # Test setting username for non-existent user
    with pytest.raises(Exception) as exc_info:
        await service.set_oauth_account_username(test_session, 999, "newusername")
    assert "User not found" in str(exc_info.value)
    
    # Test setting username for non-OAuth user
    regular_user = await service.add_new_user(test_session, is_oauth_account=False)
    with pytest.raises(Exception) as exc_info:
        await service.set_oauth_account_username(test_session, regular_user.user_id, "newusername")
    assert "Username can only be added to accounts created via Spotify OAuth" in str(exc_info.value)
    
    # Test setting username for user that already has one
    with pytest.raises(Exception) as exc_info:
        await service.set_oauth_account_username(test_session, user.user_id, "anotherusername")
    assert "Username already set for this account" in str(exc_info.value)
    
    # Test setting username that's already taken
    another_user = await service.add_new_user(test_session, is_oauth_account=True)
    with pytest.raises(Exception) as exc_info:
        await service.set_oauth_account_username(test_session, another_user.user_id, username)
    assert "Username already taken" in str(exc_info.value) 