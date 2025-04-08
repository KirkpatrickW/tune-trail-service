from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from models.postgresql import User

class UserService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserService, cls).__new__(cls)
        return cls._instance
    

    async def get_user_by_username(self, session: AsyncSession, username: str):
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalars().first()

        return user


    async def get_user_by_user_id(self, session: AsyncSession, user_id: int):
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()

        return user
    

    async def search_users_by_username(self, session: AsyncSession, search_term: str, offset: int = 0):
        total_stmt = select(func.count()).select_from(User).where(User.username.ilike(f"%{search_term}%"))
        total_result = await session.execute(total_stmt)
        total_matching_results = total_result.scalar()

        stmt = select(User).where(User.username.ilike(f"%{search_term}%")).limit(20).offset(offset)
        result = await session.execute(stmt)
        users = result.scalars().all()

        next_offset = offset + 20 if offset + 20 < total_matching_results else None

        return {
            "users": [{"user_id": user.user_id, "username": user.username} for user in users],
            "next_offset": next_offset,
        }

    async def add_new_user(self, session: AsyncSession, username: str = None, hashed_password: bytes = None, is_oauth_account: bool = False):
        if username:
            existing_user = await self.get_user_by_username(session, username)
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")

        user = User(username=username, hashed_password=hashed_password, is_oauth_account=is_oauth_account)
        session.add(user)

        await session.flush()
        await session.refresh(user)

        return user
    
    
    async def set_oauth_account_username(self, session: AsyncSession, user_id: int, username: str):
        user = await self.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.username:
            raise HTTPException(status_code=400, detail="Username already set for this account")

        if not user.is_oauth_account:
            raise HTTPException(status_code=400, detail="Username can only be added to accounts created via Spotify OAuth")
        
        existing_user = await self.get_user_by_username(session, username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

        user.username = username

        await session.flush()
        await session.refresh(user)

        return user
    

    async def delete_user_by_user_id(self, session: AsyncSession, user_id: int):
        user = await self.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await session.delete(user)

        await session.flush()

        return