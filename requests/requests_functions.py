from __future__ import annotations

__all__ = ["send_message"]

from typing import Optional

import httpx

from core.config import request_settings
from requests.requests_schemes import NewMessageData, MyRequest, MyDeleteRequest


async def send_message(
    message_data: dict | NewMessageData,
    user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
) -> httpx.Response:
    params = {"user_id": user_id} if user_id is not None else {"chat_id": chat_id}

    request = await MyRequest(
        url=request_settings.url + "/messages",
        params=params,
        headers=request_settings.headers,
        json=message_data,
    ).json_data()

    async with httpx.AsyncClient() as client:
        response = await client.post(**request)
    return response


async def edit_message(
    message_data: dict | NewMessageData, message_id: str
) -> httpx.Response:
    params = {"message_id": message_id}

    request = await MyRequest(
        url=request_settings.url + "/messages",
        params=params,
        headers=request_settings.headers,
        json=message_data,
    ).json_data()

    async with httpx.AsyncClient() as client:
        response = await client.put(**request)
    return response


async def delete_message(message_id: str) -> httpx.Response:
    params = {"message_id": message_id}

    request = await MyDeleteRequest(
        url=request_settings.url + "/messages",
        params=params,
        headers=request_settings.headers,
    ).json_data()

    async with httpx.AsyncClient() as client:
        response = await client.delete(**request)
    return response


async def callback_answer(
    callback_id: str, message_data: dict | NewMessageData | None, notification: str
) -> httpx.Response:
    params = {"callback_id": callback_id}

    data = {
        "message": (
            message_data
            if not isinstance(message_data, NewMessageData)
            else message_data.model_dump()
        ),
        "notification": notification,
    }

    request = await MyRequest(
        url=request_settings.url + "/answers",
        params=params,
        headers=request_settings.headers,
        json=data,
    ).json_data()

    async with httpx.AsyncClient() as client:
        response = await client.post(**request)
    return response
