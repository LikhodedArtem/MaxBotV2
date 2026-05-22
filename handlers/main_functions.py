__all__ = ["help", "view_list"]

from typing import Literal
from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.global_names import GN
from core.models import mylist
from core.models.db_helper import db_helper
from crud import (
    create_mylist,
    get_mylist_with_values_by_uuid,
    create_user,
    get_user_by_max_id,
    update_mylist_field, delete_mylist_with_values_by_uuid,
)

from messages.message_schemes import Message, ContactMessage
from status.status_functions import create_status
from handlers.help_functions import mylist_values_to_form


@broker.check(Event.MESSAGE_COMMAND("reg"))
async def reg_get(message: Message):
    await message.answer(
        "📞Для продолжения работы, необходим ваш номер телефона",
        "inline_keyboard",
        payload=Keyboards.reg(),
    )

    status = create_status(type="bot", action="reg")
    await message.status(status)


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
    text = (
        f"❓Что умеет данный бот:\n\n"
        f"/help - Вызвать данное меню-помощник\n"
        f"/reg - Регистрация в боте\n"
        f"/bin - Показать все удалённые элементы\n"
        f"• Списки\n"
        f"/new_list - Создать новый список\n"
    )  # f'/lists_view - Показать все списки\n'\
    # f'• Напоминания\n'\
    # f'/new_remind - Создать новое напоминание\n'\
    # f'/reminds_view - Просмотреть все напоминания'\

    await message.answer(text)


@broker.check(Event.MESSAGE_COMMAND("new_list"))
async def new_list(message: Message) -> None:
    user_id = message.sender.user_id

    async with db_helper.session_factory() as session:
        mylist = await create_mylist(session, user_id)

    await view_list(message, mylist.uuid)


async def view_list(message: Message, payload_uuid: UUID, edit: bool = False) -> None:
    status = create_status(
        type="list",
        uuid=payload_uuid,
        action="view",
        inner="list",
        is_background=True,
        send_callback=False,
    )
    await message.status(status)

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_by_uuid(session, payload_uuid)

    if mylist is None:
        await message.answer("❌Невозможно отобразить список! Он был безвозвратно удалён.")
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
    )
)
async def list_field_get(
    message: Message, payload_uuid: UUID, payload_inner: list[str]
) -> None:
    field = payload_inner[-1]

    text = f"✏️Напишите нов{"ый" if field == "type" else "ое"} <b>{GN.get(field).capitalize()}</b>\n"

    status = create_status(type="list", uuid=payload_uuid, action="set", inner=["field", field])
    print("===request_list_field", message)

    await message.status(status)

    await message.answer(text)


@broker.check(
    Event.STATUS_CALLBACK(payload={"type": "list", "action": "set", "inner": "field"})
)
async def list_field_set(
    message: Message, payload_uuid: UUID, payload_inner: list[str]
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
    )
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


@broker.check(Event.MESSAGE_CALLBACK(payload={"type": "list", "action": "delete", "inner": "first"}), allowed="List-Delete")
async def second_delete(message: Message, payload_uuid: UUID) -> None:
    await message.edit(
        "Вы <b>точно</b> уверены, что хотите <b>удалить</b> список?",
        "inline_keyboard",
        payload=Keyboards.yes_no(
            type="list", action="delete", payload_uuid=payload_uuid, inner="second"
        ),
    )


@broker.check(Event.MESSAGE_CALLBACK(payload={"type": "list", "action": "delete", "inner": "second"}), allowed="List-Delete")
async def final_delete(message: Message, payload_uuid: UUID) -> None:
    await message.delete()

    async with db_helper.session_factory() as session:
        await delete_mylist_with_values_by_uuid(session, payload_uuid)

    await message.answer("✅Список безвозвратно удалён")

    await message.clear_status()