from dishka import Provider, Scope, provide

from main.data.repositories_impl import UserRepoImpl, ChannelRepoImpl, QuizTopicRepoImpl, PostRepoImpl, \
    SourceRepoImpl, MaterialRepoImpl
from main.domain.repositories import UserRepo, ChannelRepo, QuizTopicRepo, PostRepo, SourceRepo, MaterialRepo


class RepoProvider(Provider):
    scope = Scope.REQUEST

    user_repo = provide(UserRepoImpl, provides=UserRepo)
    channel_repo = provide(ChannelRepoImpl, provides=ChannelRepo)
    quiz_topic_repo = provide(QuizTopicRepoImpl, provides=QuizTopicRepo)
    post_repo = provide(PostRepoImpl, provides=PostRepo)
    source_repo = provide(SourceRepoImpl, provides=SourceRepo)
    material_repo = provide(MaterialRepoImpl, provides=MaterialRepo)