from core.errors import AppError
from main.domain.services.material_reminder_service import MAX_INTERVAL_HOURS, MIN_INTERVAL_HOURS


class TimeInputError(AppError):
    """User entered time is invalid."""

    user_message = (
        "I didn't understand the time. Please write it in one of these formats:\n"
        "18:00 — today or tomorrow\n"
        "25.12 18:00 — day and month\n"
        "25.12.2026 18:00 — including the year"
    )

class TimeInPastError(TimeInputError):
    user_message = "This time is already past."

class PostInputError(AppError):
    """The admin sent something we cannot turn into a post."""

    user_message = "I can't use that as a post. Send text, or a photo with a caption."

class PostInputEmptyError(PostInputError):
    user_message = "That message is empty. Send some text, or a photo."

class PostInputUnsupportedError(PostInputError):
    user_message = (
        "I can only take plain text or a single photo for now. "
        "Videos, documents and stickers are not supported yet."
    )

    def __init__(self, content_type: str | None = None):
        self.content_type = content_type
        super().__init__(f"Unsupported content type for a custom post: {content_type!r}.")

class PostInputTooLongError(PostInputError):
    def __init__(self, length: int, limit: int, with_photo: bool):
        self.length = length
        self.limit = limit
        self.with_photo = with_photo

        where = "a photo caption" if with_photo else "a message"
        self.user_message = (
            f"That is {length} characters, and Telegram allows {limit} in {where}. "
            + (
                "Send the photo and the text as two separate posts, or shorten it."
                if with_photo
                else "Please shorten it."
            )
        )
        super().__init__(f"Custom post too long: {length} > {limit} (with_photo={with_photo}).")

class PostInputNoPhotoError(PostInputError):
    user_message = (
        "A material post needs at least one picture. Send the post together "
        "with its pictures."
    )

    def __init__(self) -> None:
        super().__init__("Material post arrived with no photos.")

class PostInputTooManyPhotosError(PostInputError):
    def __init__(self, length: int, limit: int):
        self.length = length
        self.limit = limit

        self.user_message = (
            f"There are too many photos ({length} from allowed {limit}) in your post."
        )
        super().__init__(f"Custom post has too many photos: {length} > {limit}.")

class ReminderInputError(AppError):
    """A reminder setting typed by hand could not be used."""

class ReminderIntervalInputError(ReminderInputError):
    user_message = (
        f"Send the interval as a whole number of hours, from {MIN_INTERVAL_HOURS} "
        f"to {MAX_INTERVAL_HOURS}. For example: 8"
    )

class WorkingHoursInputError(ReminderInputError):
    user_message = (
        "I didn't understand the hours. Send the start and the end, for example "
        "9-23 or 09:30-22:00."
    )

class WorkingHoursEmptyError(WorkingHoursInputError):
    user_message = (
        "The start and the end are the same time. For no limit at all, pick "
        "Around the clock instead."
    )