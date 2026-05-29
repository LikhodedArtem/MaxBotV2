from typing import Optional
from uuid import UUID

from messages.message_schemes import Message
from core.models import db_helper
from crud import get_mylist_by_uuid, get_users_with_roles_by_mylist_uuid


async def list_checker(message: Message, payload_uuid: UUID, status_inner: Optional[tuple[str]] = None) -> bool:
    async with db_helper.session_factory() as session:
        mylist = await get_mylist_by_uuid(session, payload_uuid)
        users = await get_users_with_roles_by_mylist_uuid(session, payload_uuid)

    users_ids = [info[0].max_id for info in users]


    if mylist is None:
        await message.answer("❌Работа с этим списком прекращена")
        return False

    if mylist.deleted and (status_inner is None or "deleted" not in status_inner):
        await message.answer("❌Список был удалён")
        return False

    if message.real_user_id not in users_ids:
        await message.answer("❌Вы не имеете доступа к этому списку")
        return False

    return True
