from pydantic import SecretStr, BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class DBSettingsScheme(BaseModel):
    username: str
    password: SecretStr
    host: str
    port: int


class RMQSettingsScheme(BaseModel):
    rmq_password: SecretStr
    rmq_username: str
    rmq_host: str
    rmq_port: int


class RedisSettingsScheme(BaseModel):
    redis_host: str
    redis_port: int


db_settings = DBSettingsScheme(
    username=os.getenv("PG_USERNAME"),
    password=os.getenv("PG_PASSWORD"),
    port=os.getenv("PG_PORT"),
    host=os.getenv("PG_HOST"),
)


redis_settings = RedisSettingsScheme(
    redis_host=os.getenv("REDIS_HOST"), redis_port=os.getenv("REDIS_PORT")
)

rmq_settings = RMQSettingsScheme(
    rmq_host=os.getenv("RMQ_HOST"),
    rmq_password=os.getenv("RMQ_PASSWORD"),
    rmq_port=os.getenv("RMQ_PORT"),
    rmq_username=os.getenv("RMQ_USERNAME"),
)


class AuthSettingsScheme(BaseModel):
    secret_key: SecretStr
    algoritm: str
    accsess_token_expire_days: int



auth_settings = AuthSettingsScheme(
    secret_key=os.getenv("SECRET_KEY"),
    accsess_token_expire_days=365,
    algoritm="HS256",
    
)