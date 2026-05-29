"""Функции для работы с Payload"""

from __future__ import annotations

import re

from .payload_schemes import *

__all__ = ["convert_payload", "restore_payload"]


def convert_payload(payload: Payload) -> str:
    """Payload -> str

    Args:
        payload: Payload для конвертирования в строку

    """

    answer = f"t={payload.type}&a={payload.action}"

    if payload.uuid is not None:
        answer += f"&u={payload.uuid}"

    for number, inner in enumerate(payload.inner.value):
        answer += f"&i{number + 1}={inner}"

    return answer


def restore_payload(payload: str) -> Payload:
    """str -> Payload

    Args:
        payload: строка для восстановления в Payload

    """

    try:
        tags = {"t": "type", "u": "uuid", "a": "action", "i": "inner"}
        regular = r"(?P<tag>[A-Za-z]\d*)=(?P<value>[^&=\s]+)"

        data = {"type": None, "action": None}

        inner = ()

        find = re.findall(regular, payload)
        for item in range(len(find)):
            tag = find[item][0]
            value = find[item][1]

            if tag in ("t", "u", "a"):
                data[tags[tag]] = value
            elif bool(re.fullmatch(r"i\d+", tag)):
                inner += (value,)
            else:
                raise ValueError(f"Несуществующий ключ {tag} в Payload")

        data["inner"] = inner

        assert None not in list(data.values()), "Один из ключей отсутствует в Payload"

        return Payload(**data)

    except Exception as e:
        raise ValueError(f"Неправильный вид Payload по причине: {str(e)}")
