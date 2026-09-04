from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import Channel
from main.domain.entities import ChannelEntity, ChannelAddEntity
from main.domain.repositories import ChannelRepo


class ChannelRepoImpl(ChannelRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> ChannelEntity | None:
        query = (
            select(Channel)
            .where(Channel.username == username)
        )

        channel: Channel | None = await self.session.scalar(query)

        return channel.to_entity() if channel is not None else None

    async def get_by_channel_id(self, channel_id: int) -> ChannelEntity | None:
        channel = await self.session.get(Channel, channel_id)

        return channel.to_entity() if channel is not None else None

    async def add_channel(self, channel: ChannelAddEntity) -> ChannelEntity | None:
        query = (
            insert(Channel)
            .values(channel_id=channel.channel_id, username=channel.username, title=channel.title)
            .on_conflict_do_nothing()
            .returning(Channel)
        )
        added_channel: Channel | None = await self.session.scalar(query)

        await self.session.commit()

        return added_channel.to_entity() if added_channel is not None else None

    async def remove_channel(self, channel_id: int) -> ChannelEntity | None:
        query = (
            delete(Channel)
            .where(Channel.channel_id == channel_id)
            .returning(Channel)
        )
        removed_channel: Channel | None = await self.session.scalar(query)

        await self.session.commit()

        return removed_channel.to_entity() if removed_channel is not None else None

    async def set_storage_channel(
        self, channel_id: int, storage_channel_id: int | None
    ) -> ChannelEntity | None:
        channel: Channel | None = await self.session.scalar(
            update(Channel)
            .where(Channel.channel_id == channel_id)
            .values(storage_channel_id=storage_channel_id)
            .returning(Channel)
        )
        await self.session.commit()
        return channel.to_entity() if channel is not None else None

    async def list_all(self) -> list[ChannelEntity]:
        query = (
            select(Channel)
            .order_by(Channel.added_at)
        )
        channels = await self.session.scalars(query)
        return [channel.to_entity() for channel in channels.all()]