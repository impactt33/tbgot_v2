from datetime import datetime

from main.domain.entities import PostEntity, PostCreateEntity
from main.domain.errors import PostNotFoundError, PostWasNotCreated, PostNotDraftError, PostNotScheduledError, \
    PostNotClaimedError
from main.domain.repositories import PostRepo
from main.domain.services.post_service import PostService


class PostServiceImpl(PostService):
    def __init__(self, post_repo: PostRepo):
        self.post_repo = post_repo

    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        return await self.post_repo.create_draft(data)

    async def find_by_id(self, post_id: int) -> PostEntity | None:
        return await self.post_repo.find_by_id(post_id)

    async def get_by_id(self, post_id: int) -> PostEntity:
        post = await self.post_repo.find_by_id(post_id)

        if post is None:
            raise PostNotFoundError(post_id)

        return post

    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity:
        post = await self.post_repo.mark_published(post_id, telegram_message_id)

        if post is None:
            raise PostNotClaimedError(post_id)

        return post

    async def mark_failed(self, post_id: int) -> PostEntity:
        post = await self.post_repo.mark_failed(post_id)

        if post is None:
            raise PostNotFoundError(post_id)

        return post

    async def claim_due(self, limit: int = 10) -> list[PostEntity]:
        return await self.post_repo.claim_scheduled(limit)

    async def claim_for_publishing(self, post_id: int) -> PostEntity:
        """Raises PostNotDraftError if there was nothing left to claim."""
        post = await self.post_repo.claim_for_publishing(post_id)

        if post is None:
            raise PostNotDraftError(post_id)

        return post

    async def schedule(self, post_id: int, when: datetime) -> PostEntity:
        post = await self.post_repo.schedule(post_id, when)

        if post is None:
            raise PostNotDraftError(post_id)

        return post

    async def find_scheduled(self, channel_id: int | None = None, limit: int = 20) -> list[PostEntity]:
        return await self.post_repo.find_scheduled(channel_id, limit)

    async def unschedule(self, post_id: int) -> PostEntity:
        post = await self.post_repo.unschedule(post_id)

        if post is None:
            raise PostNotScheduledError(post_id)

        return post

    async def delete_draft(self, post_id: int) -> PostEntity:
        post = await self.post_repo.delete_draft(post_id)

        if post is None:
            raise PostNotDraftError(post_id)

        return post