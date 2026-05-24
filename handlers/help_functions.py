__all__ = ["mylist_values_to_form", "format_get_mylist_value_id_by_number"]

from uuid import UUID

from core.models.db_helper import db_helper
from core.models.mylist_value import MyListValue
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


async def format_get_mylist_value_id_by_number(
    obj_uuid: UUID, text_id: str
) -> int | None:
    if not text_id.isdigit():
        return None

    index = int(text_id) - 1

    async with db_helper.session_factory() as session:
        return await get_mylist_value_id_by_number(session, obj_uuid, index)
