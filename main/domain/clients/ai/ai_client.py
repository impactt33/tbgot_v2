from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class AIClient(ABC, Generic[T]):
    @staticmethod
    @abstractmethod
    async def process_to_history(history: list[str]) -> T:
        ...

    @abstractmethod
    async def ask_text(self, user_message: str, json_mode: bool = False) -> str:
        ...

    @abstractmethod
    async def ask_image(self, user_message: str, images_bytes: list[bytes], json_mode: bool = False) -> str:
        ...