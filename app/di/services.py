from dishka import Provider, Scope, provide

from main.domain.services import UserService
from main.domain.services_impl import UserServiceImpl


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    user_service = provide(UserServiceImpl, provides=UserService)