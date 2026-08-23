from core.errors import AppError


class SourceError(AppError):
    """Base class for all errors related to sources."""

class SourceNotFoundError(SourceError):
    user_message = "Source not found."

    def __init__(self, source_id: int | None = None) -> None:
        self.source_id = source_id
        super().__init__(f"Source (source_id: {source_id!r}) was not found.")

class NoSourceFoundError(SourceError):
    user_message = "Не нашёл ни одного нового ресурса. Попробуй ещё раз."

    def __init__(self, channel_id: int | None = None) -> None:
        self.channel_id = channel_id
        super().__init__(f"No fresh source found for channel {channel_id!r}.")

class InvalidSourceDraftError(SourceError):
    user_message = "Пост получился некорректным. Попробуй ещё раз."

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or "Source draft is invalid.")