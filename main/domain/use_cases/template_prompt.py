"""Turning a channel's template into prompt blocks, or into nothing at all.

Nothing is a supported outcome rather than a degraded one: QUIZ and SOURCES
worked before templates existed, and a channel that never filled one keeps
generating exactly as it did. MATERIAL is the exception - it is new, so there
it is a hard requirement and this module is not involved.
"""
from main.domain.entities import PostTemplateEntity
from main.domain.services.post_template_service import MIN_EXAMPLES

_EXAMPLES_BLOCK = """
Вот несколько постов этого канала. Воспроизведи их манеру: тон, длину,
структуру, оформление. Содержание из них не бери — это образцы формы, а не
источник фактов.

{examples}
"""

_INSTRUCTION_BLOCK = """
Отдельные требования владельца канала:
{instruction}
"""


def instruction_block(template: PostTemplateEntity | None) -> str:
    """The owner's instruction alone, for prompts examples make no sense in.

    Picking a quiz topic is one: the topics already used are listed there
    anyway, and whole posts would only cost tokens. An instruction like "темы
    про сетки и типографику" changes the choice from random to steered.
    """
    if template is None or not template.instruction:
        return ""

    return _INSTRUCTION_BLOCK.format(instruction=template.instruction)


def manner_block(template: PostTemplateEntity | None) -> str:
    """Examples and the instruction, for prompts that write the post itself.

    Examples need MIN_EXAMPLES to be worth showing: below that a model copies
    the accidents of the one or two it was handed rather than the manner. An
    instruction is useful on its own and goes in whenever it is set.
    """
    if template is None:
        return ""

    block = ""

    if len(template.examples) >= MIN_EXAMPLES:
        block += _EXAMPLES_BLOCK.format(examples="\n\n---\n\n".join(template.examples))

    return block + instruction_block(template)
