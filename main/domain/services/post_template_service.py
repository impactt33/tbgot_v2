from abc import ABC, abstractmethod

from main.domain.entities import PostTemplateEntity
from main.domain.enums import PostType

# Below three examples the model copies the accidents of the two it was given
# instead of the channel's manner, so generation is refused outright. Above five
# the prompt grows without the output getting better.
MIN_EXAMPLES = 3
MAX_EXAMPLES = 5

# Free text from the channel owner, appended after the examples in the prompt.
MAX_INSTRUCTION_LENGTH = 1024

# CUSTOM is written by hand and never generated, so it has nothing to template.
TEMPLATE_POST_TYPES = (PostType.MATERIAL, PostType.QUIZ, PostType.SOURCES)


class PostTemplateService(ABC):
    @abstractmethod
    async def find(self, channel_id: int, post_type: PostType) -> PostTemplateEntity | None:
        ...

    @abstractmethod
    async def get_for_generation(
        self, channel_id: int, post_type: PostType
    ) -> PostTemplateEntity:
        """The template, only if it is usable for generating a post.

        Raises PostTemplateNotFoundError when nothing was ever set up, and
        NotEnoughExamplesError when there are fewer than MIN_EXAMPLES.
        """

    @abstractmethod
    async def list_by_channel(self, channel_id: int) -> list[PostTemplateEntity]:
        ...

    @abstractmethod
    async def add_example(
        self, channel_id: int, post_type: PostType, example: str
    ) -> PostTemplateEntity:
        """Raises TooManyExamplesError once MAX_EXAMPLES is reached."""

    @abstractmethod
    async def remove_example(
        self, channel_id: int, post_type: PostType, index: int
    ) -> PostTemplateEntity:
        """Raises ExampleNotFoundError for a stale button."""

    @abstractmethod
    async def set_instruction(
        self, channel_id: int, post_type: PostType, instruction: str | None
    ) -> PostTemplateEntity:
        """None clears it."""
