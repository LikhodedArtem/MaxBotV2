from messages.message_schemes import Message
from core.models.db_helper import db_helper
from crud import get_user_by_max_id
from broker.query import Query


async def reg_checker(queries: list[Query]) -> bool:
    for query in queries:
        if hasattr(query, "message"):
            message = query.message
            print("===reg_checker", message.sender.user_id)

            async with db_helper.session_factory() as session:
                user = await get_user_by_max_id(session, message.sender.user_id)

            if user is None:
                await message.answer(
                    "❌Для работы с ботом необходимо сначала зарегистрироваться. /reg"
                )
                return False
            return True