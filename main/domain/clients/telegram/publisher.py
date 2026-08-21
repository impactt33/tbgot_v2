from abc import ABC, abstractmethod

from main.domain.entities import PostEntity


class Publisher(ABC):
    @abstractmethod
    async def publish(self, post: PostEntity, chat_id: int) -> int:
        ...