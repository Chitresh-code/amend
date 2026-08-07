from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.credentials import router as credentials_router
from app.config import settings
from app.db import close_pool, open_pool
from app.redis import close_redis, open_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await open_pool()
    open_redis()
    yield
    await close_redis()
    await close_pool()


app = FastAPI(title="Amend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(credentials_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
