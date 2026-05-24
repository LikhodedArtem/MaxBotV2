import asyncio
from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.config import bot_info
from core.global_names import GN
from core.models.db_helper import db_helper
from handlers.checkers import list_checker
from crud import get_mylists_by_max_id, delete_deleted_mylists_by_max_id, delete_deleted_from_mylists_by_uuid

from messages.message_schemes import Message, ContactMessage, Sender
from status.status_functions import create_status
from handlers.help_functions import *

from .main_functions import view_list, help


@broker.check([Event.MESSAGE_COMMAND("lists_view"), Event.MESSAGE_CALLBACK(payload={"type": "help", "action": "lists_view"})])
async def view_lists(message: Message, page: int = 1, edit: bool = False, deleted: bool = False):
    if page < 1:
        return

    async with db_helper.session_factory() as session:
        mylists = await get_mylists_by_max_id(session, message.real_user_id, page, deleted)

    base_text = "🔍Выберите <b>Список</b> для просмотра:" if not deleted else "🗑Выберите <b>Удалённый список</b> для просмотра"
    first = page == 1

    if mylists is None:
        if not first: return

        text = "❌У вас нет ни одного списка. /new_list" if not deleted else "❌Корзина пуста"
        if not edit:
            await message.answer(
                text,
                "inline_keyboard",
                payload=Keyboards.lists(page, [], first=first, final=True),
            )
        else:
            await message.edit(
                text,
                "inline_keyboard",
                payload=Keyboards.lists(page, [], first=first, final=True),
            )
    else:
        final = True if len(mylists) != 11 else False
        mylist_info = [[mylist.title, mylist.uuid] for i, mylist in enumerate(mylists) if i != 10]

        if not edit:
            await message.answer(
                base_text,
                "inline_keyboard",
                payload=Keyboards.lists(page, mylist_info, first=first, final=final, deleted=deleted),
            )
        else:
            await message.edit(
                base_text,
                "inline_keyboard",
                payload=Keyboards.lists(page, mylist_info, first=first, final=final, deleted=deleted),
            )
    status = create_status(type="lists", action="view", inner=f"{page}")
    await message.status(status)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "lists", "action": "view", "inner": "left"}
    ),
    allowed={"type": "lists", "action": "view"},
    without_allowed=False
)
async def view_lists_left(message: Message, status_inner: tuple[str]):
    await view_lists(message=message, page=int(status_inner[-1]) - 1, edit=True)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "lists", "action": "view", "inner": "right"}
    ),
    allowed={"type": "lists", "action": "view"},
    without_allowed=False
)
async def view_lists_right(message: Message, status_inner: tuple[str]):
    await view_lists(message=message, page=int(status_inner[-1]) + 1, edit=True)


@broker.check(
    Event.MESSAGE_CALLBACK(
            payload={"type": "lists", "action": "view", "inner": "list"}
    ),
    allowed={"type": "lists", "action": "view"},
    can_be_none=True
)
async def view_lists_view_list(message: Message, payload_uuid: UUID, status_inner: tuple[str]):
    page = int(status_inner[-1]) if status_inner is not None else 1
    await view_list(message, payload_uuid, is_from_lists=True, page=page)


@broker.check(
    Event.MESSAGE_CALLBACK(
            payload={"type": "lists", "action": "view", "inner": "escape"}
    ),
    allowed={"type": "lists", "action": "view"}
)
async def view_lists_escape(message: Message):
    await message.clear_status()

    await help(message=message)


@broker.check(
    [
        Event.MESSAGE_COMMAND("bin"),
        Event.MESSAGE_CALLBACK(payload={"type": "help", "action": "bin"})
    ]
)
async def bin(message: Message):
    await view_lists(message=message, deleted=True)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "lists", "action": "view", "inner": "clear"}
    ),
    allowed={"type": "lists", "action": "view"}
)
async def bin_clear(message: Message):
    await message.clear_status()
    await message.status(name="Clear-Bin")

    await message.answer("Вы уверены, что хотите <b>очистить</b> корзину?", "inline_keyboard", payload=Keyboards.yes_no(type="lists", action="view", inner="clear"))


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "lists", "action": "view", "inner": ("clear", "yes")}
    ),
    allowed="Clear-Bin",
)
async def bin_clear_yes(message: Message):
    await message.clear_status()

    async with db_helper.session_factory() as session:
        await delete_deleted_mylists_by_max_id(session, message.real_user_id)

    await message.answer("✅Корзина очищена")

    await asyncio.sleep(GN.sleep_time)
    await help(message=message)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "lists", "action": "view", "inner": ("clear", "no")}
    ),
    allowed="Clear-Bin",
)
async def bin_clear_no(message: Message):
    await message.clear_status()
    await message.delete()

    await bin(message=message)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("deleted", "get")}
    ),
    allowed=[{"type": "list", "action": "view"}, {"type": "lists", "action": "view"}],
    compare_uuids=True,
)
async def bin_recover_list(message: Message, payload_uuid: UUID):
    await message.answer("✅Список восстановлен")

    async with db_helper.session_factory() as session:
        await delete_deleted_from_mylists_by_uuid(session, payload_uuid)

    await asyncio.sleep(GN.sleep_time)
    await view_list(message=message, payload_uuid=payload_uuid)