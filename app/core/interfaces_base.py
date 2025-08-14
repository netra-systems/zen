"""Base service interfaces and mixins."""

import asyncio
from typing import Dict
from datetime import datetime, UTC

from .exceptions import ServiceError
from .error_context import ErrorContext
from .interfaces_service import (
    BaseServiceInterface, 
    ServiceHealth, 
    ServiceMetrics
)


class BaseServiceMixin:
    """Mixin providing common service functionality."""
    
    def __init__(self):
        self._initialized = False
        self._metrics = ServiceMetrics()
        self._background_tasks: set = set()
        
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    @property
    def metrics(self) -> ServiceMetrics:
        """Get service metrics."""
        return self._metrics
    
    def _update_metrics(self, success: bool, response_time: float):
        """Update service metrics."""
        self._metrics.requests_total += 1
        if success:
            self._metrics.requests_successful += 1
        else:
            self._metrics.requests_failed += 1
        
        # Update average response time
        if self._metrics.requests_total == 1:
            self._metrics.average_response_time = response_time
        else:
            self._metrics.average_response_time = (
                (self._metrics.average_response_time * (self._metrics.requests_total - 1) + response_time)
                / self._metrics.requests_total
            )
        
        self._metrics.last_request_timestamp = datetime.now(UTC)
    
    def _create_background_task(self, coro):
        """Create and track a background task."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    async def _cancel_background_tasks(self):
        """Cancel all background tasks."""
        if self._background_tasks:
            for task in list(self._background_tasks):
                task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()


class BaseService(BaseServiceMixin):
    """Base service implementation with common patterns."""
    
    def __init__(self, service_name: str):
        super().__init__()
        self._service_name = service_name
        
    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self._service_name
    
    async def initialize(self) -> None:
        """Initialize the service."""
        if self._initialized:
            return
        
        try:
            await self._initialize_impl()
            self._initialized = True
        except Exception as e:
            raise ServiceError(
                message=f"Failed to initialize service {self._service_name}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    async def _initialize_impl(self) -> None:
        """Service-specific initialization logic."""
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        try:
            await self._cancel_background_tasks()
            await self._shutdown_impl()
            self._initialized = False
        except Exception as e:
            raise ServiceError(
                message=f"Failed to shutdown service {self._service_name}: {e}",
                context=ErrorContext.get_all_context()
            )
    
    async def _shutdown_impl(self) -> None:
        """Service-specific shutdown logic."""
        pass
    
    async def health_check(self) -> ServiceHealth:
        """Perform health check and return status."""
        try:
            # Basic health check - override in subclasses for specific checks
            dependencies = await self._check_dependencies()
            
            status = "healthy"
            for dep_name, dep_status in dependencies.items():
                if dep_status != "healthy":
                    status = "degraded"
                    break
            
            return ServiceHealth(
                service_name=self._service_name,
                status=status,
                timestamp=datetime.now(UTC),
                dependencies=dependencies,
                metrics=self._metrics.model_dump()
            )
        except Exception as e:
            return ServiceHealth(
                service_name=self._service_name,
                status="unhealthy",
                timestamp=datetime.now(UTC),
                dependencies={},
                metrics={"error": str(e)}
            )
    
    async def _check_dependencies(self) -> Dict[str, str]:
        """Check service dependencies - override in subclasses."""
        return {}