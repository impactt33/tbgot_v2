from dishka import Provider, Scope, provide

from core.config.settings import Settings
from main.data.clients_impl.ai.gemini_ai_client import GeminiAIClient
from main.domain.clients import AIClient


class ClientProvider(Provider):
    scope = Scope.APP

    @provide
    def ai_client(self, settings: Settings) -> AIClient:
        return GeminiAIClient(api_key=settings.GEMINI_API_KEY)