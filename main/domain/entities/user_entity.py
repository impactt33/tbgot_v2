from datetime import datetime

from pydantic import BaseModel

from main.data.enums import UserRole


class UserEntity(BaseModel):
    telegram_id: int
    username: str
    role: UserRole
    created_at: datetime
    updated_at: datetime