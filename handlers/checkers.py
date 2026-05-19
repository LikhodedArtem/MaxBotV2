from uuid import UUID

from messages.message_schemes import Message
from core.models.db_helper import db_helper
from crud import get_mylist_by_uuid, get_user_by_max_id


async def reg_checker(message: Message) -> bool:
    async with db_helper.session_factory() as session:
        user = await get_user_by_max_id(session, message.sender.user_id)

    if user is None:
        await message.answer(
            "❌Для работы с ботом необходимо сначала зарегистрироваться. /reg"
        )
        return False
    return True

async def list_checker(message: Message, payload_uuid: UUID) -> bool:
    async with db_helper.session_factory() as session:
        mylist = await get_mylist_by_uuid(session, payload_uuid)

    if mylist is None:
        await message.answer(
            "❌Работа с этим списком прекращена"
        )
        return False
    return True