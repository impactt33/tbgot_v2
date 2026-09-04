import asyncio
import logging

from dishka import AsyncContainer

from main.domain.entities import PostEntity
from main.domain.services import PostService
from main.domain.use_cases.publish_post import PublishPostUseCase

logger = logging.getLogger(__name__)


async def run_scheduler(container: AsyncContainer, interval: int = 60) -> None:
    while True:
        for post in await _claim_due(container):
            await _publish(container, post)

        await asyncio.sleep(interval)


async def _claim_due(container: AsyncContainer) -> list[PostEntity]:
    """Take the whole batch in one scope: it is a single statement anyway."""
    try:
        async with container() as request_container:
            post_service: PostService = await request_container.get(PostService)
            return await post_service.claim_due()
    except Exception:
        logger.exception("Failure while claiming due posts")
        return []


async def _publish(container: AsyncContainer, post: PostEntity) -> None:
    """A scope per post, not one scope for the batch.

    A scope is a session, and a failed statement poisons the session it ran on:
    every later post in the batch would die on InFailedSQLTransactionError
    instead of being published. Leaving the scope closes that session and
    discards it, so the next post starts on a clean one.
    """
    try:
        async with container() as request_container:
            publish = await request_container.get(PublishPostUseCase)
            await publish.publish_claimed(post)
    except Exception:
        logger.exception("Failed to publish post %s", post.id)
