from fastapi import APIRouter, Depends, File, UploadFile
from apps.user_service.service import UserService
from apps.user_service.scheme import (
    CreateUserScheme,
    BaseUserScheme,
    UpdateProfileScheme,
    UpdatePasswordRequestScheme,
)
from database.user_database import get_user_sesison
from utils.utils import get_rmq_connection, get_redis_cli
from aio_pika import RobustConnection
from redis.asyncio import StrictRedis
from sqlalchemy.ext.asyncio import AsyncSession
from utils.utils import get_current_user


user_service_router = APIRouter(tags=["User Service"], prefix="/user/api/v1")


@user_service_router.post("/create-user/", response_model=CreateUserScheme)
async def create_user(
    request: CreateUserScheme, session: AsyncSession = Depends(get_user_sesison)
):
    service = UserService(session=session)
    return await service._create_user(request=request)


@user_service_router.get("/get-user/{user_id}/", response_model=BaseUserScheme)
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_user_sesison),
    rmq_cli: RobustConnection = Depends(get_rmq_connection),
    redis_cli: StrictRedis = Depends(get_redis_cli),
):
    service = UserService(session=session, redis_cli=redis_cli, rmq_cli=rmq_cli)
    return await service._get_user_by_id(user_id=user_id)


@user_service_router.get(
    "/get-user-by-username/{username}/", response_model=BaseUserScheme
)
async def get_user_by_username(
    username: str,
    session: AsyncSession = Depends(get_user_sesison),
    rmq_cli: RobustConnection = Depends(get_rmq_connection),
    redis_cli: StrictRedis = Depends(get_redis_cli),
):
    service = UserService(session=session, redis_cli=redis_cli, rmq_cli=rmq_cli)
    return await service._get_user_by_username(username=username)


@user_service_router.get(
    "/get-user-by-credeltions/{username}/{password}/", response_model=BaseUserScheme
)
async def get_user_by_credeltions(
    username: str,
    password: str,
    session: AsyncSession = Depends(get_user_sesison),
    rmq_cli: RobustConnection = Depends(get_rmq_connection),
):
    service = UserService(session=session, rmq_cli=rmq_cli)
    return await service._get_user_by_username_password(
        username=username, password=password
    )


@user_service_router.patch("/update-profile/", response_model=UpdateProfileScheme)
async def update_profile(
    request: UpdateProfileScheme,
    session: AsyncSession = Depends(get_user_sesison),
    current_user: BaseUserScheme = Depends(get_current_user),
):
    service = UserService(session=session, current_user=current_user)
    return await service._update_profile_components(request=request)


@user_service_router.patch("/update-profile-picture/")
async def upload_profile_picture(
    picture: UploadFile = File(...),
    current_user: BaseUserScheme = Depends(get_current_user),
    session: AsyncSession = Depends(get_user_sesison),
):
    service = UserService(current_user=current_user, session=session)
    return await service._upload_profile_picture(picture=picture)


@user_service_router.patch(
    "/update-password/", response_model=dict
)
async def update_password(
    request: UpdatePasswordRequestScheme,
    session: AsyncSession = Depends(get_user_sesison),
    current_user: BaseUserScheme = Depends(get_current_user),
):
    service = UserService(session=session, current_user=current_user)
    return await service._update_user_password(request=request)
