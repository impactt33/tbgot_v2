from pydantic import BaseModel, Field


class QuizPayload(BaseModel):
    question: str = Field(max_length=300)
    options: list[str] = Field(min_length=2, max_length=12)
    correct_index: int = Field(ge=0)
    explanation: str = Field(max_length=200)
    topic_id: int

class SourcePayload(BaseModel):
    title: str
    text: str
    url: str
    source_title: str
    source_id: int | None = None

class CustomPayload(BaseModel):
    """A post the admin wrote by hand: PostType.CUSTOM.

    `html_text` is already rendered — we keep the formatting the admin typed
    rather than the raw text plus entities, so publishing is a plain send with
    parse_mode=HTML.

    `photo_file_id` is Telegram's own handle for a photo already on its servers.
    Re-sending by file_id is what the Bot API recommends, so nothing has to be
    downloaded, stored or re-uploaded: the bot that received the photo can send
    it to any chat. The handle is tied to the bot's token — see the docstring on
    TelegramPublisher._publish_custom for what to do if the token ever changes.
    """

    html_text: str
    photo_file_ids: list[str] = Field(default_factory=list)