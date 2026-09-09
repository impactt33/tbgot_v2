from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.enums import PostType
from main.domain.services.post_template_service import (
    MAX_EXAMPLES,
    MIN_EXAMPLES,
    TEMPLATE_POST_TYPES,
)
from main.presentation.callbacks import (
    SetupChannelCB,
    TemplateAction,
    TemplateCB,
    TemplateRemoveExampleCB,
    TemplateTypesCB,
)


def template_types_keyboard(
    channel_id: int, counts: dict[PostType, int]
) -> InlineKeyboardMarkup:
    """Post types of one channel, marked by whether the template is usable.

    A full circle means the type has enough examples to generate with; an empty
    one means generation would be refused.
    """
    builder = InlineKeyboardBuilder()

    for post_type in TEMPLATE_POST_TYPES:
        count = counts.get(post_type, 0)
        mark = "•" if count >= MIN_EXAMPLES else "○"
        builder.button(
            text=f"{mark} {post_type.value} ({count}/{MAX_EXAMPLES})",
            callback_data=TemplateCB(
                action=TemplateAction.OPEN, channel_id=channel_id, post_type=post_type
            )
        )

    builder.button(text="Back", callback_data=SetupChannelCB(channel_id=channel_id))
    builder.adjust(1)
    return builder.as_markup()


def template_keyboard(
    channel_id: int,
    post_type: PostType,
    *,
    example_count: int,
    has_instruction: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if example_count < MAX_EXAMPLES:
        builder.button(
            text="Add example",
            callback_data=TemplateCB(
                action=TemplateAction.ADD_EXAMPLE, channel_id=channel_id, post_type=post_type
            )
        )

    if example_count:
        builder.button(
            text="Remove example",
            callback_data=TemplateCB(
                action=TemplateAction.LIST_EXAMPLES, channel_id=channel_id, post_type=post_type
            )
        )

    builder.button(
        text="Change instruction" if has_instruction else "Set instruction",
        callback_data=TemplateCB(
            action=TemplateAction.SET_INSTRUCTION, channel_id=channel_id, post_type=post_type
        )
    )

    if has_instruction:
        builder.button(
            text="Clear instruction",
            callback_data=TemplateCB(
                action=TemplateAction.CLEAR_INSTRUCTION,
                channel_id=channel_id,
                post_type=post_type
            )
        )

    builder.button(text="Back", callback_data=TemplateTypesCB(channel_id=channel_id))
    builder.adjust(1)
    return builder.as_markup()


def examples_keyboard(
    channel_id: int, post_type: PostType, lengths: list[int]
) -> InlineKeyboardMarkup:
    """One button per stored example, addressed by position.

    Button labels carry the length instead of a preview: the examples are full
    posts with HTML markup in them, and a truncated one tells the admin nothing
    that its number does not.
    """
    builder = InlineKeyboardBuilder()

    for index, length in enumerate(lengths):
        builder.button(
            text=f"Remove #{index + 1} ({length} chars)",
            callback_data=TemplateRemoveExampleCB(
                channel_id=channel_id, post_type=post_type, index=index
            )
        )

    builder.button(
        text="Back",
        callback_data=TemplateCB(
            action=TemplateAction.OPEN, channel_id=channel_id, post_type=post_type
        )
    )
    builder.adjust(1)
    return builder.as_markup()


def back_to_template_keyboard(channel_id: int, post_type: PostType) -> InlineKeyboardMarkup:
    """Escape hatch from the "send me an example" screen."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Back",
        callback_data=TemplateCB(
            action=TemplateAction.OPEN, channel_id=channel_id, post_type=post_type
        )
    )
    return builder.as_markup()


def skip_explanation_keyboard(channel_id: int, post_type: PostType) -> InlineKeyboardMarkup:
    """The only way out of "write an explanation" that is not writing one."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Skip",
        callback_data=TemplateCB(
            action=TemplateAction.SKIP_EXPLANATION,
            channel_id=channel_id,
            post_type=post_type
        )
    )
    return builder.as_markup()
