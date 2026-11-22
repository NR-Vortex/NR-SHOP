from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

from sqlalchemy.engine import URL

from core.config import settings


DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",

    username=settings.POSTGRES_USER,

    password=settings.POSTGRES_PASSWORD.get_secret_value(),

    host=settings.DB_HOST,

    port=settings.DB_PORT,

    database=settings.POSTGRES_DB,
)


engine = create_async_engine(
    DATABASE_URL,

    echo=False,

    pool_pre_ping=True,
)


async_session = async_sessionmaker(
    bind=engine,

    expire_on_commit=False,
)


async def close_database():

    await engine.dispose()