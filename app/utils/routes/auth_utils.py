from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from services.providers.spotify_service import SpotifyService

from utils.encryption_helper import decrypt_token, encrypt_token

user_service = UserService()
user_spotify_oauth_account_service = UserSpotifyOAuthAccountService()
user_session_service = UserSessionService()

spotify_service = SpotifyService()

async def fetch_or_refresh_spotify_access_token_details(session: AsyncSession, user_id: int):
    spotify_access_token = None
    spotify_subscription = None
    async with session.begin():
        user_spotify_oauth_account = await user_spotify_oauth_account_service.get_spotify_oauth_account_by_user_id(session, user_id)

        if user_spotify_oauth_account:
            if user_spotify_oauth_account.access_token_expires_at <= datetime.now(timezone.utc) - timedelta(minutes=20):
                spotify_refresh_token = decrypt_token(user_spotify_oauth_account.encrypted_refresh_token)

                try:
                    spotify_access_token_details = await spotify_service.renew_user_access_token(spotify_refresh_token)
                    spotify_access_token, spotify_expires_in_seconds, spotify_subscription = spotify_access_token_details.values()
                except Exception:
                    user = await user_service.get_user_by_user_id(session, user_id)
                    if user.is_oauth_account:
                        await user_session_service.invalidate_all_user_sessions_by_user_id(session, user_id)
                    else:
                        await user_spotify_oauth_account_service.delete_spotify_oauth_account_by_user_id(session, user_id)

                    raise HTTPException(status_code=401, detail="Failed to refresh Spotify access token")

                await user_spotify_oauth_account_service.update_oauth_tokens(
                    session,
                    user_id,
                    spotify_subscription,
                    encrypt_token(spotify_access_token),
                    spotify_expires_in_seconds
                )
            else:
                spotify_access_token = decrypt_token(user_spotify_oauth_account.encrypted_access_token)
                spotify_subscription = user_spotify_oauth_account.subscription

    return spotify_access_token, spotify_subscription