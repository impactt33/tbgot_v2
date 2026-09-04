from abc import ABC, abstractmethod

from main.domain.entities import AddMaterialEntity, MaterialEntity


class MaterialService(ABC):
    @abstractmethod
    async def find_by_id(self, material_id: int) -> MaterialEntity | None:
        ...

    @abstractmethod
    async def get_by_id(self, material_id: int) -> MaterialEntity:
        """Raises MaterialNotFoundError."""

    @abstractmethod
    async def find_by_file(self, channel_id: int, file_unique_id: str) -> MaterialEntity | None:
        """None, if this file has not been taken for this channel yet."""

    @abstractmethod
    async def add_material(self, data: AddMaterialEntity) -> MaterialEntity:
        """Raises MaterialAlreadyUsedError if the file is already stored."""

    @abstractmethod
    async def mark_used(self, material_id: int, post_id: int) -> MaterialEntity:
        ...

    @abstractmethod
    async def delete_unused(self, material_id: int) -> MaterialEntity | None:
        ...
