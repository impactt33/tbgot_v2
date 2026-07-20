from pydantic import BaseModel


class UserCreateEntity(BaseModel):
    telegram_id: int
    username: str