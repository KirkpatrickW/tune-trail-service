from contextlib import asynccontextmanager
from pathlib import Path
from config.logger import logger
import inspect

RELOADING_FLAG_PATH = Path("reloading.flag")

def create_lifespan(on_startup=None, on_shutdown=None, on_reload_startup=None, on_reload_shutdown=None):
    @asynccontextmanager
    async def lifespan(app):
        if not RELOADING_FLAG_PATH.exists():
            logger.info("🚀 Initial startup detected.")
            if on_startup:
                await on_startup() if inspect.iscoroutinefunction(on_startup) else on_startup()
        else:
            logger.info("🔄 Reload startup detected.")
            if on_reload_startup:
                await on_reload_startup() if inspect.iscoroutinefunction(on_reload_startup) else on_reload_startup()

            RELOADING_FLAG_PATH.unlink()

        yield

        if not RELOADING_FLAG_PATH.exists():
            logger.info("🛑 Final shutdown detected.")
            if on_shutdown:
                await on_shutdown() if inspect.iscoroutinefunction(on_shutdown) else on_shutdown()
        else:
            logger.info("🔃 Reload shutdown detected.")
            if on_reload_shutdown:
                await on_reload_shutdown() if inspect.iscoroutinefunction(on_reload_shutdown) else on_reload_shutdown()

    return lifespan