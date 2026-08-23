from abc import ABC, abstractmethod

from main.domain.entities import SourceEntity, AddSourceEntity


class SourceRepo(ABC):
    @abstractmethod
    async def find_by_id(self, source_id: int) -> SourceEntity | None:
        ...

    @abstractmethod
    async def get_source_urls(self, channel_id: int) -> list[str]:
        """Use for prompt for model."""

    @abstractmethod
    async def find_unused(self, channel_id: int, limit: int) -> list[SourceEntity]:
        ...

    @abstractmethod
    async def add_source(self, source: AddSourceEntity) -> SourceEntity | None:
        """None, if already exists."""

    @abstractmethod
    async def mark_used(self, source_id: int, post_id: int) -> SourceEntity | None:
        ...

    @abstractmethod
    async def delete_unused(self, source_id: int) -> SourceEntity | None:
        """Returns None if topic doesn't exist or already used in post."""