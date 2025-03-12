from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.postgresql.user import User

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
    

    async def add_new_user(self, session: AsyncSession, username: str = None, hashed_password: bytes = None, is_oauth_account: bool = False):
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