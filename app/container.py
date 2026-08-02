from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider

from app.di import ConfigProvider, DatabaseProvider, ServiceProvider, RepoProvider, ClientProvider

container = make_async_container(
    ConfigProvider(),
    DatabaseProvider(),
    ClientProvider(),
    RepoProvider(),
    ServiceProvider(),
    AiogramProvider()
)