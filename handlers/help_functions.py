__all__ = ["mylist_values_to_form", "mylist_owners_to_form", "format_get_mylist_value_id_by_number"]

from typing import Optional
from uuid import UUID

from core.models import db_helper, MyListValue, MyListUserRole, User
from sqlalchemy.orm import Mapped

from crud import get_mylist_value_id_by_number


def mylist_values_to_form(
    mylist_values: list[MyListValue] | Mapped[list[MyListValue]],
):
    if len(mylist_values) == 0:
        values_text = f"    • <i>Пока что нет</i>\n"
    else:
        values_text = ""

        for i, value in enumerate(mylist_values):
            cod1, cod2 = "", ""
            # if value.made: не реализованно
            #     continue
            if value.made:
                cod1, cod2 = "<del>", "</del>"

            values_text += f"  /{i + 1}  {cod1} {value.value} {cod2}\n"

    return values_text


def mylist_owners_to_form(
        user_info: list[tuple], user_id: int, below_then: Optional[MyListUserRole] = None,
) -> tuple[str, MyListUserRole]:
    author_text = "<b>Автор:</b>\n"
    admins_text = "<b>Администраторы:</b>\n"
    users_text = "<b>Пользователи:</b>\n"

    author = ""
    admins = []
    users = []

    my_role = MyListUserRole

    for info in user_info:
        user: User = info[0]
        is_you = user.max_id == user_id
        if is_you:
            my_role = info[1]
        add_text = " <i>(Вы)</i>\n" if is_you else "\n"
        fio = f"{user.first_name}" + f" {user.last_name}" if user.last_name is not None else ""
        match info[1]:
            case MyListUserRole.AUTHOR:
                if below_then is not None:
                    continue
                author += f"\t- {fio}" + add_text
            case MyListUserRole.ADMIN:
                if below_then == MyListUserRole.ADMIN or below_then == MyListUserRole.USER:
                    continue
                admins.append(f"\t- {fio}" + add_text)
            case MyListUserRole.USER:
                if below_then == MyListUserRole.USER:
                    continue
                users.append(f"\t- {fio}" + add_text)

    final_text = author_text + author
    if admins:
        if below_then == MyListUserRole.AUTHOR or below_then is None:
            final_text += admins_text + "".join(admins)
    if users:
        final_text += users_text + "".join(users)

    return final_text, my_role



async def format_get_mylist_value_id_by_number(
    obj_uuid: UUID, text_id: str
) -> int | None:
    if not text_id.isdigit():
        return None

    index = int(text_id) - 1

    async with db_helper.session_factory() as session:
        return await get_mylist_value_id_by_number(session, obj_uuid, index)