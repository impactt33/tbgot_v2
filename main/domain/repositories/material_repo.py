from abc import ABC, abstractmethod

from main.domain.entities import AddMaterialEntity, MaterialEntity


class MaterialRepo(ABC):
    @abstractmethod
    async def find_by_id(self, material_id: int) -> MaterialEntity | None:
        ...

    @abstractmethod
    async def find_by_file(self, channel_id: int, file_unique_id: str) -> MaterialEntity | None:
        """The deduplication lookup: has this exact file been taken already?

        None means the file is new for this channel.
        """

    @abstractmethod
    async def add_material(self, material: AddMaterialEntity) -> MaterialEntity | None:
        """None, if this file is already stored for this channel."""

    @abstractmethod
    async def mark_used(self, material_id: int, post_id: int) -> MaterialEntity | None:
        ...

    @abstractmethod
    async def delete_unused(self, material_id: int) -> MaterialEntity | None:
        """Returns None if the material doesn't exist or is already used in a post."""
