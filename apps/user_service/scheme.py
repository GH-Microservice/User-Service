from pydantic import BaseModel
from typing import Optional


class CreateUserScheme(BaseModel):
    username: str
    password: str
    email: str


class BaseUserScheme(BaseModel):
    id: int
    username: str
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    social_link: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None


class GetUserRequest(BaseModel):
    username: str


class GetUserByUsernamePasswordScheme(BaseModel):
    username: str
    password: str


class UpdateProfileScheme(BaseModel):
    username: Optional[str] = None
    bio: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    social_link: Optional[str] = None


class UpdatePasswordRequestScheme(BaseModel):
    old_password: str
    new_password: str
