from __future__ import annotations

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .mylist import MyList


class MyListUserRole(PyEnum):
    AUTHOR = "author"
    USER = "user"


class UserMyListAssociation(Base):
    __tablename__ = "user_mylist_association"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    mylist_id: Mapped[int] = mapped_column(ForeignKey("mylists.id"), nullable=False)
    role: Mapped[MyListUserRole] = mapped_column(
        Enum(MyListUserRole, name="mylist_user_role"),
        nullable=False,
        default=MyListUserRole.USER,
    )

    user: Mapped[User] = relationship(back_populates="mylist_links")
    mylist: Mapped[MyList] = relationship(back_populates="user_links")

    __table_args__ = (
        UniqueConstraint("user_id", "mylist_id", name="idx_unique_user_mylist"),
    )