import asyncio
import logging

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramServerError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from main.domain.clients import MediaDownloader
from main.domain.errors import MediaDownloadError

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Retry only what a second attempt can fix.

    Bot.download is two calls, and they fail differently. getFile goes through
    aiogram's session and raises TelegramNetworkError; the download itself goes
    to api.telegram.org through aiohttp directly, with raise_for_status=True and
    no wrapping, so a broken stream surfaces as a plain aiohttp error.

    A wrong file_id gives TelegramBadRequest, and that is not retried: a fourth
    attempt at a file that does not exist is three wasted round trips.
    """
    return isinstance(exc, (
        TelegramNetworkError,
        TelegramServerError,
        aiohttp.ClientError,
        TimeoutError,
    ))


class TelegramMediaDownloader(MediaDownloader):
    def __init__(self, bot: Bot):
        self.bot = bot

    # noinspection PyTypeChecker
    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _download(self, file_id: str) -> bytes:
        # destination=None keeps the file in a BytesIO: nothing touches the disk.
        stream = await self.bot.download(file_id)

        if stream is None:
            # Only happens when a path destination was passed, which it never is.
            raise MediaDownloadError(file_id)

        return stream.read()

    async def download(self, file_id: str) -> bytes:
        try:
            return await self._download(file_id)
        except MediaDownloadError:
            raise
        except Exception as exc:
            logger.error("Downloading file %s failed: %s", file_id, exc)
            raise MediaDownloadError(file_id, exc) from exc

    async def download_many(self, file_ids: list[str]) -> list[bytes]:
        # return_exceptions=True so a single failure does not leave the other
        # downloads running unattended: gather propagates the first error at
        # once but does not cancel its siblings.
        results = await asyncio.gather(
            *(self.download(file_id) for file_id in file_ids),
            return_exceptions=True
        )

        for result in results:
            if isinstance(result, BaseException):
                raise result

        return [result for result in results if isinstance(result, bytes)]
