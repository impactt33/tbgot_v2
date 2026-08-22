from main.domain.entities import ChannelEntity, ChannelAddEntity
from main.domain.errors import ChannelNotFoundError, ChannelAlreadyAddedError
from main.domain.repositories import ChannelRepo
from main.domain.services.channel_service import ChannelService


class ChannelServiceImpl(ChannelService):
    def __init__(self, channel_repo: ChannelRepo):
        self.channel_repo = channel_repo

    async def get_channel_by_id(self, channel_id: int) -> ChannelEntity:
        channel = await self.channel_repo.get_by_channel_id(channel_id)

        if channel is None:
            raise ChannelNotFoundError(channel_id=channel_id)

        return channel

    async def get_channel_by_username(self, username: str) -> ChannelEntity:
        channel = await self.channel_repo.get_by_username(username)

        if channel is None:
            raise ChannelNotFoundError(username=username)

        return channel

    async def find_channel_by_id(self, channel_id: int) -> ChannelEntity | None:
        channel = await self.channel_repo.get_by_channel_id(channel_id)

        return channel

    async def find_channel_by_username(self, username: str) -> ChannelEntity | None:
        channel = await self.channel_repo.get_by_username(username)

        return channel

    async def add_channel(self, channel: ChannelAddEntity) -> ChannelEntity | None:
        added_channel = await self.channel_repo.add_channel(channel)

        if added_channel is None:
            raise ChannelAlreadyAddedError()

        return added_channel

    async def remove_channel(self, channel_id: int) -> ChannelEntity | None:
        removed_channel = await self.channel_repo.remove_channel(channel_id)

        if removed_channel is None:
            raise ChannelNotFoundError(channel_id=channel_id)

        return removed_channel

    async def list_channels(self) -> list[ChannelEntity]:
        return await self.channel_repo.list_all()