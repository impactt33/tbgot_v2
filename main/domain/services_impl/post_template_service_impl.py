from main.domain.entities import PostTemplateEntity
from main.domain.enums import PostType
from main.domain.errors import (
    ExampleNotFoundError,
    NotEnoughExamplesError,
    PostTemplateNotFoundError,
    TooManyExamplesError,
)
from main.domain.repositories import PostTemplateRepo
from main.domain.services import PostTemplateService
from main.domain.services.post_template_service import MAX_EXAMPLES, MIN_EXAMPLES


class PostTemplateServiceImpl(PostTemplateService):
    def __init__(self, post_template_repo: PostTemplateRepo):
        self.post_template_repo = post_template_repo

    async def find(self, channel_id: int, post_type: PostType) -> PostTemplateEntity | None:
        return await self.post_template_repo.find(channel_id, post_type)

    async def get_for_generation(
        self, channel_id: int, post_type: PostType
    ) -> PostTemplateEntity:
        template = await self.post_template_repo.find(channel_id, post_type)

        if template is None:
            raise PostTemplateNotFoundError(channel_id, post_type)

        if len(template.examples) < MIN_EXAMPLES:
            raise NotEnoughExamplesError(len(template.examples), MIN_EXAMPLES)

        return template

    async def list_by_channel(self, channel_id: int) -> list[PostTemplateEntity]:
        return await self.post_template_repo.list_by_channel(channel_id)

    async def add_example(
        self, channel_id: int, post_type: PostType, example: str
    ) -> PostTemplateEntity:
        template = await self.post_template_repo.add_example(
            channel_id, post_type, example, max_examples=MAX_EXAMPLES
        )

        # None means the statement's own cap check refused the write: the array
        # was already at MAX_EXAMPLES.
        if template is None:
            raise TooManyExamplesError(MAX_EXAMPLES)

        return template

    async def remove_example(
        self, channel_id: int, post_type: PostType, index: int
    ) -> PostTemplateEntity:
        template = await self.post_template_repo.remove_example(channel_id, post_type, index)

        if template is None:
            raise ExampleNotFoundError(index)

        return template

    async def set_instruction(
        self, channel_id: int, post_type: PostType, instruction: str | None
    ) -> PostTemplateEntity:
        template = await self.post_template_repo.set_instruction(
            channel_id, post_type, instruction
        )

        # The upsert returns a row in both branches, so None can only mean the
        # statement no longer matches the constraint it conflicts on.
        if template is None:
            raise PostTemplateNotFoundError(channel_id, post_type)

        return template
