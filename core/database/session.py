from functools import wraps
from typing import ParamSpec, TypeVar, Callable, Concatenate, Awaitable

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from core.database.engine import engine

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False
)

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")

def connection(
    method: Callable[
        Concatenate[T, AsyncSession, P],
        Awaitable[R]
    ]
) -> Callable[Concatenate[T, P], Awaitable[R]]:
    @wraps(method)
    async def wrapper(
        self: T,
        *args: P.args,
        **kwargs: P.kwargs
    ):
        async with async_session_maker() as session:
            try:
                return await method(
                    self,
                    *args,
                    session=session,
                    **kwargs
                )
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    return wrapper