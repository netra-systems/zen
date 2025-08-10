
import asyncio
from app.logging_config import central_logger
from typing import Coroutine

logger = central_logger.get_logger(__name__)

class BackgroundTaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, coro: Coroutine):
        """Adds a coroutine to be run as a background task."""
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        logger.info(f"Task {task.get_name()} added to background manager.")

    async def shutdown(self):
        """Cancels all running background tasks."""
        logger.info("Shutting down background tasks...")
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Background tasks shut down.")
