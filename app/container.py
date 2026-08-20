from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider

from app.di import ConfigProvider, DatabaseProvider, ServiceProvider, RepoProvider, ClientProvider, UseCaseProvider

container = make_async_container(
    ConfigProvider(),
    DatabaseProvider(),
    ClientProvider(),
    RepoProvider(),
    ServiceProvider(),
    UseCaseProvider(),
    AiogramProvider()
)