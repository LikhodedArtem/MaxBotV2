from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import TIMESTAMP, false

from uuid import UUID, uuid4

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .mylist_value import MyListValue
    from .user_mylist_association import UserMyListAssociation


class MyList(Base):
    uuid: Mapped[UUID] = mapped_column(nullable=False, unique=True, default=uuid4)
    title: Mapped[str | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    type: Mapped[str | None] = mapped_column(nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, default=lambda: datetime.now(ZoneInfo("Europe/Moscow"))
    )
    deleted: Mapped[bool] = mapped_column(default=False, server_default=false(), nullable=False)
    delete_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=True
    )


    user_links: Mapped[list[UserMyListAssociation]] = relationship(
        back_populates="mylist",
        cascade="all, delete-orphan"
    )

    users: Mapped[list[User]] = relationship(
        secondary="user_mylist_association",
        back_populates="mylists",
        viewonly=True,
    )

    values: Mapped[list[MyListValue]] = relationship(
        "MyListValue", back_populates="mylist"
    )

    def __str__(self):
        return f"MyList({self.uuid}, {self.title}, {self.description}, {self.type}, {self.create_time})"
