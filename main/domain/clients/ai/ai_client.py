from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from main.domain.enums.failures.ai_answer_failures import AIFailure

TModel = TypeVar("TModel", bound=BaseModel)

class AIClient(ABC):
    @abstractmethod
    async def ask_text(self, prompt: str, *, system: str | None = None) -> str | AIFailure:
        ...

    @abstractmethod
    async def ask_structured(self, prompt: str, schema: type[TModel], *, system: str | None = None) -> TModel | AIFailure:
        ...

    @abstractmethod
    async def ask_image(self, prompt: str, images: list[bytes], *, mime_type: str = "image/jpeg") -> str | AIFailure:
        ...