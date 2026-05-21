__all__ = ["help", "view_list"]

from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.models import mylist
from core.models.db_helper import db_helper
from crud import create_mylist, get_mylist_with_values_by_uuid
from messages.message_schemes import Message
from status.status_functions import create_payload_status
from handlers.help_functions import mylist_values_to_form


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
    status = create_payload_status(type="list", uuid=payload_uuid, action="view", inner="list")
    await message.status(status, is_background=True, send_callback=False)

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_with_values_by_uuid(session, payload_uuid)

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
            text, "inline_keyboard", payload=await Keyboards.change_list(mylist.uuid)
        )
    else:
        await message.edit(
            text, "inline_keyboard", payload=await Keyboards.change_list(mylist.uuid)
        )


@broker.check(Event.MESSAGE_COMMAND("yyy"))
async def create(message: Message) -> None:
    await message.answer("command yyy")


@broker.check(Event.MESSAGE_COMMAND)
async def create(message: Message) -> None:
    await message.answer("command")

@broker.check(Event.MESSAGE_COMMAND("zzz"))
async def create(message: Message) -> None:
    await message.answer("command zzz")