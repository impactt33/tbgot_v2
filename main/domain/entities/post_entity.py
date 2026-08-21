from datetime import datetime
from typing import Any

from pydantic import BaseModel

from main.domain.enums import PostType, PostStatus


class PostEntity(BaseModel):
    id: int
    channel_id: int
    post_type: PostType
    status: PostStatus
    payload: dict[str, Any]
    telegram_message_id: int | None
    created_at: datetime
    scheduled_at: datetime | None
    published_at: datetime | None

class PostCreateEntity(BaseModel):
    channel_id: int
    post_type: PostType
    payload: dict[str, Any]
