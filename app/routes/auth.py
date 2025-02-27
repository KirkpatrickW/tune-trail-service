import bcrypt
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from sqlalchemy.ext.asyncio import AsyncSession

from config.logger import Logger

from clients.postgresql_client import PostgreSQLClient

from dependencies.validate_jwt import access_token_data_ctx, validate_jwt
from dependencies.validate_spotify_account import validate_spotify_account

from models.schemas.auth.complete_spotify_request import CompleteSpotifyRequest
from models.schemas.auth.register_request import RegisterRequest
from models.schemas.auth.spotify_oauth_callback_params import SpotifyOAuthCallbackParams, SpotifyOAuthType

from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService
from services.postgresql.user_spotify_oauth_account_service import UserSpotifyOAuthAccountService
from services.providers.spotify_service import SpotifyService

from utils.jwt_helper import create_access_token, decode_access_token
from utils.routes.auth_utils import connect_spotify, fetch_or_refresh_spotify_access_token, link_spotify

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

    access_token = create_access_token(user_id, str(user_session.user_session_id))

    return { "access_token": access_token }


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

    access_token = create_access_token(user_id, str(user_session.user_session_id), await fetch_or_refresh_spotify_access_token(session, user_id))

    return { "access_token": access_token }


@auth_router.get("/spotify-oauth-callback")
async def spotify_oauth_callback(request: Request, spotify_oauth_callback_params: SpotifyOAuthCallbackParams = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    type = spotify_oauth_callback_params.type

    base_url = str(request.base_url)
    path = request.url.path

    redirect_uri = base_url.rstrip("/") + path

    if type == SpotifyOAuthType.CONNECT:
        return await connect_spotify(session, spotify_oauth_callback_params.code, redirect_uri)
    
    if type == SpotifyOAuthType.LINK:
        # Decode the JWT token from state, emulating the logic of the validate_jwt decorator
        # This is necessary as Spotify only allows state as a passthrough, not the actual JWT token
        access_token_data = decode_access_token(token_override=spotify_oauth_callback_params.jwt_token)
        if access_token_data["is_expired"]:
            raise HTTPException(status_code=401, detail="Token has expired")

        return await link_spotify(session, spotify_oauth_callback_params.code, redirect_uri, access_token_data["payload"]["user_id"])


@auth_router.put("/complete-spotify", dependencies=[
    Depends(validate_jwt),
    Depends(validate_spotify_account)
])
async def complete_spotify(complete_spotify_request: CompleteSpotifyRequest, session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_id = access_token_data["payload"]["user_id"]

    async with session.begin():
        await user_service.set_oauth_account_username(session, user_id, complete_spotify_request.username)
    
    return {"message": "Spotify account setup complete"}


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

    new_access_token = create_access_token(user_id, access_token["user_session_id"], None)

    return { "access_token": new_access_token }


@auth_router.put("/logout", dependencies=[
    Depends(validate_jwt)
])
async def logout(session: AsyncSession = Depends(postgresql_client.get_session)):
    access_token_data = access_token_data_ctx.get()
    user_session_id = access_token_data["payload"]["user_session_id"]

    async with session.begin():
        await user_session_service.invalidate_user_session(session, user_session_id)

    return {"message": "Logged out successfully"}


@auth_router.put("/refresh-token")
async def refresh_token(access_token_data: dict = Depends(decode_access_token), session: AsyncSession = Depends(postgresql_client.get_session)):
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
        
        new_access_token = create_access_token(user_id, user_session_id, await fetch_or_refresh_spotify_access_token(session, user_id))
        await user_session_service.refresh_user_session_expiry(session, user_session_id)

    return { "access_token": new_access_token }