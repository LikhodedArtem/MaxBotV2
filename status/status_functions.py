__all__ = ["add_status_query", "create_payload_status"]

from copy import deepcopy
from datetime import datetime
from typing import Optional
from uuid import UUID

from broker.event_broker import Query
from broker.event import Event
from callback.payload_schemes import Payload, PayloadCheck, Inner
from core.config import bot_info
from status.status_shemes import *
from status.status_crud import get_status
from messages.message_schemes import Callback


def create_payload_status(
    type: str,
    action: str,
    uuid: Optional[UUID] = None,
    inner: Optional[str | list[str]] = None,
) -> Status:
    """Функция для быстрого создания Payload статуса"""

    payload = Payload(type=type, uuid=uuid, action=action, inner=Inner(value=inner))
    status = Status(value=payload)

    return status


async def add_status_query(queries: list[Query]) -> list[Query]:
    for query in queries:
        if query.message is not None:
            sender_id = query.message.sender.user_id
            recipient_id = query.message.recipient.user_id

            status = await get_status(sender_id if sender_id != bot_info.my_id else recipient_id)
            print("===add_status_query", status)

            if status is None:
                continue

            if not status.is_background:
                queries = []

            if status.send_callback:
                status_query = deepcopy(query)
                if status.is_str:
                    status_query.event=Event.STATUS_CALLBACK(name=status.value)
                else:
                    status_query.event=Event.STATUS_CALLBACK(payload=status.value)

                queries.append(status_query)

            break

    return queries


# def get_query_from_status(query: Query) -> Query | None:
#     if (query.message is not None
#         and query.callback is None
#         and isinstance(query.status, Status)
#         and query.status.is_payload
#         and query.status.send_callback):
#
#         timestamp = int(datetime.now().timestamp() * 1000)
#
#         new_callback = Callback(
#             timestamp=timestamp,
#             callback_id="status_callback",
#             payload=query.status.value,
#             user=query.message.sender,
#             type="status",
#         )
#
#         new_query = Query(event=Event.STATUS_CALLBACK, callback=new_callback, message=query.message)
#
#         return new_query
#     return None