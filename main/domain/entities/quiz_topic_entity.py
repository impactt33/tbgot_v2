from datetime import datetime

from pydantic import BaseModel


class QuizTopicEntity(BaseModel):
    id: int
    channel_id: int
    topic: str
    created_at: datetime
    used_in_post: int | None

class QuizTopicAddEntity(BaseModel):
    channel_id: int
    topic: str