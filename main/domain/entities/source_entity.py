from datetime import datetime

from pydantic import BaseModel


class SourceEntity(BaseModel):
    id: int
    channel_id: int
    name: str | None
    url: str
    created_at: datetime
    used_in_post: int | None

class AddSourceEntity(BaseModel):
    channel_id: int
    name: str | None
    url: str