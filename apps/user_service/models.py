from database.user_database import UserBase
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class UserModel(UserBase):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    profile_picture: Mapped[str] = mapped_column(String, nullable=True)

    name: Mapped[str] = mapped_column(String, nullable=True)
    surname: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)

    gender: Mapped[str] = mapped_column(String, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    social_link: Mapped[str] = mapped_column(String, nullable=True)

    bio: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)
