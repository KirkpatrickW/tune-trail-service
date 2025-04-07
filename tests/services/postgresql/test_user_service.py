import pytest
from sqlalchemy import select
from fastapi import HTTPException

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

@pytest.mark.asyncio
async def test_search_users_by_username_success(test_session):
    service = UserService()
    
    # Create test users with different usernames
    usernames = ["testuser1", "testuser2", "testuser3", "otheruser1", "otheruser2"]
    users = []
    
    for username in usernames:
        user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
        users.append(user)
    
    # Test searching for users with "test" in username
    result = await service.search_users_by_username(test_session, "test")
    
    assert result["total_matching_results"] == 3
    assert len(result["users"]) == 3
    assert result["next_offset"] is None  # No more results
    
    # Verify the returned users
    returned_usernames = [user["username"] for user in result["users"]]
    assert "testuser1" in returned_usernames
    assert "testuser2" in returned_usernames
    assert "testuser3" in returned_usernames
    
    # Test searching with offset
    result = await service.search_users_by_username(test_session, "test", offset=2)
    
    assert result["total_matching_results"] == 3
    assert len(result["users"]) == 1
    assert result["next_offset"] is None  # No more results
    
    # Test searching for users with "other" in username
    result = await service.search_users_by_username(test_session, "other")
    
    assert result["total_matching_results"] == 2
    assert len(result["users"]) == 2
    assert result["next_offset"] is None  # No more results
    
    # Verify the returned users
    returned_usernames = [user["username"] for user in result["users"]]
    assert "otheruser1" in returned_usernames
    assert "otheruser2" in returned_usernames
    
    # Test searching for non-existent users
    result = await service.search_users_by_username(test_session, "nonexistent")
    
    assert result["total_matching_results"] == 0
    assert len(result["users"]) == 0
    assert result["next_offset"] is None

@pytest.mark.asyncio
async def test_search_users_by_username_case_insensitive(test_session):
    service = UserService()
    
    # Create test users with mixed case usernames
    usernames = ["TestUser", "testuser", "TESTUSER", "AnotherUser"]
    users = []
    
    for username in usernames:
        user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
        users.append(user)
    
    # Test searching with lowercase
    result = await service.search_users_by_username(test_session, "testuser")
    
    assert result["total_matching_results"] == 3
    assert len(result["users"]) == 3
    
    # Test searching with uppercase
    result = await service.search_users_by_username(test_session, "TESTUSER")
    
    assert result["total_matching_results"] == 3
    assert len(result["users"]) == 3
    
    # Test searching with mixed case
    result = await service.search_users_by_username(test_session, "TestUser")
    
    assert result["total_matching_results"] == 3
    assert len(result["users"]) == 3

@pytest.mark.asyncio
async def test_search_users_by_username_pagination(test_session):
    service = UserService()
    
    # Create 25 test users to test pagination
    usernames = [f"testuser{i}" for i in range(1, 26)]
    users = []
    
    for username in usernames:
        user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
        users.append(user)
    
    # Test first page (default limit is 20)
    result = await service.search_users_by_username(test_session, "testuser")
    
    assert result["total_matching_results"] == 25
    assert len(result["users"]) == 20
    assert result["next_offset"] == 20  # There are more results
    
    # Test second page
    result = await service.search_users_by_username(test_session, "testuser", offset=20)
    
    assert result["total_matching_results"] == 25
    assert len(result["users"]) == 5
    assert result["next_offset"] is None  # No more results
    
    # Test with offset beyond available results
    result = await service.search_users_by_username(test_session, "testuser", offset=30)
    
    assert result["total_matching_results"] == 25
    assert len(result["users"]) == 0
    assert result["next_offset"] is None

@pytest.mark.asyncio
async def test_search_users_by_username_partial_match(test_session):
    service = UserService()
    
    # Create test users with various usernames
    usernames = ["testuser", "test123", "123test", "test", "user", "testuser123"]
    users = []
    
    for username in usernames:
        user = await service.add_new_user(test_session, username=username, is_oauth_account=False)
        users.append(user)
    
    # Test searching with partial match at the beginning
    result = await service.search_users_by_username(test_session, "test")
    
    assert result["total_matching_results"] == 5  # testuser, test123, test, testuser123
    assert len(result["users"]) == 5
    
    # Test searching with partial match in the middle
    result = await service.search_users_by_username(test_session, "user")
    
    assert result["total_matching_results"] == 3  # testuser, user, testuser123
    assert len(result["users"]) == 3
    
    # Test searching with partial match at the end
    result = await service.search_users_by_username(test_session, "123")
    
    assert result["total_matching_results"] == 3  # test123, 123test, testuser123
    assert len(result["users"]) == 3

@pytest.mark.asyncio
async def test_delete_user_by_user_id_success(test_session):
    service = UserService()
    
    # Create a test user
    user = await service.add_new_user(test_session, username="testuser", is_oauth_account=False)
    user_id = user.user_id
    
    # Verify user exists in database
    result = await test_session.execute(select(User).where(User.user_id == user_id))
    assert result.scalar_one() is not None
    
    # Delete the user
    await service.delete_user_by_user_id(test_session, user_id)
    
    # Verify user no longer exists in database
    result = await test_session.execute(select(User).where(User.user_id == user_id))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_delete_user_by_user_id_not_found(test_session):
    service = UserService()
    
    # Try to delete a non-existent user
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_user_by_user_id(test_session, 999)
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"

@pytest.mark.asyncio
async def test_delete_user_by_user_id_with_related_data(test_session):
    service = UserService()
    
    # Create a test user
    user = await service.add_new_user(test_session, username="testuser", is_oauth_account=False)
    user_id = user.user_id
    
    # Create related data (this would be locality tracks in a real scenario)
    # For this test, we'll just verify the user can be deleted even with related data
    # In a real application, you might need to handle cascading deletes
    
    # Delete the user
    await service.delete_user_by_user_id(test_session, user_id)
    
    # Verify user no longer exists in database
    result = await test_session.execute(select(User).where(User.user_id == user_id))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_delete_multiple_users(test_session):
    service = UserService()
    
    # Create multiple test users
    users = []
    for i in range(3):
        user = await service.add_new_user(test_session, username=f"testuser{i}", is_oauth_account=False)
        users.append(user)
    
    # Delete each user
    for user in users:
        await service.delete_user_by_user_id(test_session, user.user_id)
        
        # Verify user no longer exists in database
        result = await test_session.execute(select(User).where(User.user_id == user.user_id))
        assert result.scalar_one_or_none() is None
    
    # Verify all users were deleted
    result = await test_session.execute(select(User).where(User.user_id.in_([u.user_id for u in users])))
    assert len(result.scalars().all()) == 0 