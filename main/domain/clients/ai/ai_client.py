from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)

class AIClient(ABC):
    @abstractmethod
    async def ask_text(self, prompt: str, *, system: str | None = None) -> str | None:
        ...

    @abstractmethod
    async def ask_structured(self, prompt: str, shema: type[TModel], *, system: str | None = None) -> TModel | None:
        ...

    @abstractmethod
    async def ask_image(self, prompt: str, images: list[bytes], *, mime_type: str = "image/jpeg") -> str | None:
        ...