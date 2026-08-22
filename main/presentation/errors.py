from core.errors import AppError


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