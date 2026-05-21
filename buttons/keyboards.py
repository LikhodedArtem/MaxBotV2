from __future__ import annotations

__all__ = ["Keyboard", "Keyboards"]

from uuid import UUID

from sqlalchemy.orm import Mapped

from buttons.buttons_schemes import *
from callback.payload_schemes import PayloadStart

Keyboard: dict[str, list[list[Button]]]


class Keyboards:

    @classmethod
    async def change_list(
        cls,
        obj_uuid: UUID | Mapped[UUID],
    ) -> Keyboard:
        p = PayloadStart(type="list", uuid=obj_uuid, action="change")

        btn1 = CallbackButton.create("Название", p.add(inner=["list", "title"]))
        btn2 = CallbackButton.create("Описание", p.add(inner=["list", "description"]))
        btn3 = CallbackButton.create("Тип", p.add(inner=["list", "type"]))
        btn4 = CallbackButton.create(
            "Содержимое", p.add(inner=["values", "start"])
        )
        btn5 = CallbackButton.create(
            "🗑Удалить", p.add(action="delete", inner="start", cancel_inner=True)
        )

        keyboard = [[btn1, btn2], [btn3, btn4], [btn5]]

        return {"buttons": keyboard}

    @classmethod
    async def reg(cls) -> Keyboard:
        btn1 = RequestContactButton.create("Отправить данные")

        keyboard = [[btn1]]

        return {"buttons": keyboard}

    @classmethod
    async def yes_no(
        cls,
        type: str,
        obj_uuid: UUID,
        action: str,
        inner: str | list[str] | None = None,
    ) -> Keyboard:
        p = PayloadStart(type=type, uuid=obj_uuid, action=action, inner=inner)

        btn1 = CallbackButton.create("✅Да", p.add(inner="yes"))
        btn2 = CallbackButton.create("❌Нет", p.add(inner="no"))

        keyboard = [[btn1, btn2]]

        return {"buttons": keyboard}

    @classmethod
    async def change_list_values(cls, obj_uuid: UUID) -> Keyboard:
        p = PayloadStart(type="list", uuid=obj_uuid, action="change", inner="values")

        btn1 = CallbackButton.create("➕Добавить", p.add(inner=["add", "get"]))
        btn2 = CallbackButton.create("🗑Удалить", p.add(inner=["delete", "get"]))
        btn3 = CallbackButton.create(
            "✏️Изменить", p.add(inner=["change", "get_id"])
        )
        btn4 = CallbackButton.create("➡️Вернуться", p.add(inner="escape"))

        keyboard = [[btn1, btn2], [btn3, btn4]]

        return {"buttons": keyboard}

    @classmethod
    async def change_list_value(
        cls, obj_uuid: UUID, value_id: int, came_from: str
    ) -> Keyboard:
        p = PayloadStart(type="list", uuid=obj_uuid, action="change", inner="value")

        btn1 = CallbackButton.create(
            "✏️Изменить", p.add(inner=["change", f"{value_id}"])
        )
        btn2 = CallbackButton.create(
            "🗑Удалить", p.add(inner=["delete", f"{value_id}"])
        )
        btn3 = CallbackButton.create(
            "➡️Вернуться", p.add(inner=["escape", came_from])
        )

        keyboard = [[btn1, btn2], [btn3]]

        return {"buttons": keyboard}
