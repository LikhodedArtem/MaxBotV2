import logging

from sqlalchemy.testing.suite.test_reflection import users

from broker.event import Event
from broker.event_broker import Query
from messages.message_schemes import Message, Callback, ContactMessage, Sender
from callback.payload_functions import restore_payload


async def form_webhook_to_query(data: dict) -> list[Query]:
    try:
        if "update_type" not in data:
            raise ValueError("В данных из webhook отсутствует update_type")

        match data["update_type"]:
            case "message_created":
                text = data["message"]["body"]["text"]

                try:
                    message = Message(**data["message"])

                    if list(text)[0] == "/" and len(text) > 1:
                        q1 = Query(event=Event.MESSAGE_COMMAND, message=message)
                        q2 = Query(
                            event=Event.MESSAGE_COMMAND("".join(list(text)[1:])),
                            message=message,
                        )
                        return [q1, q2]

                except Exception:
                    try:
                        message = ContactMessage(**data["message"])
                    except Exception:
                        return []

                q1 = Query(event=Event.MESSAGE_CREATED, message=message)
                q2 = Query(event=Event.MESSAGE_CREATED(text=text), message=message)

                return [q1, q2]

            case "message_callback":
                payload = restore_payload(data["callback"]["payload"])
                message = Message(**data["message"])
                callback = Callback(**data["callback"])

                q1 = Query(
                    event=Event.MESSAGE_CALLBACK, message=message, callback=callback
                )
                q2 = Query(
                    event=Event.MESSAGE_CALLBACK(payload=payload),
                    message=message,
                    callback=callback,
                )

                return [q1, q2]

            case "bot_started":
                q1 = Query(
                    event=Event.BOT_STARTED,
                    user=Sender(**data["user"]),
                )

                return [q1]

            case "bot_stopped":
                q1 = Query(
                    event=Event.BOT_STOPPED,
                    user=Sender(**data["user"]),
                )

                return [q1]

            case "dialog_removed":
                q1 = Query(
                    event=Event.DIALOG_REMOVED,
                    user=Sender(**data["user"]),
                )

                return [q1]

        return []

    except Exception:
        logging.exception("Не получилось отсортировать данные из webhook: '%s'", data)
