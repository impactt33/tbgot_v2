from abc import ABC, abstractmethod


class MediaDownloader(ABC):
    """Pulling the bytes of a Telegram file into memory.

    Needed because a model cannot be handed a file_id: Gemini takes either
    inline bytes or a URI it can fetch itself, and Telegram's download URL
    carries the bot token in the path, so it is not a link to hand out.
    """

    @abstractmethod
    async def download(self, file_id: str) -> bytes:
        """Raises MediaDownloadError."""

    @abstractmethod
    async def download_many(self, file_ids: list[str]) -> list[bytes]:
        """Same order as the ids came in.

        Raises MediaDownloadError if any one of them fails: a post assembled
        from half its pictures is worse than an honest refusal.
        """
