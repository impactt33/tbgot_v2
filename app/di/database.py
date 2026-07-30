from typing import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession

from core.config.settings import Settings


class DatabaseProvider(Provider):
    scope = Scope.APP

    @provide
    async def engine(self, settings: Settings) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_size=settings.DB_MAX_POOL_SIZE
        )
        yield engine
        await engine.dispose()

    @provide
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self, maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with maker() as session:
            yield session