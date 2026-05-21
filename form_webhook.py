import logging

from broker.event import Event
from broker.event_broker import Query
from messages.message_schemes import Message, Callback
from callback.payload_functions import restore_payload


def form_webhook_to_query(data: dict) -> list[Query]:
    try:
        if "update_type" not in data:
            raise ValueError("В данных из webhook отсутствует update_type")

        match data["update_type"]:
            case "message_created":
                text = data["message"]["body"]["text"]
                if list(text)[0] == "/" and len(text) > 1:
                    q1 = Query(event=Event.MESSAGE_COMMAND,
                               message=Message(**data["message"])
                               )
                    q2 = Query(event=Event.MESSAGE_COMMAND("".join(list(text)[1:])),
                               message=Message(**data["message"])
                               )
                    return [q1, q2]

                q1 =  Query(event=Event.MESSAGE_CREATED,
                            message=Message(**data["message"])
                            )
                q2 = Query(event=Event.MESSAGE_CREATED(text=text),
                           message=Message(**data["message"])
                           )

                return [q1, q2]

            case "message_callback":
                payload = restore_payload(data["callback"]["payload"])

                q1 = Query(event=Event.MESSAGE_CALLBACK,
                           message=Message(**data["message"]),
                           callback=Callback(**data["callback"])
                           )
                q2 = Query(event=Event.MESSAGE_CALLBACK(payload=payload),
                           message=Message(**data["message"]),
                           callback=Callback(**data["callback"]))

                return [q1, q2]

    except Exception:
        logging.exception(
            "Не получилось отсортировать данные из webhook: '%s'",
            data
        )
