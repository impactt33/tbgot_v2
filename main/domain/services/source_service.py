from abc import ABC, abstractmethod

from main.domain.entities import SourceEntity, AddSourceEntity


class SourceService(ABC):
    @abstractmethod
    async def get_source_urls(self, channel_id: int) -> list[str]:
        ...

    @abstractmethod
    async def find_unused(self, channel_id: int, limit: int = 10) -> list[SourceEntity]:
        ...

    @abstractmethod
    async def find_by_id(self, source_id: int) -> SourceEntity | None:
        ...

    @abstractmethod
    async def add_source(self, data: AddSourceEntity) -> SourceEntity | None:
        ...

    @abstractmethod
    async def mark_used(self, source_id: int, post_id: int) -> SourceEntity:
        ...

    @abstractmethod
    async def delete_unused(self, source_id: int) -> SourceEntity | None:
        """None doesn`t raise an error because it`s okay if source wasn`t delete. Check repo description."""
