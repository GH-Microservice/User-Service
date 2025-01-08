from pydantic import BaseModel
from typing import Optional


class SUser(BaseModel):
    id: int
    username: str
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    social_link: Optional[str] = None
