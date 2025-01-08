from fastapi import FastAPI
from database.user_database import user_engine, UserBase
from apps.user_service.router import user_service_router


app = FastAPI(title="Github Projects")


app.include_router(user_service_router)


async def create_teables():
    async with user_engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)


@app.on_event("startup")
async def on_startup():
    return await create_teables()
