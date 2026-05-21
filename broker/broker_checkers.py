from core.config import bot_info
from messages.message_schemes import Message
from core.models.db_helper import db_helper
from crud import get_user_by_max_id
from broker.query import Query
from broker.event import Event


async def reg_checker(queries: list[Query]) -> bool:
    print()
    for query in queries:
        if (query.event == Event.MESSAGE_COMMAND("reg")
            or query.event == Event.STATUS_CALLBACK(payload={"type": "bot", "action": "reg"})):

            return True

    for query in queries:
        if hasattr(query, "message"):
            message = query.message

            sender_id = message.sender.user_id
            recipient_id = message.recipient.user_id

            async with db_helper.session_factory() as session:
                user = await get_user_by_max_id(session, sender_id if sender_id != bot_info.my_id else recipient_id)

            if user is None:
                await message.answer(
                    "❌Для работы с ботом необходимо сначала зарегистрироваться. /reg"
                )
                return False
            return True