from dishka import Provider, Scope, provide

from main.data.repositories_impl import UserRepoImpl, ChannelRepoImpl
from main.data.repositories_impl.post_repo_impl import PostRepoImpl
from main.data.repositories_impl.quiz_topic_repo_impl import QuizTopicRepoImpl
from main.domain.repositories import UserRepo, ChannelRepo, QuizTopicRepo, PostRepo


class RepoProvider(Provider):
    scope = Scope.REQUEST

    user_repo = provide(UserRepoImpl, provides=UserRepo)
    channel_repo = provide(ChannelRepoImpl, provides=ChannelRepo)
    quiz_topic_repo = provide(QuizTopicRepoImpl, provides=QuizTopicRepo)
    post_repo = provide(PostRepoImpl, provides=PostRepo)