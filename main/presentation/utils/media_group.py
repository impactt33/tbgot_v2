"""Collecting an album that Telegram delivers as separate updates.

Telegram has no "album received" event: it sends one update per photo, tied
together only by `media_group_id`. There is no count either, so the only way to
know the album ended is that nothing else arrived for a moment.

The first update's handler becomes the one that waits and returns the whole
group; every later update just drops its message into the bucket and returns.
That keeps the waiting inside the handler that will go on to answer the user,
so no background task has to reach back into the Dispatcher.

In-memory on purpose: a group settles in about a second, and a restart in the
middle of one costs a re-send, not a lost post.
"""
import asyncio
import logging

from aiogram.types import Message

SETTLE_DELAY = 1.0

logger = logging.getLogger(__name__)

class MediaGroupCollector:
    """One per bot: must be APP-scoped, or each update gets its own bucket."""

    def __init__(self, settle_delay: float = SETTLE_DELAY):
        self._groups: dict[str, list[Message]] = {}
        self._settle_delay = settle_delay

    async def collect(self, message: Message) -> list[Message] | None:
        group_id = message.media_group_id

        if group_id is None:
            return [message]

        if group_id in self._groups:
            self._groups[group_id].append(message)
            return None

        self._groups[group_id] = [message]
        await asyncio.sleep(self._settle_delay)
        parts = self._groups.pop(group_id, [])

        parts.sort(key=lambda part: part.message_id)
        logger.debug("Album %s settled with %d parts", group_id, len(parts))

        return parts

