from datetime import datetime

from pydantic import BaseModel
from typing import NamedTuple

from main.domain.enums import UserRole

class UserEntity(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    role: UserRole
    created_at: datetime
    updated_at: datetime


class NewUserEntity(NamedTuple):
    user: UserEntity
    was_created: bool

class UserCreateEntity(BaseModel):
    telegram_id: int
    username: str | None