from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import Material
from main.domain.entities import AddMaterialEntity, MaterialEntity
from main.domain.repositories.material_repo import MaterialRepo


class MaterialRepoImpl(MaterialRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, material_id: int) -> MaterialEntity | None:
        material: Material | None = await self.session.scalar(
            select(Material)
            .where(Material.id == material_id)
        )

        return material.to_entity() if material is not None else None

    async def find_by_file(self, channel_id: int, file_unique_id: str) -> MaterialEntity | None:
        material: Material | None = await self.session.scalar(
            select(Material)
            .where(
                Material.channel_id == channel_id,
                Material.file_unique_id == file_unique_id
            )
        )

        return material.to_entity() if material is not None else None

    async def add_material(self, material: AddMaterialEntity) -> MaterialEntity | None:
        added: Material | None = await self.session.scalar(
            insert(Material)
            .values(
                channel_id=material.channel_id,
                file_unique_id=material.file_unique_id,
                source_chat_id=material.source_chat_id,
                source_username=material.source_username,
                source_message_id=material.source_message_id,
                storage_chat_id=material.storage_chat_id,
                storage_message_id=material.storage_message_id,
            )
            .on_conflict_do_nothing(index_elements=["channel_id", "file_unique_id"])
            .returning(Material)
        )
        await self.session.commit()
        return added.to_entity() if added is not None else None

    async def mark_used(self, material_id: int, post_id: int) -> MaterialEntity | None:
        material: Material | None = await self.session.scalar(
            update(Material)
            .where(Material.id == material_id)
            .values(used_in_post=post_id)
            .returning(Material)
        )
        await self.session.commit()
        return material.to_entity() if material is not None else None

    async def delete_unused(self, material_id: int) -> MaterialEntity | None:
        material: Material | None = await self.session.scalar(
            delete(Material)
            .where(
                Material.id == material_id,
                Material.used_in_post.is_(None)
            )
            .returning(Material)
        )
        await self.session.commit()
        return material.to_entity() if material is not None else None
