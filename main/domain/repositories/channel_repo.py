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