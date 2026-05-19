from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, DateTime

from uuid import UUID, uuid4

from .base import Base
from .mixins import UserRelationMixin

if TYPE_CHECKING:
    from .mylist_value import MyListValue


class MyList(Base, UserRelationMixin):
    uuid: Mapped[UUID] = mapped_column(nullable=False, unique=True, default=uuid4)
    title: Mapped[str | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    type: Mapped[str | None] = mapped_column(nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    values: Mapped[list[MyListValue]] = relationship(
        "MyListValue", back_populates="mylist"
    )

    def __str__(self):
        return f"MyList({self.uuid}, {self.title}, {self.description}, {self.type}, {self.create_time})"