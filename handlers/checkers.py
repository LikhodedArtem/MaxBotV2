from typing import Optional
from uuid import UUID

from messages.message_schemes import Message
from core.models import db_helper
from crud import get_mylist_by_uuid


async def list_checker(message: Message, payload_uuid: UUID, status_inner: Optional[tuple[str]] = None) -> bool:
    async with db_helper.session_factory() as session:
        mylist = await get_mylist_by_uuid(session, payload_uuid)

    if status_inner is None:
        return True

    if mylist is None:
        await message.answer("❌Работа с этим списком прекращена")
        return False

    if mylist.deleted and (status_inner is None or "deleted" not in status_inner):
        await message.answer("❌Список перемещён в корзину. /bin")
        return False

    return True
