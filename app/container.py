from aiogram import Bot
from dishka import make_async_container, AsyncContainer
from dishka.integrations.aiogram import AiogramProvider

from app.di import ConfigProvider, DatabaseProvider, ServiceProvider, RepoProvider, ClientProvider, UseCaseProvider, \
    CacheProvider


def create_container(bot: Bot) -> AsyncContainer:
    container = make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        ClientProvider(),
        RepoProvider(),
        ServiceProvider(),
        UseCaseProvider(),
        AiogramProvider(),
        CacheProvider(),
        context={Bot: bot}
    )

    return container