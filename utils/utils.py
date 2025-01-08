from fastapi import HTTPException, Depends, security, status
from utils.scheme import SUser
from passlib.context import CryptContext
from config.config import rmq_settings, redis_settings
import logging
import colorlog
from redis.asyncio import StrictRedis
from datetime import datetime, timedelta
from jose import jwt, JWTError
import aio_pika
import json
import httpx
import os


SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ACCESS_TOKEN_EXPIRE_DAYS = 365
ALGORITHM = "HS256"


oauth2_scheme = security.OAuth2PasswordBearer(
    tokenUrl="http://localhost:8000/auth/service/api/v1/auth-login/",
)


pwd_password = CryptContext(schemes=["bcrypt"])


class Hash:
    def bcrypt(password: str) -> str:
        return pwd_password.hash(password)

    def verify(hashed_password, plain_password):
        return pwd_password.verify(hashed_password, plain_password)


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

handler = colorlog.StreamHandler()

formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
    datefmt=None,
    log_colors={
        "DEBUG": "blue",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)

handler.setFormatter(formatter)

log.addHandler(handler)


async def get_rmq_connection():
    connection = await aio_pika.connect_robust(
        f"amqp://{rmq_settings.rmq_username}:{rmq_settings.rmq_password.get_secret_value()}@{rmq_settings.rmq_host}:{rmq_settings.rmq_port}/"
    )
    try:
        yield connection
    finally:
        await connection.close()


async def get_redis_cli():
    return await StrictRedis(
        host=redis_settings.redis_host, port=redis_settings.redis_port
    )


async def consume_data(queue_name: str, connection: aio_pika.RobustConnection):

    async with connection.channel() as channel:
        queue = await channel.declare_queue(queue_name, durable=True)

        async for message in queue.iterator():
            async with message.process():
                try:
                    body_str = message.body.decode("utf-8")
                    json_data = json.loads(body_str)
                    return json_data
                except json.JSONDecodeError as e:
                    log.error("Error of decoding message %s:", e)
                    continue

    raise HTTPException(status_code=404, detail="User data not found in queue")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    connection: aio_pika.RobustConnection = Depends(get_rmq_connection),
) -> SUser:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Запрос к внешнему API для создания очереди
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8081/user/api/v1/get-user-by-username/{user_id}/"
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ошибка взаимодействия с внешним сервисом: {e}",
        )

    # Получение данных пользователя из очереди
    queue_name = f"get-user-by-username-{user_id}"
    user_data = await consume_data(queue_name, connection)
    user = SUser.parse_obj(user_data)

    return user


async def delete_file(file_path_root, file_name):

    file_path = os.path.join(file_path_root, file_name)
    if file_path:
        log.info("file deleted succsesfully %s", file_name)

    log.error("Error deleting file %s", file_name)
