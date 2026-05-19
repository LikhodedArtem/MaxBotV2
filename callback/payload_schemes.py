from __future__ import annotations

__all__ = [""]

from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator

class PayloadMixin(BaseModel):
    uuid: Optional[UUID] = None
    inner: Inner = Field(default_factory=lambda: Inner(value=None))

    @field_validator("inner", mode="before")
    @classmethod
    def check_inner(cls, v: str | list | None) -> Inner:
        if isinstance(v, Inner):
            return v
        return Inner(value=v)


class Payload(PayloadMixin):
    """Для хранения информации о действии CallbackButton или Status

    Attributes:
        type: тип обрабатываемого объекта
        action: действие над этим объектом
        uuid: uuid обрабатываемого объекта
        inner: дополнительная информация о совершаемом действии

    """

    type: str
    action: str

    def __eq__(self, other: Payload) -> bool:
        if isinstance(other, Payload):
            return (
                self.type == other.type
                and self.action == other.action
                and self.uuid == other.uuid
                and self.inner == other.inner
            )
        raise NotImplemented


class PayloadStart(PayloadMixin):
    """Позволяет изначально формировать лишь часть информации Payload перед полным завершением через add

    Attributes:
        type: тип обрабатываемого объекта
        action: действие над этим объектом
        uuid: uuid обрабатываемого объекта
        inner: дополнительная информация о совершаемом действии

    """

    type: str
    action: Optional[str] = None

    async def add(
        self,
        type: Optional[str] = None,
        action: Optional[str] = None,
        uuid: Optional[UUID] = None,
        inner: str | list | None = None,
        cancel_inner: bool = False,
    ) -> str:
        """Закончить формирование информации в полноценный Payload

        Args:
            type: тип обрабатываемого объекта
            action: действие над объектом
            uuid: uuid обрабатываемого объекта
            inner: дополнительная информация о совершаемом действии
            cancel_inner: Убрать из учёта inner, указанный при старте

        """

        inner = Inner(value=inner)

        try:
            data = Payload(
                type=type if type is not None else self.type,
                uuid=uuid if uuid is not None else self.uuid,
                action=action if action is not None else self.action,
                inner=self.inner + inner if not cancel_inner else inner,
            )
        except:
            raise ValueError("Пропущен один из пунктов при сборке PayloadStart")

        from .payload_functions import convert_payload

        return await convert_payload(data)


class PayloadCheck(PayloadMixin):
    type: Optional[str] = None
    action: Optional[str] = None
    freeze_inner: bool = False


class Inner(BaseModel):
    """Хранение дополнительная информация о совершаемом действии Payload

    Attributes:
        value: на входе принимает str | list[str] | None, итого хранит list[str]

    """

    value: list[str]

    @classmethod
    def value_to_list(сls, value: str | list[str] | None) -> list[str]:
        """Преобразует str | list[str] | None в list"""

        if isinstance(value, str):
            return [value]
        if value is None:
            return []
        return value

    @field_validator("value", mode="before")
    @classmethod
    def prepare_value(cls, v: str | list[str] | None) -> list[str]:
        """value на входе может быть str | list[str] | None, но хранится в виде list[str]"""

        return cls.value_to_list(v)

    def __add__(self, other) -> Inner:
        """Inner + Inner = list"""

        if isinstance(other, Inner):
            l1 = self.value_to_list(self.value)
            l2 = other.value_to_list(other.value)
            return Inner(value=l1 + l2)
