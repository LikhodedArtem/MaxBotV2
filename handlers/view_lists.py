import asyncio
from uuid import UUID

from broker import broker
from broker.event import Event
from buttons.keyboards import Keyboards
from core.config import bot_info
from core.global_names import GN
from core.models import db_helper, MyListUserRole
from handlers.checkers import list_checker
from crud import get_mylists_by_max_id, delete_deleted_mylists_by_max_id, delete_deleted_from_mylists_by_uuid, \
    add_user_to_list, get_users_with_roles_by_mylist_uuid, get_mylist_by_uuid, get_user_from_association_by_number, \
    delete_user_from_association_by_id, delete_user_from_mylist_by_max_id_and_uuid

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

        text = "❌У вас нет ни одного списка" if not deleted else "❌Корзина пуста"
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
    await message.answer("Вы уверены, что хотите <b>очистить</b> корзину?", "inline_keyboard",
                         payload=Keyboards.yes_no(type="lists", action="view", inner="clear"))

    await message.clear_status()
    await message.status(name="Clear-Bin")


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


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "work")}
    ),
    allowed=GN.list_view,
    checkers=list_checker,
    compare_uuids=True,
)
async def list_work_with_owners(message: Message, payload_uuid: UUID):
    async with db_helper.session_factory() as session:
        users = await get_users_with_roles_by_mylist_uuid(session, payload_uuid)

    owners_text, my_role = mylist_owners_to_form(users, message.real_user_id)

    await message.answer(f"✏️Выберите действие с участниками списка: \n{owners_text}", "inline_keyboard", payload=Keyboards.work_with_lists_owners(payload_uuid))

    status = create_status(name="Work-With-Owners")
    await message.status(status)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "share", "get")}
    ),
    allowed="Work-With-Owners",
    checkers=list_checker,
    compare_uuids=True,
)
async def list_owners_share_get(message: Message, payload_uuid: UUID):
    await message.answer("Нажмите <b>📎 -> \"Контакты\"</b>, и выберите пользователя, с которым хотите поделиться списком", "inline_keyboard", payload=Keyboards.escape("list", "change", payload_uuid, ("owners", "mini", "escape")))

    status = create_status(type="list", uuid=payload_uuid, action="change", inner=("owners", "share", "set"))
    await message.status(status)



@broker.check(
    Event.STATUS_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "share", "set")}
    ),
    checkers=list_checker,
    compare_uuids=True,
)
async def list_owners_share_set(message: Message, payload_uuid: UUID):
    if not isinstance(message, ContactMessage):
        return

    user_data = message.body.attachments[0].payload.max_info.model_dump()
    user_data["chat_id"] = message.recipient.chat_id
    async with db_helper.session_factory() as session:
        await add_user_to_list(session, payload_uuid, user_data)

    await message.answer("✅Пользователь добавлен")

    await message.clear_status()

    await view_list(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "delete", "get")}
    ),
    allowed="Work-With-Owners",
    checkers=list_checker,
    compare_uuids=True,
)
async def list_owners_delete_get(message: Message, payload_uuid: UUID):
    async with db_helper.session_factory() as session:
        users = await get_users_with_roles_by_mylist_uuid(session, payload_uuid)

    owners_text = ""
    i = 1
    for info in users:
        if info[1] == MyListUserRole.AUTHOR:
            continue

        first_name = info[0].first_name
        last_name = " " + info[0].last_name if info[0].last_name is not None else ""

        owners_text += f"\t/{i} {first_name}{last_name}\n"
        i += 1

    if not owners_text:
        await message.answer("❌Вы не можете никого удалить")
        await list_owners_mini_escape(message=message, payload_uuid=payload_uuid)
        return

    text = (f"🗑Вы имеете возможность удалить следующих <b>участников</b>:\n\n"
            f"{owners_text}"
            f"\n<b>Нажмите на номер</b> участника для его удаления")

    await message.answer(text, "inline_keyboard", payload=Keyboards.escape("list", "change", payload_uuid, ("owners", "mini", "escape")))

    status = create_status(type="list", action="change", inner=("owners", "delete", "set"), uuid=payload_uuid)
    await message.status(status)


@broker.check(
    Event.MESSAGE_COMMAND,
    allowed={"type": "list", "action": "change", "inner": ("owners", "delete", "set")},
    checkers=list_checker,
    compare_uuids=True,
    without_allowed=False,
)
async def list_owners_delete_set(message: Message, payload_uuid: UUID):
    text = message.body.text
    if len(text) < 2 or list(text)[0] != "/":
        return
    text_id = int(text[1:])
    if text_id < 1:
        await message.answer("❌Указан неверный номер")
        await list_owners_mini_escape(message=message, payload_uuid=payload_uuid)
        return

    async with db_helper.session_factory() as session:
        mylist = await get_mylist_by_uuid(session, payload_uuid)
        user = await get_user_from_association_by_number(session, mylist.id, text_id)
        if user is None:
            await message.answer("❌Указан неверный номер")
            await list_owners_mini_escape(message=message, payload_uuid=payload_uuid)
            return
        await delete_user_from_association_by_id(session, mylist.id, user.user_id)

    await message.answer("✅Участник удалён")

    await list_owners_mini_escape(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "mini", "escape")}
    ),
    allowed=[
        {"type": "list", "action": "change", "inner": ("owners", "delete", "set")},
        {"type": "list", "action": "change", "inner": ("owners", "share", "set")}
    ],
    checkers=list_checker,
    compare_uuids=True,
)
async def list_owners_mini_escape(message: Message, payload_uuid: UUID):
    await message.clear_status()

    await list_work_with_owners(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("owners", "escape")}
    ),
    allowed="Work-With-Owners",
    checkers=list_checker,
    compare_uuids=True,
    without_allowed=False
)
async def list_owners_escape(message: Message, payload_uuid: UUID):
    await message.clear_status()

    await view_list(message=message, payload_uuid=payload_uuid)


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("forever", "escape", "first")}
    ),
    checkers=list_checker,
    allowed=GN.list_view,
    compare_uuids=True,
)
async def first_escape_forever(message: Message, payload_uuid: UUID) -> None:
    await message.answer(
        "Вы уверены, что хотите <b>навсегда покинуть</b> список?",
        "inline_keyboard",
        payload=Keyboards.yes_no(
            type="list", action="change", payload_uuid=payload_uuid, inner=("forever", "escape", "second")
        ),
    )

    await message.status(name="Forever-Escape")


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("forever", "escape", "second", "yes")}
    ),
    allowed="Forever-Escape",
    checkers=list_checker,
    compare_uuids=True,
)
async def second_escape_forever(message: Message, payload_uuid: UUID) -> None:
    await message.edit(
        "Вы <b>точно</b> уверены, что хотите <b>навсегда покинуть</b> список?",
        "inline_keyboard",
        payload=Keyboards.yes_no(
            type="list", action="change", payload_uuid=payload_uuid, inner=("forever", "escape", "final")
        ),
    )


@broker.check(
    Event.MESSAGE_CALLBACK(
        payload={"type": "list", "action": "change", "inner": ("forever", "escape", "final", "yes")}
    ),
    allowed="Forever-Escape",
    checkers=list_checker,
    compare_uuids=True,
)
async def final_escape_forever(message: Message, payload_uuid: UUID) -> None:
    await message.delete()

    async with db_helper.session_factory() as session:
        await delete_user_from_mylist_by_max_id_and_uuid(session, payload_uuid, message.real_user_id)

    await message.answer("✅Вы покинули список")

    await message.clear_status()

    await asyncio.sleep(GN.sleep_time)
    await help(message=message)


@broker.check(
    [
        Event.MESSAGE_CALLBACK(
            payload={"type": "list", "action": "change", "inner": ("forever", "escape", "second", "no")}
        ),
        Event.MESSAGE_CALLBACK(
            payload={"type": "list", "action": "change", "inner": ("forever", "escape", "final", "no")}
        ),
    ],
    "Forever-Escape",
    checkers=list_checker,
    compare_uuids=True,
)
async def cancel_escape_forever(message: Message, payload_uuid: UUID) -> None:
    await message.delete()
    await message.clear_status()

    status = create_status(type="list", action="view", uuid=payload_uuid)
    await message.status(status)