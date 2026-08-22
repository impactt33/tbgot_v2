from dishka import Provider, Scope, provide

from main.data.cache_impl import RoleCacheImpl
from main.domain.cache import RoleCache


class CacheProvider(Provider):
    scope = Scope.APP

    @provide
    def role_cache(self) -> RoleCache:
        return RoleCacheImpl()