import pytest
from datetime import datetime, timezone
from sqlalchemy import select
import uuid

from app.models.postgresql import UserSession
from app.services.postgresql.user_session_service import UserSessionService
from app.services.postgresql.user_service import UserService

@pytest.mark.asyncio
async def test_create_user_session(test_session):
    user_service = UserService()
    session_service = UserSessionService()
    
    # Create a test user
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    
    # Test creating a session
    user_session = await session_service.create_user_session(test_session, user.user_id)
    
    assert user_session.user_id == user.user_id
    assert user_session.expires_at > datetime.now(timezone.utc)
    assert user_session.is_invalidated is False
    
    # Verify session was saved to database
    result = await test_session.execute(select(UserSession).where(UserSession.user_session_id == user_session.user_session_id))
    saved_session = result.scalar_one()
    assert saved_session.user_id == user_session.user_id
    assert saved_session.expires_at == user_session.expires_at
    assert saved_session.is_invalidated == user_session.is_invalidated

@pytest.mark.asyncio
async def test_create_user_session_non_existent_user(test_session):
    session_service = UserSessionService()
    
    # Test creating a session for non-existent user
    with pytest.raises(Exception) as exc_info:
        await session_service.create_user_session(test_session, 999)
    assert "User not found" in str(exc_info.value)
    
    # Verify no session was created
    result = await test_session.execute(select(UserSession).where(UserSession.user_id == 999))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_get_user_session_by_id(test_session):
    user_service = UserService()
    session_service = UserSessionService()
    
    # Create a test user and session
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    user_session = await session_service.create_user_session(test_session, user.user_id)
    
    # Test getting the session
    found_session = await session_service.get_user_session_by_id(test_session, user_session.user_session_id)
    assert found_session.user_id == user_session.user_id
    assert found_session.expires_at == user_session.expires_at
    assert found_session.is_invalidated == user_session.is_invalidated
    
    # Test getting non-existent session
    non_existent_session = await session_service.get_user_session_by_id(test_session, uuid.uuid4())
    assert non_existent_session is None

@pytest.mark.asyncio
async def test_refresh_user_session_expiry(test_session):
    user_service = UserService()
    session_service = UserSessionService()
    
    # Create a test user and session
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    user_session = await session_service.create_user_session(test_session, user.user_id)
    original_expires_at = user_session.expires_at
    
    # Test refreshing the session
    refreshed_session = await session_service.refresh_user_session_expiry(test_session, user_session.user_session_id)
    assert refreshed_session.expires_at > original_expires_at
    
    # Verify session was updated in database
    result = await test_session.execute(select(UserSession).where(UserSession.user_session_id == user_session.user_session_id))
    saved_session = result.scalar_one()
    assert saved_session.expires_at == refreshed_session.expires_at
    
    # Test refreshing non-existent session
    with pytest.raises(Exception) as exc_info:
        await session_service.refresh_user_session_expiry(test_session, uuid.uuid4())
    assert "Session not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_invalidate_user_session(test_session):
    user_service = UserService()
    session_service = UserSessionService()
    
    # Create a test user and session
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    user_session = await session_service.create_user_session(test_session, user.user_id)
    
    # Test invalidating the session
    await session_service.invalidate_user_session(test_session, user_session.user_session_id)
    
    # Verify session was invalidated in database
    result = await test_session.execute(select(UserSession).where(UserSession.user_session_id == user_session.user_session_id))
    saved_session = result.scalar_one()
    assert saved_session.is_invalidated is True
    
    # Test invalidating non-existent session
    with pytest.raises(Exception) as exc_info:
        await session_service.invalidate_user_session(test_session, uuid.uuid4())
    assert "Session not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_invalidate_all_user_sessions_by_user_id(test_session):
    user_service = UserService()
    session_service = UserSessionService()
    
    # Create a test user and multiple sessions
    user = await user_service.add_new_user(test_session, is_oauth_account=False)
    session1 = await session_service.create_user_session(test_session, user.user_id)
    session2 = await session_service.create_user_session(test_session, user.user_id)
    
    # Test invalidating all sessions
    invalidated_sessions = await session_service.invalidate_all_user_sessions_by_user_id(test_session, user.user_id)
    assert len(invalidated_sessions) == 2
    
    # Verify sessions were invalidated in database
    result = await test_session.execute(select(UserSession).where(UserSession.user_id == user.user_id))
    saved_sessions = result.scalars().all()
    assert all(session.is_invalidated for session in saved_sessions)
    
    # Test invalidating sessions for non-existent user
    invalidated_sessions = await session_service.invalidate_all_user_sessions_by_user_id(test_session, 999)
    assert len(invalidated_sessions) == 0 