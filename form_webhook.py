import logging

from broker.event import Event
from broker.event_broker import Query
from messages.message_schemes import Message, ContactMessage, Callback


def form_webhook_to_query(data: dict) -> Query:
    try:
        if "update_type" not in data:
            raise ValueError("В данных из webhook отсутствует update_type")

        match data["update_type"]:
            case "message_created":
                text = data["message"]["body"]["text"]
                if list(text)[0] == "/":
                    return Query(event=Event.MESSAGE_COMMAND("".join(list(text)[1:])), message=Message(**data["message"]))
                return Query(event=Event.MESSAGE_CREATED, message=Message(**data["message"]))

            case "message_callback":
                return Query(event=Event.MESSAGE_CALLBACK, message=Message(**data["message"]), callback=Callback(**data["callback"]))
    except Exception:
        logging.exception(
            "Не получилось отсортировать данные из webhook: '%s'",
            data
        )
