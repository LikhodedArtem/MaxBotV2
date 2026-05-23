from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.global_names import GN
from core.models.db_helper import db_helper
from handlers.checkers import list_checker
from crud import get_mylists_by_max_id

from messages.message_schemes import Message, ContactMessage, Sender
from status.status_functions import create_status
from handlers.help_functions import *


@broker.check(Event.MESSAGE_COMMAND("lists_view"))
async def view_lists(message: Message, page: int = 1, edit: bool = False):
    async with db_helper.session_factory() as session:
        mylists = await get_mylists_by_max_id(session, message.sender.user_id, page)

    base_text = "🔍Выберите список для просмотра:"
    first = page == 1

    if mylists is None:
        text = "❌У вас нет ни одного списка." if first else base_text
        if not edit:
            await message.answer(
                text,
                "inline_keyboard",
                payload=Keyboards.lists([], first=first, final=True),
            )
        else:
            await message.edit(
                text,
                "inline_keyboard",
                payload=Keyboards.lists([], first=first, final=True),
            )
    else:
        info = [[mylist.title, mylist.uuid] for mylist in mylists]
        final = len(info) != 10
        mylist_info = format_lists_info(info)

        if not edit:
            await message.answer(
                base_text,
                "inline_keyboard",
                payload=Keyboards.lists(mylist_info, first=first, final=final),
            )
        else:
            await message.edit(
                base_text,
                "inline_keyboard",
                payload=Keyboards.lists(mylist_info, first=first, final=final),
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
    await view_lists(message, int(status_inner[-1]) - 1, edit=True)


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
    allowed={"type": "lists", "action": "view"}
)
async def view_lists_view_list(message: Message, payload_uuid: UUID):
    print("ZZZZZZZZZZZZZZZZZZZZ") 