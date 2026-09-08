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
    async def ask_structured(
        self,
        prompt: str,
        schema: type[TModel],
        *,
        system: str | None = None,
        images: list[bytes] | None = None,
        mime_type: str = "image/jpeg",
    ) -> TModel | AIFailure:
        """Ask for an answer shaped like `schema`, optionally showing images.

        Images are keyword-only on purpose: they are the rare case, and a bare
        list appearing third in a call would read like part of the prompt.

        `mime_type` applies to the whole list rather than to each image.
        Telegram photos are always JPEG, so there is nothing to mix; the day
        there is, this becomes a list.
        """