"""Agent-related service interfaces for multi-agent systems."""

from .interfaces_service import AsyncServiceInterface
from .interfaces_base import BaseService


class AsyncTaskService(BaseService, AsyncServiceInterface):
    """Base service for services that run background tasks."""
    
    def __init__(self, service_name: str):
        super().__init__(service_name)
        self._background_running = False
    
    async def start_background_tasks(self) -> None:
        """Start background tasks."""
        if self._background_running:
            return
        
        self._background_running = True
        await self._start_background_tasks_impl()
    
    async def _start_background_tasks_impl(self) -> None:
        """Implementation-specific background task startup."""
        pass
    
    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        if not self._background_running:
            return
        
        self._background_running = False
        await self._stop_background_tasks_impl()
        await self._cancel_background_tasks()
    
    async def _stop_background_tasks_impl(self) -> None:
        """Implementation-specific background task shutdown."""
        pass
    
    async def _shutdown_impl(self) -> None:
        """Shutdown implementation."""
        await self.stop_background_tasks()