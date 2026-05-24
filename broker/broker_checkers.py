from core.config import bot_info
from messages.message_schemes import Message
from core.models.db_helper import db_helper
from crud import get_user_by_max_id
from broker.query import Query
from broker.event import Event


async def reg_checker(queries: list[Query]) -> bool:
    print()
    for query in queries:
        if (
            query.event == Event.MESSAGE_COMMAND("reg")
            or query.event
            == Event.STATUS_CALLBACK(payload={"type": "bot", "action": "reg"})
            or query.event == Event.BOT_STARTED
            or query.event == Event.BOT_STOPPED
            or query.event == Event.DIALOG_REMOVED
        ):

            return True

    for query in queries:
        if query.message is not None:
            message = query.message

            async with db_helper.session_factory() as session:
                user = await get_user_by_max_id(
                    session, message.real_user_id
                )

            if user is None:
                await message.answer(
                    "❌Для работы с ботом необходимо сначала зарегистрироваться. /reg"
                )
                return False
            return True
