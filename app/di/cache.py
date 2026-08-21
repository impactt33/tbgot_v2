from dishka import Provider, Scope

from main.data.cache_impl import RoleCacheImpl
from main.domain.cache import RoleCache


class CacheProvider(Provider):
    scope = Scope.APP

    def role_cache(self) -> RoleCache:
        return RoleCacheImpl()