from dishka import Provider, Scope, provide

from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.domain.services_impl import UserServiceImpl
from main.domain.services_impl.channel_service_impl import ChannelServiceImpl


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    user_service = provide(UserServiceImpl, provides=UserService)
    channel_service = provide(ChannelServiceImpl, provides=ChannelService)