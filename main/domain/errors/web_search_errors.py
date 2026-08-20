from core.errors import AppError


class WebSearchError(AppError):
    """Base class for all web search errors."""

    user_message = "Web search is not available. Try again later."