import asyncio
import logging
from fastapi import FastAPI, Request
from mcp.server.sse import SseServerTransport
from mcp.server import Server
import uvicorn

logging.basicConfig(level=logging.DEBUG)

server = Server("test")
sse = SseServerTransport("/messages")

app = FastAPI()

@app.get("/sse")
async def sse_route(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

@app.post("/messages")
async def messages_route(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    uvicorn.run(app, port=8001)
