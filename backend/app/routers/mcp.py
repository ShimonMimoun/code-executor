from mcp.server.sse import SseServerTransport

from app.mcp_server import mcp_server
import logging
import traceback

logger = logging.getLogger(__name__)

sse = SseServerTransport("/api/v1/mcp/messages")

class SSEApp:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            try:
                logger.info("SSE Connected")
                async with sse.connect_sse(scope, receive, send) as streams:
                    await mcp_server.run(
                        streams[0], streams[1], mcp_server.create_initialization_options()
                    )
            except Exception as e:
                logger.error(f"Error in handle_sse: {e}\n{traceback.format_exc()}")
                raise

class MessagesApp:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            await sse.handle_post_message(scope, receive, send)

sse_asgi_app = SSEApp()
messages_asgi_app = MessagesApp()
