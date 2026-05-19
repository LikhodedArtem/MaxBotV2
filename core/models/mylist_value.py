from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

import uuid

from .base import Base

if TYPE_CHECKING:
    from .mylist import MyList


class MyListValue(Base):
    value: Mapped[str] = mapped_column(nullable=False)
    made: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="False"
    )

    mylist_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mylists.uuid"), nullable=False
    )
    mylist: Mapped[MyList] = relationship("MyList", back_populates="values")

    def __str__(self):
        return f"|{"U" if self.made else "X"}| {self.value}"