from abc import abstractmethod, ABC
from datetime import datetime
from typing import Any

from main.domain.entities import PostEntity, PostCreateEntity


class PostRepo(ABC):
    @abstractmethod
    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        ...

    @abstractmethod
    async def find_by_id(self, post_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def find_scheduled(
        self, channel_id: int | None = None, limit: int = 20
    ) -> list[PostEntity]:
        """Scheduled posts, not changing status."""

    @abstractmethod
    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def mark_failed(self, post_id: int) -> PostEntity | None:
        ...

    @abstractmethod
    async def claim_scheduled(self, limit: int = 10) -> list[PostEntity]:
        ...

    @abstractmethod
    async def claim_for_publishing(self, post_id: int) -> PostEntity | None:
        """DRAFT/SCHEDULED -> PUBLISHING in one statement.

        None, if there was nothing to claim: someone published it already, or
        the scheduler took it a moment ago.
        """

    @abstractmethod
    async def schedule(self, post_id: int, when: datetime) -> PostEntity | None:
        """None, if post not in DRAFT/SCHEDULED."""

    @abstractmethod
    async def unschedule(self, post_id: int) -> PostEntity | None:
        """None, if post already not in SCHEDULED, it was claimed by scheduler."""

    @abstractmethod
    async def delete_draft(self, post_id: int) -> PostEntity | None:
        """None, if post not in DRAFT/SCHEDULED. Published do not delete."""

    @abstractmethod
    async def update_draft_payload(
        self, post_id: int, payload: dict[str, Any]
    ) -> PostEntity | None:
        """Replace the payload of a post that is still a draft.

        DRAFT only, unlike delete_draft, which also takes SCHEDULED: rewriting
        a post the scheduler is already counting on is a different decision
        from throwing it away, and nothing in the interface asks for it.

        None, if there was nothing to update.
        """