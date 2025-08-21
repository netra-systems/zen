"""Base service interfaces and mixins."""

import asyncio
from typing import Dict, Any
from datetime import datetime, UTC

from netra_backend.app.exceptions import ServiceError
from app.schemas.shared_types import ErrorContext
from netra_backend.app.interfaces_service import (
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
        self._update_success_metrics(success)
        self._update_response_time(response_time)
        self._metrics.last_request_timestamp = datetime.now(UTC)
    
    def _update_success_metrics(self, success: bool):
        """Update success/failure metrics."""
        if success:
            self._metrics.requests_successful += 1
        else:
            self._metrics.requests_failed += 1
    
    def _update_response_time(self, response_time: float):
        """Update average response time."""
        if self._metrics.requests_total == 1:
            self._metrics.average_response_time = response_time
        else:
            self._calculate_avg_response_time(response_time)
    
    def _calculate_avg_response_time(self, response_time: float):
        """Calculate new average response time."""
        prev_avg = self._metrics.average_response_time
        total_requests = self._metrics.requests_total
        self._metrics.average_response_time = (
            (prev_avg * (total_requests - 1) + response_time) / total_requests
        )
    
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
        
        await self._perform_initialization()
    
    async def _perform_initialization(self) -> None:
        """Perform service initialization with error handling."""
        try:
            await self._initialize_impl()
            self._initialized = True
        except Exception as e:
            self._raise_initialization_error(e)
    
    def _raise_initialization_error(self, error: Exception):
        """Raise formatted initialization error."""
        raise ServiceError(
            message=f"Failed to initialize service {self._service_name}: {error}",
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
            self._raise_shutdown_error(e)
    
    def _raise_shutdown_error(self, error: Exception):
        """Raise formatted shutdown error."""
        raise ServiceError(
            message=f"Failed to shutdown service {self._service_name}: {error}",
            context=ErrorContext.get_all_context()
        )
    
    async def _shutdown_impl(self) -> None:
        """Service-specific shutdown logic."""
        pass
    
    async def health_check(self) -> ServiceHealth:
        """Perform health check and return status."""
        try:
            dependencies = await self._check_dependencies()
            status = self._determine_health_status(dependencies)
            return self._create_health_response(status, dependencies)
        except Exception as e:
            return self._create_unhealthy_response(e)
    
    def _determine_health_status(self, dependencies: Dict[str, str]) -> str:
        """Determine overall health status from dependencies."""
        for dep_status in dependencies.values():
            if dep_status != "healthy":
                return "degraded"
        return "healthy"
    
    def _create_health_response(self, status: str, dependencies: Dict[str, str]) -> ServiceHealth:
        """Create healthy service health response."""
        health_data = self._build_health_response_data(status, dependencies)
        return ServiceHealth(**health_data)
    
    def _build_health_response_data(self, status: str, dependencies: Dict[str, str]) -> Dict[str, Any]:
        """Build health response data dictionary."""
        return {
            "service_name": self._service_name, "status": status, "timestamp": datetime.now(UTC),
            "dependencies": dependencies, "metrics": self._metrics.model_dump()
        }
    
    def _create_unhealthy_response(self, error: Exception) -> ServiceHealth:
        """Create unhealthy service health response."""
        error_data = self._build_unhealthy_response_data(error)
        return ServiceHealth(**error_data)
    
    def _build_unhealthy_response_data(self, error: Exception) -> Dict[str, Any]:
        """Build unhealthy response data dictionary."""
        return {
            "service_name": self._service_name, "status": "unhealthy", "timestamp": datetime.now(UTC),
            "dependencies": {}, "metrics": {"error": str(error)}
        }
    
    async def _check_dependencies(self) -> Dict[str, str]:
        """Check service dependencies - override in subclasses."""
        return {}