from abc import ABC, abstractmethod

from main.domain.entities import ChannelEntity, ChannelAddEntity


class ChannelService(ABC):
    @abstractmethod
    async def get_channel_by_id(self, channel_id: int) -> ChannelEntity:
        ...

    @abstractmethod
    async def get_channel_by_username(self, username: str) -> ChannelEntity:
        ...

    @abstractmethod
    async def find_channel_by_id(self, channel_id: int) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def find_channel_by_username(self, username: str) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def add_channel(self, channel: ChannelAddEntity) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def remove_channel(self, channel_id: int) -> ChannelEntity | None:
        ...

    @abstractmethod
    async def get_list_channels(self) -> list[ChannelEntity]:
        ...
