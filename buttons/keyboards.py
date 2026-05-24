from __future__ import annotations

__all__ = ["Keyboard", "Keyboards"]

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Mapped

from buttons.buttons_schemes import *
from callback.payload_schemes import PayloadStart

Keyboard: dict[str, list[list[Button]]]


class Keyboards:

    @classmethod
    def change_list(
        cls,
        payload_uuid: UUID | Mapped[UUID],
    ) -> Keyboard:
        p = PayloadStart(type="list", uuid=payload_uuid, action="change")

        btn1 = CallbackButton.create("Название", p.add(inner=("field", "title")))
        btn2 = CallbackButton.create("Описание", p.add(inner=("field", "description")))
        btn3 = CallbackButton.create("Тип", p.add(inner=("field", "type")))
        btn4 = CallbackButton.create("Содержимое", p.add(inner=("values", "start")))
        btn5 = CallbackButton.create(
            "🗑Удалить", p.add(action="delete", inner="start", cancel_inner=True)
        )
        btn6 = CallbackButton.create("Вернуться⬆️", p.add(inner="escape"))

        keyboard = [[btn1, btn2], [btn3, btn4], [btn5, btn6]]

        return {"buttons": keyboard}

    @classmethod
    def reg(cls) -> Keyboard:
        btn1 = RequestContactButton.create("Отправить данные")

        keyboard = [[btn1]]

        return {"buttons": keyboard}

    @classmethod
    def yes_no(
        cls,
        type: str,
        action: str,
        payload_uuid: Optional[UUID] = None,
        inner: str | tuple[str] | None = None,
    ) -> Keyboard:
        p = PayloadStart(type=type, uuid=payload_uuid, action=action, inner=inner)

        btn1 = CallbackButton.create("✅Да", p.add(inner="yes"))
        btn2 = CallbackButton.create("❌Нет", p.add(inner="no"))

        keyboard = [[btn1, btn2]]

        return {"buttons": keyboard}

    @classmethod
    def change_list_values(cls, payload_uuid: UUID) -> Keyboard:
        p = PayloadStart(
            type="list", uuid=payload_uuid, action="change", inner="values"
        )

        btn1 = CallbackButton.create("➕Добавить", p.add(inner=("add", "get")))
        btn2 = CallbackButton.create("🗑Удалить", p.add(inner=("delete", "get")))
        btn3 = CallbackButton.create("✏️Изменить", p.add(inner=("change", "get_id")))
        btn4 = CallbackButton.create("Вернуться⬆️", p.add(inner="escape"))

        keyboard = [[btn1, btn2], [btn3, btn4]]

        return {"buttons": keyboard}

    @classmethod
    def change_list_value(
        cls, payload_uuid: UUID, value_id: int, came_from: str
    ) -> Keyboard:
        p = PayloadStart(type="list", uuid=payload_uuid, action="change", inner="value")

        btn1 = CallbackButton.create(
            "✏️Изменить", p.add(inner=("change", f"{value_id}"))
        )
        btn2 = CallbackButton.create("🗑Удалить", p.add(inner=("delete", f"{value_id}")))
        btn3 = CallbackButton.create("Вернуться⬆️", p.add(inner=("escape", came_from)))

        keyboard = [[btn1, btn2], [btn3]]

        return {"buttons": keyboard}

    @classmethod
    def lists(
        cls, page: int, lists_info: list[tuple[str, UUID], ...] | list, first: bool = True, final: bool = False, deleted: bool = False
    ) -> Keyboard:
        p = PayloadStart(type="lists", action="view")

        keyboard = []



        for index, info in enumerate(lists_info):
            btn_list = CallbackButton.create(f"{index + 1 + 10 * (page - 1)}. {info[0] if info[0] is not None else "Без названия"}", p.add(uuid=info[1], inner="list"))
            if not deleted:
                keyboard.append([btn_list])
            else:
                btn_list_get = CallbackButton.create("Достать🗑⬆️", p.add(type="list", action="change", uuid=info[1], inner=("deleted", "get")))
                keyboard.append([btn_list, btn_list_get])

        text1, inner1 = ("❌", "nothing") if first else ("⬅️Назад", "left")
        text2, inner2 = ("❌", "nothing") if final else ("Дальше➡️", "right")

        if not (first and final):
            btn1 = CallbackButton.create(text1, p.add(inner=inner1))
            btn2 = CallbackButton.create(text2, p.add(inner=inner2))

            keyboard.append([btn1, btn2])

        if deleted:
            delete_btn = CallbackButton.create("🧹Очистить корзину", p.add(inner="clear"))
            keyboard.append([delete_btn])

        escape_btn = CallbackButton.create("Вернуться⬆️", p.add(inner="escape"))
        keyboard.append([escape_btn])

        return {"buttons": keyboard}

    @classmethod
    def change_deleted_list(cls, payload_uuid: UUID) -> Keyboard:
        p = PayloadStart(type="list", uuid=payload_uuid, action="change")

        btn1 = CallbackButton.create("Достать из корзины🗑⬆️", p.add(inner=("deleted", "get")))
        btn2 = CallbackButton.create("Вернуться⬆️", p.add(inner="escape"))

        keyboard = [[btn1], [btn2]]

        return {"buttons": keyboard}

    @classmethod
    def help(cls):
        p = PayloadStart(type="help")

        btn1 = CallbackButton.create("➕Создать новый список", p.add(action="new_list"))
        btn2 = CallbackButton.create("👀Показать все списки", p.add(action="lists_view"))
        btn3 = CallbackButton.create("🗑Корзина", p.add(action="bin"))

        keyboard = [[btn1], [btn2], [btn3]]

        return {"buttons": keyboard}
