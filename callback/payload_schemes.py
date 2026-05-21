from __future__ import annotations

__all__ = ["Payload", "PayloadStart", "PayloadCheck", "Inner"]

from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator

"""
Построение payload:

    Предполагаемый вид:
        "t=...&u=...&a=...&i1..."

    & - разделитель
    t=... - type, определять тип объекта
    a=... - action, основной способ как сортировать payload
    u=... - uuid, находить нужный объект
    i1=... - inner1 (может быть 2, 3 ...), подгруппа action,
    позволяет делать делать более удобное распределение payload

"""


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

    def add(
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

        return convert_payload(data)


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

        if isinstance(v, str):
            return [v.lower()]
        if v is None:
            return []
        return list(map(lambda x: x.lower(), v))

    def __add__(self, other) -> Inner:
        """Inner + Inner = list"""

        if isinstance(other, Inner):
            return Inner(value=self.value + other.value)

        raise ValueError("Inner не может быть сложен ни с чем кроме Inner")

    def __eq__(self, other: Inner) -> bool:
        if isinstance(other, Inner):
            return self.value == other.value
        raise NotImplemented

    def __contains__(self, other: Any) -> bool:
        return other in self.value

    def __iter__(self):
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)
