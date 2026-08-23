from main.domain.entities import SourceEntity, AddSourceEntity
from main.domain.errors import SourceNotFoundError
from main.domain.repositories import SourceRepo
from main.domain.services import SourceService


class SourceServiceImpl(SourceService):
    def __init__(self, source_repo: SourceRepo):
        self.source_repo = source_repo

    async def get_source_urls(self, channel_id: int) -> list[str]:
        return await self.source_repo.get_source_urls(channel_id)

    async def find_unused(self, channel_id: int, limit: int = 10) -> list[SourceEntity]:
        return await self.source_repo.find_unused(channel_id, limit)

    async def find_by_id(self, source_id: int) -> SourceEntity | None:
        return await self.source_repo.find_by_id(source_id)

    async def add_source(self, data: AddSourceEntity) -> SourceEntity | None:
        return await self.source_repo.add_source(data)

    async def mark_used(self, source_id: int, post_id: int) -> SourceEntity:
        source = await self.source_repo.mark_used(source_id, post_id)
        if source is None:
            raise SourceNotFoundError(source_id)

        return source

    async def delete_unused(self, source_id: int) -> SourceEntity | None:
        return await self.source_repo.delete_unused(source_id)