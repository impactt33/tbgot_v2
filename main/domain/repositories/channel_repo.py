from abc import ABC, abstractmethod

from main.domain.entities import ChannelAddEntity, ChannelEntity


class ChannelRepo(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def get_by_channel_id(self, channel_id: int) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def add_channel(self, channel: ChannelAddEntity) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def remove_channel(self, channel_id: int) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def set_storage_channel(
        self, channel_id: int, storage_channel_id: int | None
    ) -> ChannelEntity | None:
        """Bind (or, with None, unbind) the storage channel. None if no such channel."""

    @abstractmethod
    async def list_all(self) -> list[ChannelEntity]:
        ...