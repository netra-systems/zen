
import asyncio
from typing import Coroutine

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class BackgroundTaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, coro: Coroutine):
        """Adds a coroutine to be run as a background task."""
        task = asyncio.create_task(self._wrap_task_with_error_handling(coro))
        self.tasks.append(task)
        logger.info(f"Task {task.get_name()} added to background manager.")

    async def _wrap_task_with_error_handling(self, coro: Coroutine):
        """Wrap task with error handling to prevent crashes."""
        try:
            return await coro
        except Exception as e:
            logger.error(f"Background task failed with error: {e}")
            # Don't re-raise - let the task fail gracefully without crashing the app

    async def shutdown(self):
        """Cancels all running background tasks."""
        logger.info("Shutting down background tasks...")
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Background tasks shut down.")
