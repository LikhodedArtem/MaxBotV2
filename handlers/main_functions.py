from typing import Optional
from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.global_names import GN
from core.models.db_helper import db_helper
from handlers.checkers import list_checker
from crud import (
    create_mylist,
    get_mylist_with_values_by_uuid,
    create_user,
    get_user_by_max_id,
    update_mylist_field,
    delete_mylist_with_values_by_uuid,
    create_mylist_value,
    delete_mylist_value_by_id,
    update_mylist_value_value_by_id,
    update_made_of_mylist_value,
    get_mylist_value_id_by_number,
)

from messages.message_schemes import Message, ContactMessage, Sender
from status.status_functions import create_status
from handlers.help_functions import *


@broker.check([Event.BOT_STARTED, Event.MESSAGE_COMMAND("reg")])
async def reg_get(sender: Sender):
    async with db_helper.session_factory() as session:
        if await get_user_by_max_id(session, sender.user_id) is None:
            await sender.answer(
                "📞Для продолжения работы, необходим ваш номер телефона",
                "inline_keyboard",
                payload=Keyboards.reg(),
            )

            status = create_status(type="bot", action="reg")
            await sender.status(status)
        else:
            await sender.answer(GN.help_text)


@broker.check(Event.STATUS_CALLBACK(payload={"type": "bot", "action": "reg"}))
async def reg_set(message: ContactMessage):
    if not isinstance(message, ContactMessage):
        return

    try:
        async with db_helper.session_factory() as session:
            user = await get_user_by_max_id(session, message.sender.user_id)
            if user is None:
                user_data = message.sender.model_dump()
                user_data["chat_id"] = message.recipient.chat_id

                await create_user(session, user_data)

                await message.answer("✅Вы успешно зарегистрировались!")
            else:
                await message.answer("✅Вы уже были зарегистрированы!")

        await message.clear_status()

        try:
            message: Message
            await help(message=message)
        except Exception as e:
            raise ValueError(e)

    except Exception as e:
        print(e)
        await message.answer(
            "❌Что-то пошло не так. Попробуйте заново пройти регистрацию или напишите в техподдержку"
        )
        await message.clear_status()


@broker.check(Event.MESSAGE_COMMAND("help"))
async def help(message: Message) -> None:
    await message.answer(GN.help_text)


@broker.check(Event.MESSAGE_COMMAND("new_list"))
async def new_list(message: Message) -> None:
    user_id = message.sender.user_id

    async with db_helper.session_factory() as session:
        mylist = await create_mylist(session, user_id)

    await view_list(message, mylist.uuid)


async def view_list(message: Message, payload_uuid: UUID, edit: bool = False, is_from_lists: bool = False, page: Optional[int] = None) -> None:
    if is_from_lists and page is None or page is not None and not is_from_lists:
        raise ValueError("Было передан или только page или только is_from_lists. Должно быть передано либо ничего из этого, либо оба сразу")

    status = create_status(
        type="list", action="view", uuid=payload_uuid, send_callback=False, inner=("from_lists", f"{page}") if is_from_lists else None
    )
    await message.status(status)

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_by_uuid(session, payload_uuid)

    if mylist is None:
        await message.answer(
            "❌Невозможно отобразить список! Он был безвозвратно удалён."
        )
        return

    mylist_type = "Не указан" if mylist.type is None else mylist.type
    mylist_title = "Отсутствует" if mylist.title is None else mylist.title
    mylist_description = (
        "Отсутствует" if mylist.description is None else mylist.description
    )

    mylist_values = mylist_values_to_form(mylist.values)

    text = (
        f"⚙️Настройки вашего списка:\n\n"
        f"<b>Тип</b>: {mylist_type}\n"
        f"<b>Название</b>: {mylist_title}\n"
        f"<b>Описание</b>: {mylist_description}\n\n"
        f"<b>Содержание</b>:\n{mylist_values}\n"
        f"<b>Дата создания</b>: {mylist.create_time}\n\n"
    )

    if not edit:
        await message.answer(
            text, "inline_keyboard", payload=Keyboards.change_list(mylist.uuid)
        )
    else:
        await message.edit(
            text, "inline_keyboard", payload=Keyboards.change_list(mylist.uuid)
        )


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": "field"}
    ),
    checkers=list_checker,
    allowed=GN.list_view,
)
async def list_field_get(
    message: Message, payload_uuid: UUID, payload_inner: tuple[str]
) -> None:
    field = payload_inner[-1]

    text = f"✏️Напишите нов{"ый" if field == "type" else "ое"} <b>{GN.get(field).capitalize()}</b>\n"

    status = create_status(
        type="list", uuid=payload_uuid, action="set", inner=("field", field)
    )
    print("===request_list_field", message)

    await message.status(status)

    await message.answer(text)


@broker.check(
    Event.STATUS_CALLBACK(payload={"type": "list", "action": "set", "inner": "field"})
)
async def list_field_set(
    message: Message, payload_uuid: UUID, payload_inner: tuple[str]
) -> None:
    field = payload_inner[-1]

    ru_field = GN.get(field)

    text = (
        f"Новое {ru_field} сохранено✅"
        if field != "type"
        else f"Новый {ru_field} сохранён✅"
    )

    async with db_helper.session_factory() as session:
        await update_mylist_field(session, payload_uuid, field, message.body.text)

    await message.answer(text)
    await message.clear_status()

    await view_list(message, payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "delete", "inner": "start"}
    ),
    checkers=list_checker,
    allowed=GN.list_view,
)
async def first_delete(message: Message, payload_uuid: UUID) -> None:
    await message.answer(
        "Вы уверены, что хотите <b>удалить</b> список?",
        "inline_keyboard",
        payload=Keyboards.yes_no(
            type="list", action="delete", payload_uuid=payload_uuid, inner="first"
        ),
    )

    await message.status(name="List-Delete")


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "delete", "inner": ("first", "yes")}
    ),
    allowed="List-Delete",
    checkers=list_checker,
)
async def second_delete(message: Message, payload_uuid: UUID) -> None:
    await message.edit(
        "Вы <b>точно</b> уверены, что хотите <b>удалить</b> список?",
        "inline_keyboard",
        payload=Keyboards.yes_no(
            type="list", action="delete", payload_uuid=payload_uuid, inner="second"
        ),
    )


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "delete", "inner": ("second", "yes")}
    ),
    allowed="List-Delete",
    checkers=list_checker,
)
async def final_delete(message: Message, payload_uuid: UUID) -> None:
    await message.delete()

    async with db_helper.session_factory() as session:
        await delete_mylist_with_values_by_uuid(session, payload_uuid)

    await message.answer("✅Список безвозвратно удалён")

    await message.clear_status()

    await help(message=message)


@broker.check(
    [
        Event.MESSAGE_CALLBACK(
            payload={"type": "list", "action": "delete", "inner": ("first", "no")}
        ),
        Event.MESSAGE_CALLBACK(
            payload={"type": "list", "action": "delete", "inner": ("second", "no")}
        ),
    ],
    "List-Delete",
    checkers=list_checker,
)
async def cancel_delete(message: Message) -> None:
    await message.delete()
    await message.clear_status()


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": "escape"}
    ),
    allowed=GN.list_view,
    can_be_none=True
)
async def list_view_escape(message: Message, status_inner: tuple[str] | None) -> None:
    await message.clear_status()

    if status_inner is not None and len(status_inner) > 0 and status_inner[0] == "from_lists":
        page = int(status_inner[-1])

        from .view_lists import view_lists
        await view_lists(message=message, page=page)
    else:
        await help(message=message)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "start")}
    ),
    checkers=list_checker,
    allowed=GN.list_view,
)
async def view_values(message: Message, payload_uuid: UUID) -> None:
    status = create_status(
        type="list",
        uuid=payload_uuid,
        action="view",
        inner="values",
        send_callback=False,
    )
    await message.status(status, send_callback=False)

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_by_uuid(session, payload_uuid)
        values = mylist.values

    print("===values", values)

    name = f' "{mylist.title}"' if mylist.title is not None else ""

    text = f"📋<b>Содержание</b> списка{name}:\n" f"{mylist_values_to_form(values)}"

    await message.answer(
        text, "inline_keyboard", payload=Keyboards.change_list_values(payload_uuid)
    )


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "add", "get")}
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def add_value_get(message: Message, payload_uuid: UUID) -> None:
    await message.answer("✏️Напишите новый <b>пункт</b> списка")

    status = create_status(
        type="list", uuid=payload_uuid, action="change", inner=("values", "add", "set")
    )
    await message.status(status)


@broker.check(
    Event.STATUS_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "add", "set")}
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def add_value_set(message: Message, payload_uuid: UUID) -> None:
    async with db_helper.session_factory() as session:
        await create_mylist_value(session, payload_uuid, message.body.text)

        await message.answer("✅Новый пункт создан")

        await message.clear_status()

        await view_values(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={
            "type": "list",
            "action": "change",
            "inner": ("values", "delete", "get"),
        }
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def delete_value_get(message: Message, payload_uuid: UUID) -> None:
    await message.answer("🗑Напишите <b>номер пункта</b> для удаления")

    status = create_status(
        type="list",
        uuid=payload_uuid,
        action="change",
        inner=("values", "delete", "set"),
    )
    await message.status(status)


@broker.check(
    Event.STATUS_CALLBACK(
        payload={
            "type": "list",
            "action": "change",
            "inner": ("values", "delete", "set"),
        }
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def delete_value_set(message: Message, payload_uuid: UUID) -> None:
    text_id = message.body.text
    try:
        value_id = await format_get_mylist_value_id_by_number(payload_uuid, text_id)

        if value_id is None:
            raise ValueError

        async with db_helper.session_factory() as session:
            await delete_mylist_value_by_id(session, value_id)
        await message.answer("✅Пункт успешно удалён")

    except ValueError:
        await message.answer("❌Неправильный формат данных")

    await message.clear_status()

    await view_values(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={
            "type": "list",
            "action": "change",
            "inner": ("values", "change", "get_id"),
        }
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def change_value_get_id(message: Message, payload_uuid: UUID) -> None:
    await message.answer("✏️Напишите <b>номер пункта</b> для изменения")

    status = create_status(
        type="list",
        uuid=payload_uuid,
        action="change",
        inner=("values", "change", "get_value"),
    )
    await message.status(status)


@broker.check(
    Event.STATUS_CALLBACK(
        payload={
            "type": "list",
            "action": "change",
            "inner": ("values", "change", "get_value"),
        }
    )
)
async def change_value_get_value(message: Message, payload_uuid: UUID) -> None:
    text_id = message.body.text
    try:
        value_id = await format_get_mylist_value_id_by_number(payload_uuid, text_id)

        if value_id is None:
            raise ValueError

        await message.answer("✏️Напишите <b>новое значение</b> этого пункта")

        status = create_status(
            type="list",
            uuid=payload_uuid,
            action="change",
            inner=("values", "change", "set", f"{value_id}"),
        )
        await message.status(status)

    except ValueError:
        await message.answer("❌Неправильный формат данных")

        await message.clear_status()

        await view_values(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.STATUS_CALLBACK(
        payload={
            "type": "list",
            "action": "change",
            "inner": ("values", "change", "set"),
        }
    )
)
async def change_value_set(
    message: Message, payload_uuid: UUID, payload_inner: tuple[str]
) -> None:
    value_id = int(payload_inner[-1])

    async with db_helper.session_factory() as session:
        await update_mylist_value_value_by_id(session, value_id, message.body.text)

    await message.answer("✅Пункт изменён")

    await message.clear_status()

    await view_values(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "escape")}
    ),
    allowed=GN.values_view,
    checkers=list_checker,
)
async def change_value_escape(message: Message, payload_uuid: UUID) -> None:
    await message.clear_status()

    await view_list(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_COMMAND, allowed=[GN.list_view, GN.values_view], without_allowed=False
)
async def mark_value(
    message: Message, payload_uuid: UUID, payload_inner: tuple[str]
) -> None:
    text = message.body.text
    if not len(text) > 1:
        return
    text_id = "".join(list(text)[1:])
    if not text_id.isdigit():
        return

    value_id = await format_get_mylist_value_id_by_number(payload_uuid, text_id)
    if value_id is None:
        return

    async with db_helper.session_factory() as session:
        await update_made_of_mylist_value(session, payload_uuid, value_id)

    if "values" in payload_inner:
        await view_values(message=message, payload_uuid=payload_uuid)
    else:
        await view_list(message=message, payload_uuid=payload_uuid)
