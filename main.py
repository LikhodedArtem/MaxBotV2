import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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

    return JSONResponse(status_code=200, content={"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
