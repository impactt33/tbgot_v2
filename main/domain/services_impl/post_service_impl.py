from main.domain.entities import PostEntity, PostCreateEntity
from main.domain.errors import PostNotFoundError, PostWasNotCreated
from main.domain.repositories import PostRepo
from main.domain.services.post_service import PostService


class PostServiceImpl(PostService):
    def __init__(self, post_repo: PostRepo):
        self.post_repo = post_repo

    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        draft = await self.post_repo.create_draft(data)

        if draft is None:
            raise PostWasNotCreated

        return draft

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
            raise PostNotFoundError(post_id)

        return post

    async def mark_failed(self, post_id: int) -> PostEntity:
        post = await self.post_repo.mark_failed(post_id)

        if post is None:
            raise PostNotFoundError(post_id)

        return post