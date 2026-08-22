import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka.integrations.aiogram import setup_dishka

from app.container import create_container
from app.scheduler import run_scheduler
from core.config import settings, setup_logging
from main.presentation.handlers import command_router, callback_router, message_router, error_router, admin_router
from main.presentation.middlewares import RoleMiddleware


async def main() -> None:
    setup_logging(log_level="DEBUG")
    logger = logging.getLogger(__name__)
    logger.info(f"Bot started")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(error_router)
    dp.include_router(command_router)
    dp.include_router(callback_router)
    dp.include_router(message_router)
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
        await bot.session.close() #type: ignore


if __name__ == "__main__":
    asyncio.run(main())