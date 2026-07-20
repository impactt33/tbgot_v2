import asyncio
import logging

from aiogram import Bot, Dispatcher

from core.config import settings, setup_logging
from main.presentation.handlers import command_router, callback_router, message_router


async def main() -> None:
    setup_logging(log_level="DEBUG")
    logger = logging.getLogger(__name__)
    logger.info(f"Bot started")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(command_router)
    dp.include_router(callback_router)
    dp.include_router(message_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())