from fastapi import HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from apps.user_service.models import UserModel
from apps.user_service.scheme import (
    CreateUserScheme,
    BaseUserScheme,
    GetUserRequest,
    GetUserByUsernamePasswordScheme,
    UpdateProfileScheme,
    UpdatePasswordRequestScheme,
)
from utils.utils import Hash, log, delete_file
from sqlalchemy import select, or_
from redis.asyncio import StrictRedis
import aio_pika
import json
import os
import uuid
import aiofiles

MEDIA_ROOT = "media/user-pictures/"


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        redis_cli: StrictRedis = None,
        rmq_cli: aio_pika.RobustConnection = None,
        current_user: BaseUserScheme = None,
    ):
        self.session = session
        self.redis_cli = redis_cli
        self.rmq_cli = rmq_cli
        self.current_user = current_user

    async def _create_user(self, request: CreateUserScheme):
        exist_user = (
            (
                await self.session.execute(
                    select(UserModel).filter_by(
                        username=request.username, email=request.email
                    )
                )
            )
            .scalars()
            .first()
        )

        if exist_user:
            log.error("User all ready exist %s", request.username)
            raise HTTPException(detail=f"This User all ready exist", status_code=402)

        if len(request.username) < 6:
            log.error("username so short")
            raise HTTPException(
                detail=f"{request.username} is so short", status_code=402
            )

        hashed_pass = Hash.bcrypt(request.password)

        user_data = request.dict()
        user_data["password"] = hashed_pass

        user = UserModel(**user_data)

        self.session.add(user)
        await self.session.commit()
        return CreateUserScheme(**request.__dict__)

    async def _get_user_by_id(self, user_id: int):
        cached_data = await self.get_data_from_cache(f"get-user-by-id-{user_id}")

        if cached_data:
            if isinstance(cached_data, str):
                cached_data = json.loads(cached_data)

            response_json = cached_data
            await self.publish_message(
                message=json.dumps(cached_data),
                queues_name=f"get-user-by-id-{response_json.get('id')}",
            )

            log.info("Returning cached data %s", cached_data)
            return BaseUserScheme(**cached_data)

        user = (
            (await self.session.execute(select(UserModel).filter_by(id=user_id)))
            .scalars()
            .first()
        )

        if not user:
            log.info("User not found by field %s", user_id)
            raise HTTPException(
                detail=f"User Not Found By Field {user_id}", status_code=404
            )

        response = BaseUserScheme(**user.__dict__)
        message_json = json.dumps(response.dict())

        await self.redis_cli.setex(
            f"get-user-by-id-{user_id}", 100, json.dumps(response.dict())
        )
        await self.publish_message(
            message=message_json, queues_name=f"get-user-by-id-{user.id}"
        )

        return response

    async def _get_user_by_username(self, username: str):
        cached_data = await self.get_data_from_cache(f"get-user-by-username-{username}")

        if cached_data:
            if isinstance(cached_data, str):
                cached_data = json.loads(cached_data)

            response_json = cached_data
            await self.publish_message(
                message=json.dumps(cached_data),
                queues_name=f"get-user-by-username-{response_json.get('username')}",
            )

            log.info("Returning cached data %s", cached_data)
            return BaseUserScheme(**cached_data)

        user = (
            (await self.session.execute(select(UserModel).filter_by(username=username)))
            .scalars()
            .first()
        )

        if not user:
            log.info("User not found by field %s", username)
            raise HTTPException(
                detail=f"User Not Found By Field {username}", status_code=404
            )

        response = BaseUserScheme(**user.__dict__)
        message_json = json.dumps(response.dict())

        await self.redis_cli.setex(
            f"get-user-by-username-{username}", 100, json.dumps(response.dict())
        )
        await self.publish_message(
            message=message_json, queues_name=f"get-user-by-username-{user.username}"
        )

        return response

    async def _get_user_by_username_password(self, username: str, password: str):

        user = (
            (await self.session.execute(select(UserModel).filter_by(username=username)))
            .scalars()
            .first()
        )

        if not user:
            log.info("User not found by field %s", username)
            raise HTTPException(detail=f"User Not  {username}", status_code=404)

        if not Hash.verify(password, user.password):
            raise HTTPException(detail="User password error", status_code=402)

        response = BaseUserScheme(**user.__dict__)
        message_json = json.dumps(response.dict())

        await self.publish_message(
            message=message_json,
            queues_name=f"get-user-by-username-{user.username}-password-{password}",
        )

        return response

    async def _update_profile_components(self, request: UpdateProfileScheme):

        user = (
            (
                await self.session.execute(
                    select(UserModel).filter_by(id=self.current_user.id)
                )
            )
            .scalars()
            .first()
        )

        if not user:
            raise HTTPException(detail="Credential Error", status_code=403)

        for field, value in request.dict(exclude_unset=True).items():
            if (
                field
                in [
                    "username",
                    "email",
                    "bio",
                    "name",
                    "surname",
                    "location",
                    "gender",
                    "social_link",
                ]
                and value is not None
            ):
                setattr(user, field, value)

        if request.username and request.username != self.current_user.username:
            exist_username = (
                (
                    await self.session.execute(
                        select(UserModel).filter(
                            UserModel.username == request.username,
                            UserModel.id != self.current_user.id,
                        )
                    )
                )
                .scalars()
                .first()
            )

            if exist_username:
                log.info(
                    "User can't update username because this username is already used: %s",
                    request.username,
                )
                raise HTTPException(
                    detail=f"{request.username} is already used by another user!",
                    status_code=433,
                )

        await self.session.commit()
        return UpdateProfileScheme(**request.dict())

    async def _upload_profile_picture(self, picture: UploadFile = File(...)):

        user = (
            (
                await self.session.execute(
                    select(UserModel).filter_by(id=self.current_user.id)
                )
            )
            .scalars()
            .first()
        )

        if not user:
            raise HTTPException(detail="This is not your profile", status_code=433)

        if user.profile_picture is not None:
            await delete_file(file_name=user.profile_picture, file_path_root=MEDIA_ROOT)

        file_path = os.path.join(MEDIA_ROOT, picture.filename)

        picture.filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(MEDIA_ROOT, picture.filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await picture.read(1024):
                await out_file.write(content)
        log.info("Picture  saved at %s", file_path)

        user.profile_picture = picture.filename

        await self.session.commit()
        return {"detail": "Picture Updated Succsesfully"}

    async def _update_user_password(self, request: UpdatePasswordRequestScheme):
        user = (
            (
                await self.session.execute(
                    select(UserModel).filter_by(id=self.current_user.id)
                )
            )
            .scalars()
            .first()
        )

        if not user:
            log.error("Profile error")
            raise HTTPException(detail="Profile not found", status_code=404)

        if not Hash.verify(request.old_password, user.password):
            raise HTTPException(detail="User password error", status_code=402)

        hashed_password = Hash.bcrypt(request.new_password)

        user.password = hashed_password

        log.info("User password updated succsesfully")
        await self.session.commit()

        return {"detail": "Password Updated Succsesfully"}

    async def get_data_from_cache(self, key: str):
        cached_data = await self.redis_cli.get(key)
        if not cached_data:
            log.info("No yet data from cache %s", key)
            return None
        return json.loads(cached_data)

    async def publish_message(self, message, queues_name):
        async with self.rmq_cli.channel() as channel:

            queue_name = queues_name
            await channel.declare_queue(queue_name, durable=True)

            response = message

            log.info("Message published succsesfully %s", response)
            await channel.default_exchange.publish(
                aio_pika.Message(body=response.encode(), delivery_mode=2),
                routing_key=queue_name,
            )

            return message
