from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider

from app.di import *

container = make_async_container(
    ConfigProvider(),
    DatabaseProvider(),
    RepoProvider(),
    ServiceProvider(),
    AiogramProvider()
)