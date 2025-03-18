import bcrypt
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from sqlalchemy.ext.asyncio import AsyncSession

from config.logger import Logger
from clients.postgresql_client import PostgreSQLClient

from dependencies.validate_jwt import access_token_data_ctx, validate_jwt
from dependencies.validate_spotify_account import validate_spotify_account

from models.schemas.auth.complete_spotify_request import CompleteSpotifyRequest
from models.schemas.auth.register_request import RegisterRequest
from models.schemas.auth.spotify_oauth_request import SpotifyOAuthRequest

from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from services.providers.spotify_service import SpotifyService

from utils.jwt_helper import create_access_token, decode_access_token
from utils.encryption_helper import encrypt_token
from utils.routes.auth_utils import fetch_or_refresh_spotify_access_token_details

logger = Logger()

postgresql_client = PostgreSQLClient()

user_service = UserService()
user_spotify_oauth_account_service = UserSpotifyOAuthAccountService()
user_session_service = UserSessionService()

spotify_service = SpotifyService()

auth_router = APIRouter()

@auth_router.post("/register")
async def register(register_request: RegisterRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        user = await user_service.add_new_user(
            session,
            register_request.username, 
            bcrypt.hashpw(bytes(register_request.password, encoding='utf-8'), bcrypt.gensalt()))
        
        user_id = user.user_id
        user_session = await user_session_service.create_user_session(session, user_id)

    is_admin = user.is_admin
    access_token = create_access_token(user_id, str(user_session.user_session_id), is_admin)

    return { 
        "access_token": access_token,
        "user_details": {
            "user_id": user_id,
            "username": user.username,
            "is_admin": is_admin,
            "is_oauth_account": False,
            "spotify_subscription": None
        }
    }


@auth_router.post("/login")
async def login(credentials: HTTPBasicCredentials = Depends(HTTPBasic()), session: AsyncSession = Depends(postgresql_client.get_session)):
    username, password = credentials.username, credentials.password

    async with session.begin():
        user = await user_service.get_user_by_username(session, username)
        if not user:
            raise HTTPException(status_code=401, detail="Bad Username")
        
        if user.is_oauth_account:
            raise HTTPException(status_code=400, detail="This account was created using Spotify OAuth. Please log in with Spotify")
        
        if not bcrypt.checkpw(bytes(password, "UTF-8"), user.hashed_password):
            raise HTTPException(status_code=401, detail="Bad Password")

        user_id = user.user_id
        user_session = await user_session_service.create_user_session(session, user_id)
        spotify_access_token, spotify_subscription = await fetch_or_refresh_spotify_access_token_details(session, user_id)

    is_admin = user.is_admin
    access_token = create_access_token(user_id, str(user_session.user_session_id), is_admin, spotify_access_token)

    return { 
        "access_token": access_token,
        "user_details": {
            "user_id": user_id,
            "username": user.username,
            "is_admin": is_admin,
            "is_oauth_account": user.is_oauth_account,
            "spotify_subscription": spotify_subscription
        }
    }


@auth_router.put("/connect-spotify")
async def connect_spotify(spotify_oauth_request: SpotifyOAuthRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    spotify_oauth_token_details = await spotify_service.fetch_and_handle_oauth_token(spotify_oauth_request.auth_code)
    spotify_user_id, spotify_subscription, spotify_access_token, spotify_refresh_token, spotify_expires_in_seconds = spotify_oauth_token_details.values()

    async with session.begin():
        try:
            user, user_spotify_oauth_account = await user_spotify_oauth_account_service.add_new_user_with_spotify_oauth_account(
                session, 
                spotify_user_id,
                spotify_subscription, 
                encrypt_token(spotify_access_token), 
                encrypt_token(spotify_refresh_token), 
                spotify_expires_in_seconds)
        except HTTPException:
            user_spotify_oauth_account = await user_spotify_oauth_account_service.get_spotify_oauth_account_by_provider_user_id(session, spotify_user_id)
            user = await user_service.get_user_by_user_id(session, user_spotify_oauth_account.user_id)

            if not user.is_oauth_account:
                raise HTTPException(status_code=400, detail="This Spotify account is linked to a non-OAuth account")
            
            user_id = user.user_id
            await user_spotify_oauth_account_service.update_oauth_tokens(
                session,
                user_id,
                spotify_subscription,
                encrypt_token(spotify_access_token),
                spotify_expires_in_seconds,
                encrypt_token(spotify_refresh_token))
            
        user_session = await user_session_service.create_user_session(session, user_id)

    is_admin = user.is_admin
    access_token = create_access_token(user_id, str(user_session.user_session_id), is_admin, spotify_access_token)

    return { 
        "access_token": access_token,
        "user_details": {
            "user_id": user_id,
            "username": user.username,
            "is_admin": is_admin,
            "is_oauth_account": user.is_oauth_account,
            "spotify_subscription": spotify_subscription
        }
    }


@auth_router.put("/link-spotify", dependencies=[
    Depends(validate_jwt)
])
async def link_spotify(spotify_oauth_request: SpotifyOAuthRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_id = access_token_data["payload"]["user_id"]

    spotify_oauth_token_details = await spotify_service.fetch_and_handle_oauth_token(spotify_oauth_request.auth_code)
    spotify_user_id, spotify_subscription, spotify_access_token, spotify_refresh_token, spotify_expires_in_seconds = spotify_oauth_token_details.values()

    async with session.begin():
        await user_spotify_oauth_account_service.add_spotify_oauth_account_to_existing_user(
            session,
            user_id,
            spotify_user_id,
            spotify_subscription,
            encrypt_token(spotify_access_token),
            encrypt_token(spotify_refresh_token),
            spotify_expires_in_seconds)
        
        user_session = await user_session_service.create_user_session(session, user_id)

    access_token = create_access_token(user_id, str(user_session.user_session_id), access_token_data["payload"]["is_admin"], spotify_access_token)

    return { 
        "access_token": access_token,
        "user_details": {
            "spotify_subscription": spotify_subscription
        }
    }


@auth_router.put("/complete-spotify", dependencies=[
    Depends(validate_jwt),
    Depends(validate_spotify_account)
])
async def complete_spotify(complete_spotify_request: CompleteSpotifyRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_id = access_token_data["payload"]["user_id"]

    username = complete_spotify_request.username
    async with session.begin():
        await user_service.set_oauth_account_username(session, user_id, username)
    
    return { 
        "message": "Spotify account setup complete",
        "user_details": {
            "username": username
        }
    }


@auth_router.delete("/unlink-spotify", dependencies=[
    Depends(validate_jwt),
    Depends(validate_spotify_account)
])
async def unlink_spotify(session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    access_token = access_token_data["payload"]
    user_id = access_token["user_id"]

    async with session.begin():
        await user_spotify_oauth_account_service.delete_spotify_oauth_account_by_user_id(session, user_id)

    new_access_token = create_access_token(user_id, access_token["user_session_id"], access_token["is_admin"])

    return { 
        "access_token": new_access_token,
        "user_details": {
            "spotify_subscription": None
        }
    }


@auth_router.put("/logout", dependencies=[
    Depends(validate_jwt)
])
async def logout(session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_session_id = access_token_data["payload"]["user_session_id"]

    async with session.begin():
        await user_session_service.invalidate_user_session(session, user_session_id)

    return { "message": "Logged out successfully" }


# TODO: This looks like it is raising a 500 somewhere
@auth_router.put("/refresh-token")
async def refresh_token(access_token_data: dict = Depends(decode_access_token), session: AsyncSession = Depends(postgresql_client.get_session)):
    try:
        if not access_token_data["is_expired"]:
            raise HTTPException(status_code=400, detail="Token is still valid, refresh not needed")
        
        async with session.begin():
            access_token = access_token_data["payload"]
            user_session_id = access_token["user_session_id"]
            user_id = access_token["user_id"]
            user_session = await user_session_service.get_user_session_by_id(session, user_session_id)

            if not user_session or user_session.is_invalidated:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            if user_session.expires_at <= datetime.now(timezone.utc):
                await user_session_service.invalidate_user_session(session, user_session_id)
                raise HTTPException(status_code=401, detail="Session expired")
            
            spotify_access_token, spotify_subscription = await fetch_or_refresh_spotify_access_token_details(session, user_id)
            new_access_token = create_access_token(user_id, user_session_id, access_token["is_admin"], spotify_access_token)
            await user_session_service.refresh_user_session_expiry(session, user_session_id)

        return { 
            "access_token": new_access_token,
            "user_details": {
                "spotify_subscription": spotify_subscription
            }
        }
    except Exception as e:
        logger.error(e)
        raise e