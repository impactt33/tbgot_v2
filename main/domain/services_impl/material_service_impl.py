from main.domain.entities import AddMaterialEntity, MaterialEntity
from main.domain.errors import MaterialAlreadyUsedError, MaterialNotFoundError
from main.domain.repositories import MaterialRepo
from main.domain.services import MaterialService


class MaterialServiceImpl(MaterialService):
    def __init__(self, material_repo: MaterialRepo):
        self.material_repo = material_repo

    async def find_by_id(self, material_id: int) -> MaterialEntity | None:
        return await self.material_repo.find_by_id(material_id)

    async def get_by_id(self, material_id: int) -> MaterialEntity:
        material = await self.material_repo.find_by_id(material_id)

        if material is None:
            raise MaterialNotFoundError(material_id)

        return material

    async def find_by_file(self, channel_id: int, file_unique_id: str) -> MaterialEntity | None:
        return await self.material_repo.find_by_file(channel_id, file_unique_id)

    async def add_material(self, data: AddMaterialEntity) -> MaterialEntity:
        material = await self.material_repo.add_material(data)

        # None means the unique constraint bit: this file is already stored for
        # this channel. The admin forwarded something that was taken before.
        if material is None:
            raise MaterialAlreadyUsedError(data.file_unique_id)

        return material

    async def mark_used(self, material_id: int, post_id: int) -> MaterialEntity:
        material = await self.material_repo.mark_used(material_id, post_id)

        if material is None:
            raise MaterialNotFoundError(material_id)

        return material

    async def delete_unused(self, material_id: int) -> MaterialEntity | None:
        return await self.material_repo.delete_unused(material_id)
