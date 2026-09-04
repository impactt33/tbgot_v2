from dishka import Provider, Scope, provide

from main.domain.services import UserService, QuizTopicService, SourceService, ChannelService, PostService, \
    MaterialService
from main.domain.services_impl import UserServiceImpl, ChannelServiceImpl, QuizTopicServiceImpl, PostServiceImpl, \
    SourceServiceImpl, MaterialServiceImpl


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    user_service = provide(UserServiceImpl, provides=UserService)
    channel_service = provide(ChannelServiceImpl, provides=ChannelService)
    quiz_topic_service = provide(QuizTopicServiceImpl, provides=QuizTopicService)
    post_service = provide(PostServiceImpl, provides=PostService)
    source_service = provide(SourceServiceImpl, provides=SourceService)
    material_service = provide(MaterialServiceImpl, provides=MaterialService)