import asyncio
import time

from sqlalchemy.ext.asyncio import AsyncSession

from clients.http_client import HTTPClient
from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from utils.http_helpers import RetryConfig, handle_retry

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
PROFILE_URL = "https://api.spotify.com/v1/me"

CLIENT_ID = "cbdfa4fd597743bf814729bfd1595f82"
CLIENT_SECRET = "0c93e6f13ff54d998cfc055ab0f0dcd9"

class SpotifyService:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(SpotifyService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance


    def _init(self):
        self.app_token = {"access_token": None, "expires_at": 0}

        self.app_token_lock = asyncio.Lock()
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()

        self.retry_config = RetryConfig(
            self.rate_limit_event,
            max_retries=3,
            retry_after_fallback=30,
        )

        self.http_client = HTTPClient()
        self.user_service = UserService()
        self.user_spotify_oauth_account_service = UserSpotifyOAuthAccountService()
        self.user_session_service = UserSessionService()


    async def fetch_app_access_token(self):
        async with self.app_token_lock:
            if self.app_token["access_token"] and time.time() < self.app_token["expires_at"]:
                return self.app_token["access_token"]

            data = {"grant_type": "client_credentials"}
            auth = (CLIENT_ID, CLIENT_SECRET)

            try:
                token = await handle_retry(
                    self.retry_config,
                    "POST",
                    TOKEN_URL,
                    data=data,
                    auth=auth
                )
            except Exception:
                raise RuntimeError("Failed to obtain Spotify app access token.")

            self.app_token.update({
                "access_token": token["access_token"],
                "expires_at": time.time() + token["expires_in"] - 60
            })

            return self.app_token["access_token"]


    async def fetch_and_handle_oauth_token(self, session: AsyncSession, auth_code: str, redirect_uri: str):
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri
        }
        auth = (CLIENT_ID, CLIENT_SECRET)

        oauth_token_response = await handle_retry(
            self.retry_config,
            "POST",
            TOKEN_URL,
            data=data,
            auth=auth
        )

        user_profile_response = await self.get_user_profile(oauth_token_response["access_token"])

        provider_user_id = user_profile_response["id"]
        async with session.begin():
            user_spotify_oauth_account = await self.user_spotify_oauth_account_service.get_spotify_oauth_account_by_provider_user_id(
                session, 
                provider_user_id)
            
            if user_spotify_oauth_account:
                user_id = user_spotify_oauth_account.user_id

                # Invalidate all user sessions because getting a new refresh_token invalidates the previous ones.
                self.user_session_service.invalidate_all_user_sessions_by_user_id(session, user_id)

                user = await self.user_service.get_user_by_user_id(session, user_id)
                if not user.is_oauth_account:
                    # Delete the Spotify OAuth account only if the user is not an OAuth account (unlinking) as this 
                    # account is integral to users who used Spotify OAuth for registration, oauth tokens will be updated
                    # in the database upon relogin.
                    await self.user_spotify_oauth_account_service.delete_spotify_oauth_account_by_user_id(session, user_id)

        return {
            "provider_user_id": user_profile_response["id"],
            "access_token": oauth_token_response["access_token"],
            "refresh_token": oauth_token_response["refresh_token"],
            "expires_in_seconds": oauth_token_response["expires_in"]
        }


    async def renew_user_access_token(self, refresh_token: str):
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        auth = (CLIENT_ID, CLIENT_SECRET)

        return await handle_retry(
            self.retry_config,
            "POST",
            TOKEN_URL,
            data=data,
            auth=auth
        )


    async def get_user_profile(self, access_token: str):
        headers = { "Authorization": f"Bearer {access_token}" }
        return await handle_retry(
            self.retry_config,
            "GET",
            PROFILE_URL,
            headers=headers
        )


    async def search_tracks(self, query: str, offset: int, limit: int):
        app_access_token = await self.fetch_app_access_token()
        headers = { "Authorization": f"Bearer {app_access_token}" }
        params = { "q": query, "type": "track", "offset": offset, "limit": limit }

        return await handle_retry(
            self.retry_config,
            "GET",
            SEARCH_URL,
            params=params,
            headers=headers
        )