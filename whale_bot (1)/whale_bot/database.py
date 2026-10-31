from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import settings
from models import Base

engine = create_async_engine(settings.database_url)
SessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Для старта хватает create_all; для продакшена подключите Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class DbSessionMiddleware(BaseMiddleware):
    """Одна сессия на апдейт: передаётся в хендлеры как `session`, коммит после обработки."""

    async def __call__(self, handler, event, data):
        async with SessionMaker() as session:
            data["session"] = session
            result = await handler(event, data)
            await session.commit()
            return result
