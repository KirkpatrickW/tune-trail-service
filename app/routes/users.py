from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_cache.decorator import cache

from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.validate_jwt import validate_jwt
from dependencies.validate_admin import validate_admin

from decorators.handle_client_disconnect import handle_client_disconnect

from clients.postgresql_client import PostgreSQLClient

from models.schemas.search_params import SearchParams

from services.postgresql.user_service import UserService
from services.postgresql.user_session_service import UserSessionService

users_router = APIRouter()
postgresql_client = PostgreSQLClient()

user_service = UserService()
user_session_service = UserSessionService()

@users_router.get("/search", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
@handle_client_disconnect
@cache(expire=300)
async def search_users(request: Request, search_params: SearchParams = Depends(), session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        users = await user_service.search_users_by_username(session, search_params.q, search_params.offset)

    return users


@users_router.delete("/{user_id}", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
async def delete_user(user_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        await user_service.delete_user_by_user_id(session, user_id)

    return { "message": "Successfully deleted user" }


@users_router.patch("/{user_id}/invalidate-session", dependencies=[
    Depends(validate_jwt),
    Depends(validate_admin)
])
async def invalidate_user_sessions(user_id: int, session: AsyncSession = Depends(postgresql_client.get_session)):
    async with session.begin():
        user = await user_service.get_user_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await user_session_service.invalidate_all_user_sessions_by_user_id(session, user_id)

    return { "message": f"Successfully invalidated all sessions for {user.username}"}