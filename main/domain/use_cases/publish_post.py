import logging

from main.domain.clients import Publisher
from main.domain.entities import PostEntity
from main.domain.services import PostService

logger = logging.getLogger(__name__)


class PublishPostUseCase:
    """Publishing is always claim -> send -> mark.

    The claim is what makes it safe for two callers to want the same post at
    once: the admin tapping "Publish now" and the scheduler picking the post up
    on the same second. Whoever wins the UPDATE owns the post; the loser finds
    nothing to claim and stops before the Telegram call.
    """

    def __init__(self, publisher: Publisher, post_service: PostService):
        self.publisher = publisher
        self.post_service = post_service

    async def __call__(self, post_id: int) -> PostEntity:
        """Manual path: claim the post here, then publish it.

        Raises PostNotDraftError when there is nothing left to claim — the post
        was published already, or the scheduler took it a moment ago.
        """
        post = await self.post_service.claim_for_publishing(post_id)
        return await self.publish_claimed(post)

    async def publish_claimed(self, post: PostEntity) -> PostEntity:
        """Scheduler path: claim_due has already moved the post to PUBLISHING."""
        try:
            message_id = await self.publisher.publish(post, post.channel_id)
        except Exception:
            # Every exception, not only PublisherError. A post left in
            # PUBLISHING is picked up by nobody, because claim_scheduled
            # selects SCHEDULED and nothing else — so a payload that fails
            # model_validate used to strand the post there for good.
            await self._mark_failed(post.id)
            raise

        return await self.post_service.mark_published(post.id, message_id)

    async def _mark_failed(self, post_id: int) -> None:
        """Bookkeeping must never hide the error that caused it."""
        try:
            await self.post_service.mark_failed(post_id)
        except Exception:
            logger.exception("Could not mark post %s as failed", post_id)


class PreviewPostUseCase:
    def __init__(self, publisher: Publisher, post_service: PostService):
        self.publisher = publisher
        self.post_service = post_service

    async def __call__(self, post_id: int, admin_id: int) -> int:
        post = await self.post_service.get_by_id(post_id)
        return await self.publisher.publish(post, admin_id)
