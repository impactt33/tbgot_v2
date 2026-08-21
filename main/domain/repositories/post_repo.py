from abc import abstractmethod, ABC
from datetime import datetime

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
    async def claim_scheduled(self, limit: int = 10) -> list[PostEntity]:
        ...

    @abstractmethod
    async def schedule(self, post_id: int, when: datetime) -> PostEntity | None:
        ...