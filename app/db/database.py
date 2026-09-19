import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_POOLED")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment")

database_url = make_url(DATABASE_URL)
query = dict(database_url.query)
query.pop("channel_binding", None)
query.pop("sslmode", None)
database_url = database_url.set(query=query)

engine = create_async_engine(
    database_url,
    connect_args={"ssl": "require"},
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        yield db