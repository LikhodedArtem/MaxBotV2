import asyncio
import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pprint import pprint

from broker import broker
from core.config import bot_info
from form_webhook import form_webhook_to_query
from status.clear_old_statuses import cleanup_statuses_loop
from status.status_functions import add_status_query

from handlers import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(cleanup_statuses_loop())
    yield
    cleanup_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/ping")
async def ping_pong():
    return "pong"


pprint(broker.subscribers)

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()

    secret = request.headers.get("x-max-bot-api-secret")

    if bot_info.secret_key != secret:
        logging.error("Попытка прислать данные с неверным ключом!")
        return JSONResponse(status_code=401,
        content={"error":
                    {
                    "code": "invalid_client_secret",
                    "message": f"Указан неверный секретный ключ {secret}."
                    }
                }
        )

    data = json.loads(body.decode())

    print("===webhook", data)

    queries = await form_webhook_to_query(data)
    print("===webhook", queries)
    queries = await add_status_query(queries)

    for query in queries:
        print("===webhook", query)

    await broker.publish_queries(queries)

    return JSONResponse(status_code=200, content={"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("webhook:app", host="0.0.0.0", port=80, reload=False)
