import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import PostTemplate
from main.domain.entities import PostTemplateEntity
from main.domain.enums import PostType
from main.domain.repositories.post_template_repo import PostTemplateRepo

_CONSTRAINT = "uq_post_templates_channel_id_post_type"


class PostTemplateRepoImpl(PostTemplateRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(self, channel_id: int, post_type: PostType) -> PostTemplateEntity | None:
        template: PostTemplate | None = await self.session.scalar(
            select(PostTemplate)
            .where(
                PostTemplate.channel_id == channel_id,
                PostTemplate.post_type == post_type
            )
        )

        return template.to_entity() if template is not None else None

    async def list_by_channel(self, channel_id: int) -> list[PostTemplateEntity]:
        templates = await self.session.scalars(
            select(PostTemplate)
            .where(PostTemplate.channel_id == channel_id)
            .order_by(PostTemplate.post_type)
        )

        return [template.to_entity() for template in templates]

    async def add_example(
        self, channel_id: int, post_type: PostType, example: str, *, max_examples: int
    ) -> PostTemplateEntity | None:
        # One statement covers both cases: the row is created with a one-element
        # array, or the array already there gets that same one appended. The
        # value is written once and reused through `excluded`, which is the row
        # Postgres was about to insert.
        #
        # The cap rides on DO UPDATE's WHERE. Over the limit the row is left
        # alone, RETURNING gives nothing back, and the caller reads that as a
        # refusal. The INSERT branch needs no check: a fresh array holds one.
        statement = insert(PostTemplate).values(
            channel_id=channel_id,
            post_type=post_type,
            examples=sa.func.jsonb_build_array(example),
        )
        added: PostTemplate | None = await self.session.scalar(
            statement
            .on_conflict_do_update(
                constraint=_CONSTRAINT,
                set_={
                    "examples": PostTemplate.examples + statement.excluded.examples,
                    "updated_at": sa.func.now(),
                },
                where=sa.func.jsonb_array_length(PostTemplate.examples) < max_examples,
            )
            .returning(PostTemplate)
        )
        await self.session.commit()
        return added.to_entity() if added is not None else None

    async def remove_example(
        self, channel_id: int, post_type: PostType, index: int
    ) -> PostTemplateEntity | None:
        # `jsonb - integer` drops an array element by position. The bind needs an
        # explicit Integer type: left to itself SQLAlchemy casts it to JSONB to
        # match the column, and `jsonb - jsonb` is not an operator Postgres has.
        position = sa.bindparam("index", index, type_=sa.Integer)

        template: PostTemplate | None = await self.session.scalar(
            sa.update(PostTemplate)
            .where(
                PostTemplate.channel_id == channel_id,
                PostTemplate.post_type == post_type,
                # Postgres counts negative positions from the end, so -1 would
                # quietly delete the last example instead of missing.
                position >= 0,
                sa.func.jsonb_array_length(PostTemplate.examples) > position,
            )
            .values(examples=PostTemplate.examples - position, updated_at=sa.func.now())
            .returning(PostTemplate)
        )
        await self.session.commit()
        return template.to_entity() if template is not None else None

    async def set_instruction(
        self, channel_id: int, post_type: PostType, instruction: str | None
    ) -> PostTemplateEntity | None:
        template: PostTemplate | None = await self.session.scalar(
            insert(PostTemplate)
            .values(
                channel_id=channel_id,
                post_type=post_type,
                instruction=instruction,
            )
            .on_conflict_do_update(
                constraint=_CONSTRAINT,
                set_={"instruction": instruction, "updated_at": sa.func.now()},
            )
            .returning(PostTemplate)
        )
        await self.session.commit()
        return template.to_entity() if template is not None else None
