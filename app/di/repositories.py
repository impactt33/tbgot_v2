from dishka import Provider, Scope, provide

from main.data.repositories_impl import UserRepoImpl, ChannelRepoImpl
from main.domain.repositories import UserRepo, ChannelRepo


class RepoProvider(Provider):
    scope = Scope.REQUEST

    user_repo = provide(UserRepoImpl, provides=UserRepo)
    channel_repo = provide(ChannelRepoImpl, provides=ChannelRepo)