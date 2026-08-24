import asyncio
import contextlib
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from dishka.integrations.aiogram import setup_dishka

from app.container import create_container
from app.scheduler import run_scheduler
from core.config import settings, setup_logging
from main.presentation.handlers import command_router, menu_router, post_router, error_router, admin_router
from main.presentation.middlewares import RoleMiddleware

FSM_TTL = timedelta(days=1)

async def main() -> None:
    setup_logging(log_level="DEBUG")
    logger = logging.getLogger(__name__)
    logger.info(f"Bot started")

    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        state_ttl=FSM_TTL,
        data_ttl=FSM_TTL
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Order matters: command_router first so no feature router can swallow /quit.
    dp.include_router(error_router)
    dp.include_router(command_router)
    dp.include_router(menu_router)
    dp.include_router(post_router)
    dp.include_router(admin_router)

    container = create_container(bot)

    setup_dishka(container=container, router=dp, auto_inject=True)

    role_middleware = RoleMiddleware()
    dp.message.outer_middleware(role_middleware)
    dp.callback_query.outer_middleware(role_middleware)

    scheduler_task = asyncio.create_task(run_scheduler(container))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task
        await container.close()
        await storage.close()
        await bot.session.close() #type: ignore


if __name__ == "__main__":
    asyncio.run(main())