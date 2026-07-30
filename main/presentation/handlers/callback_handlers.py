import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ReplyKeyboardRemove
from dishka import FromDishka

from main.data.enums import UserRole
from main.data.repositories_impl import UserRepoImpl
from main.domain.services import UserService
from main.domain.services_impl import UserServiceImpl

callback_router = Router(name=__name__)

logger = logging.getLogger(__name__)

@callback_router.callback_query(F.data.startswith("provide_role_"))
async def provide_role_callback(callback: CallbackQuery, bot: Bot, state: FSMContext, user_service: FromDishka[UserService]):
    logger.debug(f"Got callback query {callback.data}")

    new_role_name = callback.data.removeprefix("provide_role_")

    new_role = UserRole(new_role_name)

    logger.debug(f"New role is {new_role}")

    data = await state.get_data()
    telegram_id = data.get("contact")

    await user_service.change_user_role(
        actor_telegram_id=callback.from_user.id,
        target_telegram_id=telegram_id,
        new_role=new_role
    )

    await state.clear()

    await callback.message.edit_text("Successfully changed role.", reply_markup=None)

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=f"Your role was changed to {new_role_name} by {callback.from_user.username}"
        )
    except TelegramForbiddenError:
        logger.info("User blocked the bot, notification failed", telegram_id)
        await callback.message.answer("Role was provided, but user blocked the bot.")
    except TelegramAPIError:
        logger.exception("Notification failed", telegram_id)