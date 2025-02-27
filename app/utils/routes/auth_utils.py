from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.providers.spotify_service import SpotifyService

from utils.encryption_helper import decrypt_token, encrypt_token
from utils.jwt_helper import create_access_token

user_service = UserService()
user_spotify_oauth_account_service = UserSpotifyOAuthAccountService()
user_session_service = UserSessionService()

spotify_service = SpotifyService()

# TODO: Probably need to add logic if there is an error on spotify side to unlink if not oauth account or logout if oauth account.
async def fetch_or_refresh_spotify_access_token(session: AsyncSession, user_id: int):
    spotify_access_token = None
    user_spotify_oauth_account = await user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id(session, user_id)

    if user_spotify_oauth_account:
        if user_spotify_oauth_account.access_token_expires_at <= datetime.now(timezone.utc) - timedelta(minutes=20):
            spotify_refresh_token = decrypt_token(user_spotify_oauth_account.encrypted_refresh_token)

            spotify_access_token_details = await spotify_service.renew_user_access_token(spotify_refresh_token)
            spotify_access_token = spotify_access_token_details["access_token"]

            await user_spotify_oauth_account_service.update_oauth_tokens(
                session,
                user_id,
                encrypt_token(spotify_access_token),
                spotify_access_token_details["expires_in"]
            )
        else:
            spotify_access_token = decrypt_token(user_spotify_oauth_account.encrypted_access_token)

    return spotify_access_token


async def connect_spotify(session: AsyncSession, code: str, redirect_uri: str):
    spotify_oauth_token_details = await spotify_service.fetch_and_handle_oauth_token(code, redirect_uri)
    spotify_user_id, spotify_access_token, spotify_refresh_token, spotify_expires_in_seconds = spotify_oauth_token_details.values()

    async with session.begin():
        try:
            user, user_spotify_oauth_account = await user_spotify_oauth_account_service.add_new_user_with_spotify_oauth_account(
                session, 
                spotify_user_id, 
                encrypt_token(spotify_access_token), 
                encrypt_token(spotify_refresh_token), 
                spotify_expires_in_seconds)
        except HTTPException:
            user_spotify_oauth_account = await user_spotify_oauth_account_service.get_spotify_oauth_account_by_provider_user_id(session, spotify_user_id)
            user = await user_service.get_user_by_user_id(session, user_spotify_oauth_account.user_id)

            if not user.is_oauth_account:
                raise HTTPException(status_code=400, detail="This Spotify account is linked to a non-OAuth account")
            
            await user_spotify_oauth_account_service.update_oauth_tokens(
                session,
                user_id,
                encrypt_token(spotify_access_token),
                spotify_expires_in_seconds,
                encrypt_token(spotify_refresh_token))
            
        user_id = user.user_id
        user_session = await user_session_service.create_user_session(session, user_id)

    access_token = create_access_token(user_id, str(user_session.user_session_id), spotify_access_token)

    return { "access_token": access_token }


async def link_spotify(session: AsyncSession, code: str, redirect_uri: str, user_id: int):
    spotify_oauth_token_details = await spotify_service.fetch_and_handle_oauth_token(code, redirect_uri)
    spotify_user_id, spotify_access_token, spotify_refresh_token, spotify_expires_in_seconds = spotify_oauth_token_details.values()

    async with session.begin():
        await user_spotify_oauth_account_service.add_spotify_oauth_account_to_existing_user(
            session,
            user_id,
            spotify_user_id,
            encrypt_token(spotify_access_token),
            encrypt_token(spotify_refresh_token),
            spotify_expires_in_seconds)
        
        user_session = await user_session_service.create_user_session(session, user_id)

    access_token = create_access_token(user_id, str(user_session.user_session_id), spotify_access_token)

    return { "access_token": access_token }