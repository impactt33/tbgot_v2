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

def material_url(storage_username: str, storage_message_id: int) -> str:
    """The link to our copy of a material.

    A function and not only a property because the address is needed before
    there is a payload to ask: the model is given it to place inside the text
    itself, and that happens before the text exists.
    """
    return f"https://t.me/{storage_username}/{storage_message_id}"


class MaterialPayload(BaseModel):
    """A post pointing at a file we keep in our own storage channel.

    The published post is a bold title and the description, and the link lives
    inside the description - the model writes it there, styled the way the
    channel styles links. Everything needed to render the post is frozen here
    at draft time, and publishing resolves nothing.

    `storage_username` is what makes the link openable. A private channel's
    link is t.me/c/<shifted_id>/<message_id> and only opens for members, so a
    subscriber tapping it would get nothing — the storage channel has to be
    public, and binding one without a username is refused.

    `title` is plain text and gets escaped and bolded at publish time.
    `description` is Telegram HTML the model wrote, already checked against the
    tag list Telegram accepts, and checked to link at this material and nothing
    else - see html_guard. Keeping the title apart means a model that mangles
    its markup can only spoil the body of the post, never its first line.
    """

    title: str
    description: str
    storage_chat_id: int
    storage_message_id: int
    storage_username: str
    photo_file_ids: list[str] = Field(default_factory=list)
    material_id: int | None = None

    @property
    def url(self) -> str:
        return material_url(self.storage_username, self.storage_message_id)