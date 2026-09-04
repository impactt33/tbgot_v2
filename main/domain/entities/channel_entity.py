from datetime import datetime

from pydantic import BaseModel


class ChannelEntity(BaseModel):
    channel_id: int
    username: str | None
    title: str | None
    added_at: datetime
    storage_channel_id: int | None = None

class ChannelAddEntity(BaseModel):
    channel_id: int
    username: str | None
    title: str | None