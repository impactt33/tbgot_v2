from abc import ABC, abstractmethod

from main.domain.entities import PostTemplateEntity
from main.domain.enums import PostType


class PostTemplateRepo(ABC):
    @abstractmethod
    async def find(self, channel_id: int, post_type: PostType) -> PostTemplateEntity | None:
        ...

    @abstractmethod
    async def list_by_channel(self, channel_id: int) -> list[PostTemplateEntity]:
        """Every template of the channel, for the "which types are ready" screen."""

    @abstractmethod
    async def add_example(
        self, channel_id: int, post_type: PostType, example: str, *, max_examples: int
    ) -> PostTemplateEntity | None:
        """Append one example, creating the template row if there is none.

        `max_examples` is enforced inside the statement rather than by reading
        first: the cap is a domain rule, but checking it here keeps the whole
        thing one round trip and immune to two admins pressing at once.

        None means the cap was already reached and nothing was written.
        """

    @abstractmethod
    async def remove_example(
        self, channel_id: int, post_type: PostType, index: int
    ) -> PostTemplateEntity | None:
        """None if there is no such template, or no example at that position."""

    @abstractmethod
    async def set_instruction(
        self, channel_id: int, post_type: PostType, instruction: str | None
    ) -> PostTemplateEntity | None:
        """Upsert: the row appears if the instruction is the first thing set.

        DO UPDATE carries no condition, so a row always comes back - None would
        mean the statement stopped matching the constraint it names.
        """
