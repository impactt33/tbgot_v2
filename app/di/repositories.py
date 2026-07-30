from dishka import Provider, Scope, provide

from main.data.repositories_impl import UserRepoImpl
from main.domain.repositories import UserRepo


class RepoProvider(Provider):
    scope = Scope.REQUEST

    user_repo = provide(UserRepoImpl, provides=UserRepo)