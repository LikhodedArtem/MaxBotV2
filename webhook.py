import asyncio
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from broker import broker
from form_webhook import form_webhook_to_query
from status.status_functions import mark_status_to_query

from handlers import *

app = FastAPI()


@app.get("/ping")
async def ping_pong():
    return "pong"


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    # secret = request.headers.get("X-Max-Bot-Api-Secret")
    data = json.loads(body.decode())

    print("===webhook", data)
    query = form_webhook_to_query(data)
    print("===webhook", query)

    query = await mark_status_to_query(query)

    await broker.publish(query)

    return JSONResponse(status_code=200, content={"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("webhook:app", host="0.0.0.0", port=80, reload=True)
