from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .base import Base

if TYPE_CHECKING:
    from .mylist import MyList


class User(Base):
    max_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    first_name: Mapped[str]
    last_name: Mapped[Optional[str]]
    username: Mapped[Optional[str]]
    name: Mapped[Optional[str]]

    is_bot: Mapped[bool]
    last_activity_time: Mapped[int]

    mylists: Mapped[list[MyList]] = relationship(back_populates="user")

    async def get_list_count(self) -> int:
        return len(self.mylists)