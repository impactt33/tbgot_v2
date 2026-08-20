from abc import ABC, abstractmethod

from main.domain.entities import PostCreateEntity, PostEntity


class PostService(ABC):
    @abstractmethod
    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        ...

    @abstractmethod
    async def find_by_id(self, post_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def get_by_id(self, post_id: int) -> PostEntity:
        ...

    @abstractmethod
    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity:
        ...

    @abstractmethod
    async def mark_failed(self, post_id: int) -> PostEntity:
        ...