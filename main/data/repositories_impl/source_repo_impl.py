from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import Source
from main.domain.entities import SourceEntity, AddSourceEntity
from main.domain.repositories.source_repo import SourceRepo


class SourceRepoImpl(SourceRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, source_id: int) -> SourceEntity | None:
        source: Source | None = await self.session.scalar(
            select(Source)
            .where(Source.id == source_id)
        )

        return source.to_entity() if source is not None else None

    async def get_source_urls(self, channel_id: int) -> list[str]:
        sources = await self.session.scalars(
            select(Source.url).where(Source.channel_id == channel_id)
        )

        return list(sources.all())

    async def find_unused(self, channel_id: int, limit: int) -> list[SourceEntity]:
        sources = await self.session.scalars(
            select(Source)
            .where(
                Source.channel_id == channel_id,
                Source.used_in_post.is_(None)
            )
            .order_by(Source.created_at)
            .limit(limit)
        )

        return [source.to_entity() for source in sources.all()]

    async def add_source(self, source: AddSourceEntity) -> SourceEntity | None:
        source: Source | None = await self.session.scalar(
            insert(Source)
            .values(channel_id=source.channel_id, name=source.name, url=source.url)
            .on_conflict_do_nothing(index_elements=["channel_id", "url"])
            .returning(Source)
        )
        await self.session.commit()
        return source.to_entity() if source is not None else None

    async def mark_used(self, source_id: int, post_id: int) -> SourceEntity | None:
        source: Source | None = await self.session.scalar(
            update(Source)
            .where(Source.id == source_id)
            .values(used_in_post=post_id)
            .returning(Source)
        )
        await self.session.commit()
        return source.to_entity() if source is not None else None

    async def delete_unused(self, source_id: int) -> SourceEntity | None:
        source: Source | None = await self.session.scalar(
            delete(Source)
            .where(
                Source.id == source_id,
                Source.used_in_post.is_(None)
            )
            .returning(Source)
        )
        await self.session.commit()
        return source.to_entity() if source is not None else None