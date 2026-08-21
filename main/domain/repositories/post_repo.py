from abc import abstractmethod, ABC

from main.domain.entities import PostEntity, PostCreateEntity


class PostRepo(ABC):
    @abstractmethod
    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        ...

    @abstractmethod
    async def find_by_id(self, post_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def mark_failed(self, post_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def get_scheduled(self, limit: int = 10) -> list[PostEntity]:
        ...