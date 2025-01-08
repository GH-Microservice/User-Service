from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, mapped_column, Mapped
from sqlalchemy import String, Integer, DateTime
from config.config import db_settings
from datetime import datetime

DATABASE_URL = f"postgresql+asyncpg://{db_settings.username}:{db_settings.password.get_secret_value()}@{db_settings.host}:{db_settings.port}/UserGDB"

user_engine = create_async_engine(DATABASE_URL)

async_session = sessionmaker(bind=user_engine, class_=AsyncSession)


class UserBase(DeclarativeBase):
    id: Mapped[int] = mapped_column(Integer, index=True, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())


async def get_user_sesison() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
