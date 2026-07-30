from dishka import Provider, Scope, provide

from core.config.settings import Settings
from core.config import settings

class ConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def settings(self) -> Settings:
        return settings