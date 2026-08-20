from dishka import Provider, Scope, provide

from main.domain.services import UserService, QuizTopicService
from main.domain.services.channel_service import ChannelService
from main.domain.services.post_service import PostService
from main.domain.services_impl import UserServiceImpl
from main.domain.services_impl.channel_service_impl import ChannelServiceImpl
from main.domain.services_impl.post_service_impl import PostServiceImpl
from main.domain.services_impl.quiz_topic_service_impl import QuizTopicServiceImpl


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    user_service = provide(UserServiceImpl, provides=UserService)
    channel_service = provide(ChannelServiceImpl, provides=ChannelService)
    quiz_topic_service = provide(QuizTopicServiceImpl, provides=QuizTopicService)
    post_service = provide(PostServiceImpl, provides=PostService)