from core.errors import AppError


class MediaError(AppError):
    """Base class for errors around media files we pull from Telegram."""

class MediaDownloadError(MediaError):
    user_message = "Couldn't read the pictures from that post. Send it again."

    def __init__(self, file_id: str | None = None, exc: Exception | None = None):
        self.file_id = file_id
        self.exc = exc

        super().__init__(f"Downloading file (file_id: {file_id!r}) failed. Traceback: {exc!r}")
