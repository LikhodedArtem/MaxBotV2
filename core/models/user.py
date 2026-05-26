from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .base import Base

if TYPE_CHECKING:
    from .user_mylist_association import UserMyListAssociation
    from .mylist import MyList


class User(Base):
    max_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, unique=False, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    is_bot: Mapped[bool] = mapped_column(String, nullable=False)
    last_activity_time: Mapped[int] = mapped_column(String, nullable=False)

    mylist_links: Mapped[list[UserMyListAssociation]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    mylists: Mapped[list[MyList]] = relationship(
        secondary="user_mylist_association",
        back_populates="users",
        viewonly=True,
    )

    async def get_list_count(self) -> int:
        return len(self.mylists)
