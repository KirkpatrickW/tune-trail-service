from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.providers.spotify_service import SpotifyService

from utils.encryption_helper import decrypt_token, encrypt_token

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