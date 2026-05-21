from uuid import UUID

from messages.message_schemes import Message
from core.models.db_helper import db_helper
from crud import get_mylist_by_uuid


async def list_checker(message: Message, payload_uuid: UUID) -> bool:
    async with db_helper.session_factory() as session:
        mylist = await get_mylist_by_uuid(session, payload_uuid)

    if mylist is None:
        await message.answer("❌Работа с этим списком прекращена")
        return False
    return True
