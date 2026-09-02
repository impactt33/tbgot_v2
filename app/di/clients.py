from collections.abc import AsyncIterable

import httpx
from aiogram import Bot
from dishka import Provider, Scope, provide, from_context

from core.config.settings import Settings
from main.data.clients_impl.ai.gemini_ai_client import GeminiAIClient
from main.data.clients_impl.telegram.telegram_publisher import TelegramPublisher
from main.data.clients_impl.web_search.serper_web_search_client import SerperWebSearchClient
from main.domain.clients import AIClient, WebSearchClient, Publisher
from main.presentation.utils.media_group import MediaGroupCollector


class ClientProvider(Provider):
    scope = Scope.APP

    bot = from_context(Bot, scope=Scope.APP)

    @provide
    def publisher(self, bot: Bot) -> Publisher:
        return TelegramPublisher(bot)

    @provide
    async def http_client(self) -> AsyncIterable[httpx.AsyncClient]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
          yield client

    @provide
    def ai_client(self, settings: Settings) -> AIClient:
        return GeminiAIClient(api_key=settings.GEMINI_API_KEY)

    @provide
    def web_search_client(
        self, settings: Settings, http_client: httpx.AsyncClient
    ) -> WebSearchClient:
        return SerperWebSearchClient(api_key=settings.SERPER_API_KEY, http_client=http_client)

    @provide
    def media_group_collector(self) -> MediaGroupCollector:
        """APP scope, not REQUEST: the parts of one album arrive as separate
        updates, so a per-request collector would never see more than one."""
        return MediaGroupCollector()
