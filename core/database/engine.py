from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings

engine = create_async_engine(url=settings.SQLALCHEMY_DATABASE_URL)