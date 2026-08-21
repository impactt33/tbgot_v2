from main.domain.clients import Publisher
from main.domain.entities import PostEntity
from main.domain.enums import PostStatus
from main.domain.errors import PostAlreadyPublishedError, PublisherError
from main.domain.services import PostService


class PublishPostUseCase:
    def __init__(self, publisher: Publisher, post_service: PostService):
        self.publisher = publisher
        self.post_service = post_service

    async def __call__(self, post_id: int) -> PostEntity:
        post = await self.post_service.get_by_id(post_id)

        if post.status is PostStatus.PUBLISHED:
            raise PostAlreadyPublishedError(post_id)

        try:
            message_id = await self.publisher.publish(post, post.channel_id)
        except PublisherError:
            await self.post_service.mark_failed(post_id)
            raise

        return await self.post_service.mark_published(post_id, message_id)

class PreviewPostUseCase:
    def __init__(self, publisher: Publisher, post_service: PostService):
        self.publisher = publisher
        self.post_service = post_service

    async def __call__(self, post_id: int, admin_id: int) -> int:
        post = await self.post_service.get_by_id(post_id)
        return await self.publisher.publish(post, admin_id)