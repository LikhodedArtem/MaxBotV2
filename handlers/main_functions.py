import asyncio
from typing import Optional
from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.global_names import GN
from core.models import db_helper, MyListUserRole
from handlers.checkers import list_checker
from crud import (
    create_mylist,
    get_mylist_with_values_with_users_by_uuid,
    create_user,
    get_user_by_max_id,
    update_mylist_field,
    create_mylist_value,
    delete_mylist_value_by_id,
    update_mylist_value_value_by_id,
    update_made_of_mylist_value,
    update_delete_to_mylist_by_uuid, get_mylist_with_values_by_uuid,
)

from messages.message_schemes import Message, ContactMessage, Sender
from status.status_functions import create_status
from handlers.help_functions import *


@broker.check(Event.DIALOG_REMOVED)
async def dialog_removed(sender: Sender):
    await sender.clear_status()


@broker.check(Event.BOT_STOPPED)
async def dialog_removed(sender: Sender):
    await sender.clear_status()


@broker.check([Event.BOT_STARTED, Event.MESSAGE_COMMAND("reg")])
async def reg_get(sender: Sender):
    async with db_helper.session_factory() as session:
        if await get_user_by_max_id(session, sender.user_id) is None:
            await sender.answer(
                "📞Для продолжения работы, необходимо нажать на кнопку, для получения ваших данных",
                "inline_keyboard",
                payload=Keyboards.reg(),
            )

            status = create_status(type="bot", action="reg")
            await sender.status(status)
        else:
            await sender.answer(GN.help_text, "inline_keyboard", payload=Keyboards.help())


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

            await asyncio.sleep(GN.sleep_time)
            await help(message=message)
        except Exception as e:
            raise ValueError(e)

    except Exception as e:
        print("===reg_error", e)
        await message.answer(
            "❌Что-то пошло не так. Попробуйте заново пройти регистрацию или напишите в техподдержку"
        )
        await message.clear_status()


@broker.check(Event.MESSAGE_COMMAND("help"))
async def help(message: Message) -> None:
    await message.answer(GN.help_text, "inline_keyboard", payload=Keyboards.help())


@broker.check([Event.MESSAGE_COMMAND("new_list"), Event.MESSAGE_CALLBACK(payload={"type": "help", "action": "new_list"})])
async def new_list(message: Message) -> None:
    async with db_helper.session_factory() as session:
        mylist = await create_mylist(session, message.real_user_id)

    await view_list(message, mylist.uuid)


async def view_list(message: Message, payload_uuid: UUID, edit: bool = False, is_from_lists: bool = False, page: Optional[int] = None, view_owners: bool = False) -> None:
    if is_from_lists and page is None or page is not None and not is_from_lists:
        raise ValueError("Было передан или только page или только is_from_lists. Должно быть передано либо ничего из этого, либо оба сразу")

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_with_users_by_uuid(session, payload_uuid)

    if mylist is None:
        await message.answer(
            "❌Невозможно отобразить список! Он был безвозвратно удалён."
        )
        return

    mylist_type = "<i>Не указан</i>" if mylist.type is None else mylist.type
    mylist_title = "<i>Отсутствует</i>" if mylist.title is None else mylist.title
    mylist_description = (
        "<i>Отсутствует</i>" if mylist.description is None else mylist.description
    )

    mylist_values = mylist_values_to_form(mylist.values)
    mylist_owners, my_role = mylist_owners_to_form(mylist.user_links, message.real_user_id)

    if mylist.deleted:
        emoji = "🗑"
        deleted = "<b>удалённого</b> "
        delete_time = f"<b>Дата удаления</b>: {mylist.create_time}\n"
    else:
        emoji = "⚙️"
        deleted = ""
        delete_time = ""

    text = (
        f"{emoji}Настройки вашего {deleted}списка:\n\n"
        f"<b>Тип</b>: {mylist_type}\n"
        f"<b>Название</b>: {mylist_title}\n"
        f"<b>Описание</b>: {mylist_description}\n\n"
        f"<b>Содержание</b>:\n{mylist_values}\n"
        f"{delete_time}"
    )

    if not deleted:
        payload = Keyboards.change_list(mylist.uuid, my_role, view_owners)
    else:
        payload = Keyboards.change_deleted_list(mylist.uuid)

    if view_owners:
        text += f"\n{mylist_owners}"
        if my_role == MyListUserRole.USER:
            text += "\n**У вас недостаточно прав для изменения списка**"

    text += f"<b>Дата создания</b>: {mylist.create_time}\n"

    if not edit:
        await message.answer(
            text, "inline_keyboard", payload=payload
        )
    else:
        await message.edit(
            text, "inline_keyboard", payload=payload
        )

    delete_inner = ("deleted",) if mylist.deleted else tuple()
    from_inner = ("from_lists", f"{page}") if is_from_lists else tuple()
    inner = delete_inner + from_inner
    if len(inner) == 0: inner = None

    status = create_status(
        type="list", action="view", uuid=payload_uuid, send_callback=False, inner=inner
    )
    await message.status(status)


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

    answer_text = (
        f"Новое {ru_field} сохранено✅"
        if field != "type"
        else f"Новый {ru_field} сохранён✅"
    )

    text = message.body.text

    if len(text) < 64:
        async with db_helper.session_factory() as session:
            await update_mylist_field(session, payload_uuid, field, text)

        await message.answer(answer_text)
    else:
        await message.answer(f"❌Слишком длинн{"ое" if field != "type" else "ый"} <b>{ru_field}</b> списка")

    await message.clear_status()

    await asyncio.sleep(GN.sleep_time)
    await view_list(message, payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "delete", "inner": "start"}
    ),
    checkers=list_checker,
    allowed=GN.list_view,
    compare_uuids=True,
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
    compare_uuids=True,
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
    compare_uuids=True,
)
async def final_delete(message: Message, payload_uuid: UUID) -> None:
    await message.delete()

    async with db_helper.session_factory() as session:
        await update_delete_to_mylist_by_uuid(session, payload_uuid)

    await message.answer("✅Список перемещён в корзину. /bin")

    await message.clear_status()

    await asyncio.sleep(GN.sleep_time)
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
    compare_uuids=True,
)
async def cancel_delete(message: Message, payload_uuid: UUID) -> None:
    await message.delete()
    await message.clear_status()

    status = create_status(type="list", action="view", uuid=payload_uuid)
    await message.status(status)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": "escape"}
    ),
    allowed=GN.list_view,
    can_be_none=True
)
async def list_view_escape(message: Message, status_inner: tuple[str] | None) -> None:
    await message.clear_status()

    if status_inner is not None and len(status_inner) > 0 and "from_lists" in status_inner:
        page = int(status_inner[-1])

        from .view_lists import view_lists
        await view_lists(message=message, page=page)
    else:
        await help(message=message)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "start")}
    ),
    allowed=GN.list_view,
    checkers=list_checker,
    compare_uuids=True,
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
    compare_uuids=True,
)
async def add_value_get(message: Message, payload_uuid: UUID) -> None:
    await message.answer("✏️Пишите новые <b>пункты</b> списка, пока не захотите вернуться", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))

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
    compare_uuids=True,
)
async def add_value_set(message: Message, payload_uuid: UUID) -> None:
    text = message.body.text

    if len(text) < 64:
        async with db_helper.session_factory() as session:
            await create_mylist_value(session, payload_uuid, text)
        await message.answer("✅Новый пункт создан", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))
    else:
        await message.answer("❌Слишком длинный пункт списка", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))


@broker.check(
    Event.MESSAGE_CALLBACK(payload={"type": "l", "action": ";"}),
    allowed=[
        {"type": "list", "action": "change", "inner": ("values", "add", "set")},
        {"type": "list", "action": "change", "inner": ("values", "delete", "set")},
        {"type": "list", "action": "change", "inner": ("values", "change", "get_value")},
        {"type": "list", "action": "change", "inner": ("values", "change", "set")},
    ],
    without_allowed=False
)
async def change_value_partly_escape(message: Message, payload_uuid: UUID) -> None:
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
    compare_uuids=True,
)
async def delete_value_get(message: Message, payload_uuid: UUID) -> None:
    await message.answer("🗑Напишите <b>номер пункта</b> для удаления", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))

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
    compare_uuids=True,
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

    await asyncio.sleep(GN.sleep_time)
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
    compare_uuids=True,
)
async def change_value_get_id(message: Message, payload_uuid: UUID) -> None:
    await message.answer("✏️Напишите <b>номер пункта</b> для изменения", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))

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

        await message.answer("✏️Напишите <b>новое значение</b> этого пункта", "inline_keyboard", payload=Keyboards.change_values_escape(payload_uuid))

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
    text = message.body.text

    if len(text) < 64:
        async with db_helper.session_factory() as session:
            await update_mylist_value_value_by_id(session, value_id, text)

        await message.answer("✅Пункт изменён")
    else:
        await message.answer("❌Слишком длинный пункт списка")

    await message.clear_status()

    await asyncio.sleep(GN.sleep_time)
    await view_values(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("values", "escape")}
    ),
    allowed=GN.values_view,
    checkers=list_checker,
    compare_uuids=True,
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
    if "deleted" in payload_inner:
        return

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
        await update_made_of_mylist_value(session, value_id)

    if "values" in payload_inner:
        await view_values(message=message, payload_uuid=payload_uuid)
    else:
        await view_list(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("view", "owners")}
    ),
    allowed=GN.list_view,
    checkers=list_checker,
    compare_uuids=True,
)
async def list_view_owners(message: Message, payload_uuid: UUID) -> None:
    await view_list(message=message, payload_uuid=payload_uuid, edit=True, view_owners=True)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("hide", "owners")}
    ),
    allowed=GN.list_view,
    checkers=list_checker,
    compare_uuids=True,
)
async def list_view_owners(message: Message, payload_uuid: UUID) -> None:
    await view_list(message=message, payload_uuid=payload_uuid, edit=True, view_owners=False)
