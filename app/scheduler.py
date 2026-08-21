import asyncio
import logging

from dishka import AsyncContainer

from main.domain.services import PostService
from main.domain.use_cases.publish_post import PublishPostUseCase

logger = logging.getLogger(__name__)


async def run_scheduler(container: AsyncContainer, interval: int = 60) -> None:
    while True:
        try:
            async with container() as request_container:
                post_service = await request_container.get(PostService)
                publish = await request_container.get(PublishPostUseCase)

                for post in await post_service.claim_due():
                    try:
                        await publish(post.id)
                    except Exception:
                        logger.exception("Failed to publish post %s", post.id)
        except Exception:
            logger.exception("Failure in publisher cycle")
        await asyncio.sleep(interval)