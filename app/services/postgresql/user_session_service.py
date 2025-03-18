from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.postgresql import UserSession
from services.postgresql.user_service import UserService

class UserSessionService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSessionService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    

    def _init(self):
        self.user_service = UserService()


    async def get_user_session_by_id(self, session: AsyncSession, user_session_id: str):
        stmt = select(UserSession).where(UserSession.user_session_id == user_session_id)
        result = await session.execute(stmt)
        user_session = result.scalars().first()

        session.expunge_all()

        return user_session
    

    async def create_user_session(self, session: AsyncSession, user_id: int):
        user = await self.user_service.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        user_session = UserSession(user_id=user.user_id, expires_at=expires_at)
        session.add(user_session)

        await session.flush()
        await session.refresh(user_session)
        session.expunge_all()

        return user_session
    

    async def refresh_user_session_expiry(self, session: AsyncSession, user_session_id: str):
        user_session = await self.get_user_session_by_id(session, user_session_id)
        if not user_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        user_session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await session.flush()
        await session.refresh(user_session)
        session.expunge_all()

        return user_session
    

    async def invalidate_user_session(self, session: AsyncSession, user_session_id: str):
        user_session = await self.get_user_session_by_id(session, user_session_id)
        if not user_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        user_session.is_invalidated = True

        await session.flush()
        await session.refresh(user_session)
        session.expunge_all()

        return user_session
    

    async def invalidate_all_user_sessions_by_user_id(self, session: AsyncSession, user_id: int):
        stmt = select(UserSession).where(UserSession.user_id == user_id, UserSession.is_invalidated == False)
        result = await session.execute(stmt)
        user_sessions = result.scalars().all()

        for user_session in user_sessions:
            user_session.is_invalidated = True

        await session.flush()
        session.expunge_all()

        return user_sessions
