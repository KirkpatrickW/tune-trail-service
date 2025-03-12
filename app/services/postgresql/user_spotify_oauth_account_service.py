from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.postgresql.user_spotify_oauth_account import UserSpotifyOauthAccount
from services.postgresql.user_service import UserService

class Subscription(Enum):
    FREE = "free"
    PREMIUM = "premium"

class UserSpotifyOAuthAccountService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserSpotifyOAuthAccountService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    

    def _init(self):
        self.user_service = UserService()


    async def get_spotify_oauth_account_by_user_id(self, session: AsyncSession, user_id: int):
        stmt = select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.user_id == user_id)
        result = await session.execute(stmt)
        oauth_account = result.scalars().first()
        return oauth_account
    

    async def get_spotify_oauth_account_by_provider_user_id(self, session: AsyncSession, provider_user_id: int):
        stmt = select(UserSpotifyOauthAccount).where(UserSpotifyOauthAccount.provider_user_id == provider_user_id)
        result = await session.execute(stmt)
        oauth_account = result.scalars().first()
        return oauth_account


    async def add_new_user_with_spotify_oauth_account(self, session: AsyncSession, provider_user_id: str, subscription: Subscription, encrypted_access_token: str, encrypted_refresh_token: str, access_token_expires_in_seconds: datetime):
        existing_oauth_account = await self.get_spotify_oauth_account_by_provider_user_id(session, provider_user_id)
        if existing_oauth_account:
            raise HTTPException(status_code=400, detail="This Spotify account is already associated with a user")

        user = await self.user_service.add_new_user(session, is_oauth_account=True)
        oauth_account = UserSpotifyOauthAccount(
            user_id=user.user_id,
            provider_user_id=provider_user_id,
            subscription=subscription,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=access_token_expires_in_seconds)
        )
        session.add(oauth_account)

        await session.flush()
        await session.refresh(oauth_account)

        return user, oauth_account
    

    async def add_spotify_oauth_account_to_existing_user(self, session: AsyncSession, user_id: int, provider_user_id: str, subscription: Subscription, encrypted_access_token: str, encrypted_refresh_token: str, access_token_expires_in_seconds: datetime):
        user = await self.user_service.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_oauth_account = await self.get_spotify_oauth_account_by_provider_user_id(session, provider_user_id)
        if existing_oauth_account:
            raise HTTPException(status_code=400, detail="This Spotify account is already associated with a user")

        user_existing_oauth_account = await session.execute(select(UserSpotifyOauthAccount).filter_by(user_id=user_id))
        user_existing_oauth_account = user_existing_oauth_account.scalars().first()
        if user_existing_oauth_account:
            raise HTTPException(status_code=400, detail="A Spotify account is already linked to this user")

        oauth_account = UserSpotifyOauthAccount(
            user_id=user_id,
            provider_user_id=provider_user_id,
            subscription=subscription,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=access_token_expires_in_seconds)
        )
        session.add(oauth_account)

        await session.flush()
        await session.refresh(oauth_account)

        return oauth_account
    

    async def update_oauth_tokens(self, session: AsyncSession, user_id: int, subscription: Subscription, encrypted_access_token: str, expires_in_seconds: datetime, encrypted_refresh_token: str = None):
        user_spotify_oauth_account = await self.get_spotify_oauth_account_by_user_id(session, user_id)
        if not user_spotify_oauth_account:
            raise HTTPException(status_code=404, detail="Spotify OAuth account not found for this user")
        
        user_spotify_oauth_account.subscription = subscription
        user_spotify_oauth_account.encrypted_access_token = encrypted_access_token
        user_spotify_oauth_account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        if encrypted_refresh_token:
            user_spotify_oauth_account.encrypted_refresh_token = encrypted_refresh_token
        session.add(user_spotify_oauth_account)

        await session.flush()
        await session.refresh(user_spotify_oauth_account)

        return user_spotify_oauth_account
    

    async def delete_spotify_oauth_account_by_user_id(self, session: AsyncSession, user_id: int):
        user_spotify_oauth_account = await self.get_spotify_oauth_account_by_user_id(session, user_id)
        if not user_spotify_oauth_account:
            raise HTTPException(status_code=404, detail="Spotify OAuth account not found for this user")
        
        await session.delete(user_spotify_oauth_account)

        await session.flush()

        return