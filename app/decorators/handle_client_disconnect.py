import asyncio
from config.logger import Logger
from functools import wraps
from fastapi import Request

logger = Logger()

async def disconnect_poller(request: Request):
    while not await request.state.is_disconnected():
        await asyncio.sleep(0.1)
    logger.warning(f"Request disconnected: {request.method} {request.url}")


def handle_client_disconnect(handler):
    @wraps(handler)
    async def wrapper(request: Request, *args, **kwargs):
        poller_task = asyncio.create_task(disconnect_poller(request))
        handler_task = asyncio.create_task(handler(request, *args, **kwargs))

        done, pending = await asyncio.wait(
            [poller_task, handler_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if handler_task in done:
            return await handler_task
    
    return wrapper
