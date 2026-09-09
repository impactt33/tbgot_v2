"""One repair round for markup a model wrote.

Every generated post carries Telegram HTML now, and every model gets it wrong
sometimes. The recovery is the same wherever it happens - name the problems,
ask once for a fix, and if that fails keep the words and drop the markup - so
it lives here instead of being copied into each use case.

Sits next to ai_guard.py by design: that one turns a client failure into a
domain error, this one deals with a successful answer whose contents are wrong.
"""
import logging
from typing import TypeVar

from pydantic import BaseModel

from main.domain.clients import AIClient
from main.domain.use_cases.ai_guard import unwrap_ai
from main.domain.use_cases.html_guard import (
    ALLOWED_TAGS_HINT,
    check_link,
    check_telegram_html,
    fallback_plain,
)

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

_REPAIR_PROMPT = """Разметка в полях {fields} неверна:
{problems}

Вот твой прошлый ответ целиком:

{answer}

Верни его же — тот же смысл и та же манера — с исправленной разметкой.
Остальные поля не меняй.

Разрешены только теги {allowed_tags}. Символы < > & вне тегов пиши как
&lt; &gt; &amp;.{link_line}"""

_LINK_LINE = "\nСсылка в тексте обязательна, адрес ровно один: {url}"


def problems(text: str, required_link: str | None = None) -> list[str]:
    """Everything wrong with this piece of markup: tags first, link second."""
    found = check_telegram_html(text)

    if required_link is not None:
        found.extend(check_link(text, required_link))

    return found


def _draft_problems(
    draft: BaseModel, fields: tuple[str, ...], required_link: str | None
) -> list[str]:
    """Problems across every field carrying markup, each named by its field.

    The name is not decoration: with two markup fields a bare "<b> is never
    closed" leaves the model guessing which of them to fix.
    """
    found: list[str] = []

    for field in fields:
        found.extend(f"{field}: {problem}" for problem in problems(getattr(draft, field)))

    # The link is checked once against everything the post is made of: it has to
    # be somewhere, and which half does not matter.
    if required_link is not None:
        joined = "\n".join(getattr(draft, field) for field in fields)
        found.extend(check_link(joined, required_link))

    return found


async def ask_with_valid_markup(
    ai_client: AIClient,
    prompt: str,
    schema: type[TModel],
    *,
    fields: tuple[str, ...],
    system: str | None = None,
    images: list[bytes] | None = None,
    required_link: str | None = None,
) -> TModel:
    """Ask, and answer with a draft whose `fields` Telegram will accept.

    `fields` names the attributes holding markup, main body first; every other
    field of the schema is plain text and passes through untouched. The order
    matters only when `required_link` is set: that is the field the address is
    appended to if the fallback path had to strip the anchor away.

    Three outcomes, in order of preference: the first answer is already good;
    one repair round fixes it; or the markup goes and the words stay. The last
    one is deliberate - formatting is worth less than a post the admin can
    actually publish, and regenerating is one tap away.
    """
    draft = unwrap_ai(
        await ai_client.ask_structured(prompt, schema, system=system, images=images)
    )

    found = _draft_problems(draft, fields, required_link)

    if not found:
        return draft

    # One repair round, not a loop. A model that broke the markup twice will not
    # get it right on the fifth try, and every try costs. The problems travel
    # verbatim: a named mistake gets fixed, a re-roll gets re-rolled.
    logger.info("Model returned unusable markup in %s: %s", fields, found)

    repaired = unwrap_ai(
        await ai_client.ask_structured(
            _REPAIR_PROMPT.format(
                fields=", ".join(f"«{field}»" for field in fields),
                problems="\n".join(f"- {problem}" for problem in found),
                answer=draft.model_dump_json(indent=2),
                allowed_tags=ALLOWED_TAGS_HINT,
                link_line=(
                    "" if required_link is None
                    else _LINK_LINE.format(url=required_link)
                ),
            ),
            schema,
            system=system,
            # No images: this round fixes tags, not facts, and re-sending
            # pictures for that would double the cost of a mistake.
        )
    )

    if not _draft_problems(repaired, fields, required_link):
        return repaired

    logger.warning("Markup in %s still broken after a repair round, dropping it", fields)

    # Only the fields that are still wrong lose their markup: a model that broke
    # the explanation has no reason to cost the description its formatting.
    updates = {
        field: fallback_plain(getattr(repaired, field))
        for field in fields
        if problems(getattr(repaired, field))
    }

    if required_link is not None:
        # Stripping the markup takes the anchor with it, and the address lived
        # in the href. Without this the post would point nowhere.
        main = fields[0]
        body = updates.get(main, getattr(repaired, main))

        if required_link not in body:
            updates[main] = f"{body}\n\n{required_link}"

    return repaired.model_copy(update=updates)
