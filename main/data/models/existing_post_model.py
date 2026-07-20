from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ExistingPost(Base):
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )
    post_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )