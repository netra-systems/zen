"""Resource management utilities for proper cleanup and lifecycle management."""

import asyncio
import atexit
import signal
import sys
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC

from .exceptions import ServiceError
from .error_context import ErrorContext
from app.logging_config import central_logger as logger


class ResourceTracker:
    """Tracks and manages application resources."""
    
    def __init__(self):
        # Using object as the resource type since we store any type of resource
        self._resources: Dict[str, object] = {}
        self._cleanup_callbacks: Dict[str, Callable[[], Any]] = {}
        self._shutdown_order: List[str] = []
        self._shutdown_in_progress = False
        
    def register(
        self, 
        name: str, 
        resource: object, 
        cleanup_callback: Optional[Callable[[], Any]] = None,
        shutdown_priority: int = 0
    ):
        """Register a resource with optional cleanup callback."""
        self._validate_registration_state()
        self._store_resource_data(name, resource, cleanup_callback)
        self._insert_in_shutdown_order(name, shutdown_priority)
        self._set_resource_priority(resource, shutdown_priority)
    
    def _validate_registration_state(self) -> None:
        """Validate that registration is allowed."""
        if self._shutdown_in_progress:
            raise ServiceError(message="Cannot register resources during shutdown")
    
    def _store_resource_data(self, name: str, resource: object, cleanup_callback: Optional[Callable]) -> None:
        """Store resource and cleanup callback."""
        self._resources[name] = resource
        if cleanup_callback:
            self._cleanup_callbacks[name] = cleanup_callback
    
    def _insert_in_shutdown_order(self, name: str, shutdown_priority: int) -> None:
        """Insert resource in shutdown order based on priority."""
        insert_position = self._find_insert_position(shutdown_priority)
        if insert_position is not None:
            self._shutdown_order.insert(insert_position, name)
        else:
            self._shutdown_order.append(name)
    
    def _find_insert_position(self, shutdown_priority: int) -> Optional[int]:
        """Find the correct insertion position based on priority."""
        for i, existing_name in enumerate(self._shutdown_order):
            existing_priority = getattr(self._resources.get(existing_name), '_shutdown_priority', 0)
            if shutdown_priority > existing_priority:
                return i
        return None
    
    def _set_resource_priority(self, resource: object, shutdown_priority: int) -> None:
        """Set shutdown priority on resource if supported."""
        if hasattr(resource, '_shutdown_priority'):
            resource._shutdown_priority = shutdown_priority
    
    def get_resource(self, name: str) -> Optional[Any]:
        """Get a registered resource."""
        return self._resources.get(name)
    
    def unregister(self, name: str) -> bool:
        """Unregister a resource."""
        if name in self._resources:
            del self._resources[name]
            self._cleanup_callbacks.pop(name, None)
            if name in self._shutdown_order:
                self._shutdown_order.remove(name)
            return True
        return False
    
    async def shutdown_all(self, timeout: float = 30.0):
        """Shutdown all resources in order."""
        if self._shutdown_in_progress:
            return
        
        self._shutdown_in_progress = True
        await self._shutdown_resources_in_order(timeout)
        self._clear_all_resources()
    
    async def _shutdown_resources_in_order(self, timeout: float) -> None:
        """Shutdown resources in reverse registration order."""
        per_resource_timeout = timeout / len(self._shutdown_order) if self._shutdown_order else timeout
        for name in reversed(self._shutdown_order):
            try:
                await self._shutdown_single_resource(name, per_resource_timeout)
            except Exception as e:
                logger.error(f"Error shutting down resource {name}: {e}", file=sys.stderr)
    
    async def _shutdown_single_resource(self, name: str, timeout: float) -> None:
        """Shutdown a single resource using appropriate method."""
        resource = self._resources.get(name)
        cleanup_callback = self._cleanup_callbacks.get(name)
        
        if cleanup_callback:
            await self._execute_cleanup_callback(cleanup_callback, timeout)
        else:
            await self._execute_resource_shutdown(resource, timeout)
    
    async def _execute_cleanup_callback(self, cleanup_callback: Callable, timeout: float) -> None:
        """Execute cleanup callback (async or sync)."""
        if asyncio.iscoroutinefunction(cleanup_callback):
            await asyncio.wait_for(cleanup_callback(), timeout=timeout)
        else:
            cleanup_callback()
    
    async def _execute_resource_shutdown(self, resource: object, timeout: float) -> None:
        """Execute resource shutdown method (shutdown or close)."""
        if hasattr(resource, 'shutdown') and callable(resource.shutdown):
            await self._call_resource_method(resource.shutdown, timeout)
        elif hasattr(resource, 'close') and callable(resource.close):
            await self._call_resource_method(resource.close, timeout)
    
    async def _call_resource_method(self, method: Callable, timeout: float) -> None:
        """Call resource method (async or sync)."""
        if asyncio.iscoroutinefunction(method):
            await asyncio.wait_for(method(), timeout=timeout)
        else:
            method()
    
    def _clear_all_resources(self) -> None:
        """Clear all resource tracking data."""
        self._resources.clear()
        self._cleanup_callbacks.clear()
        self._shutdown_order.clear()
    
    def get_resource_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered resources."""
        info = {}
        for name, resource in self._resources.items():
            info[name] = self._build_resource_info(name, resource)
        return info
    
    def _build_resource_info(self, name: str, resource: object) -> Dict[str, Any]:
        """Build information dictionary for a resource."""
        return {
            "type": type(resource).__name__,
            "has_cleanup": name in self._cleanup_callbacks,
            "shutdown_priority": getattr(resource, '_shutdown_priority', 0)
        }


class ApplicationLifecycle:
    """Manages application lifecycle and graceful shutdown."""
    
    def __init__(self):
        self._resource_tracker = ResourceTracker()
        self._initialize_callback_lists()
        self._initialize_shutdown_settings()
        self._started = False
        self._register_signal_handlers()
    
    def _initialize_callback_lists(self) -> None:
        """Initialize callback storage lists."""
        self._startup_callbacks: List[Callable[[], Any]] = []
        self._shutdown_callbacks: List[Callable[[], Any]] = []
    
    def _initialize_shutdown_settings(self) -> None:
        """Initialize shutdown-related settings."""
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30.0
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            self._register_unix_signal_handlers()
        self._register_atexit_handler()
    
    def _register_unix_signal_handlers(self) -> None:
        """Register Unix signal handlers if supported."""
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._signal_handler)
        except (RuntimeError, NotImplementedError):
            pass  # Fallback for environments where signal handlers aren't supported
    
    def _register_atexit_handler(self) -> None:
        """Register atexit handler as fallback."""
        atexit.register(self._atexit_handler)
    
    def _signal_handler(self):
        """Handle shutdown signals."""
        if not self._shutdown_event.is_set():
            logger.info("Received shutdown signal, initiating graceful shutdown...", file=sys.stderr)
            self._shutdown_event.set()
    
    def _atexit_handler(self):
        """Handle atexit cleanup."""
        if not self._shutdown_event.is_set():
            logger.info("Application exiting, cleaning up resources...", file=sys.stderr)
            # Run synchronous cleanup only
            asyncio.run(self._resource_tracker.shutdown_all(timeout=5.0))
    
    def register_startup_callback(self, callback: Callable[[], Any]):
        """Register a callback to run during startup."""
        self._startup_callbacks.append(callback)
    
    def register_shutdown_callback(self, callback: Callable[[], Any]):
        """Register a callback to run during shutdown."""
        self._shutdown_callbacks.append(callback)
    
    def register_resource(
        self,
        name: str,
        resource: object,
        cleanup_callback: Optional[Callable[[], Any]] = None,
        shutdown_priority: int = 0
    ):
        """Register a resource for lifecycle management."""
        self._resource_tracker.register(name, resource, cleanup_callback, shutdown_priority)
    
    def get_resource(self, name: str) -> Optional[Any]:
        """Get a registered resource."""
        return self._resource_tracker.get_resource(name)
    
    async def startup(self) -> None:
        """Run startup procedures."""
        if self._started:
            return
        
        try:
            await self._execute_startup_sequence()
        except Exception as e:
            await self._handle_startup_failure(e)
    
    async def _execute_startup_sequence(self) -> None:
        """Execute the main startup sequence."""
        await self._run_startup_callbacks()
        self._mark_startup_complete()
    
    async def _run_startup_callbacks(self) -> None:
        """Run all registered startup callbacks."""
        for callback in self._startup_callbacks:
            await self._execute_startup_callback(callback)
    
    async def _execute_startup_callback(self, callback: Callable) -> None:
        """Execute a single startup callback (async or sync)."""
        if asyncio.iscoroutinefunction(callback):
            await callback()
        else:
            callback()
    
    def _mark_startup_complete(self) -> None:
        """Mark startup as complete and log success."""
        self._started = True
        logger.info("Application startup completed successfully", file=sys.stderr)
    
    async def _handle_startup_failure(self, error: Exception) -> None:
        """Handle startup failure with cleanup."""
        logger.error(f"Startup failed: {error}", file=sys.stderr)
        await self.shutdown()
        raise
    
    async def shutdown(self, timeout: Optional[float] = None) -> None:
        """Run shutdown procedures."""
        if not self._started:
            return
        effective_timeout = timeout or self._shutdown_timeout
        try:
            await self._execute_shutdown_sequence(effective_timeout)
        except Exception as e:
            self._log_shutdown_error(e)
    
    async def _execute_shutdown_sequence(self, timeout: float) -> None:
        """Execute the main shutdown sequence."""
        logger.info("Starting application shutdown...", file=sys.stderr)
        await self._execute_shutdown_callbacks()
        await self._resource_tracker.shutdown_all(timeout=timeout)
        self._finalize_shutdown()
    
    def _log_shutdown_error(self, error: Exception) -> None:
        """Log shutdown error."""
        logger.error(f"Error during shutdown: {error}", file=sys.stderr)
    
    async def _execute_shutdown_callbacks(self) -> None:
        """Execute all shutdown callbacks with error handling."""
        for callback in self._shutdown_callbacks:
            try:
                await self._execute_single_shutdown_callback(callback)
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}", file=sys.stderr)
    
    async def _execute_single_shutdown_callback(self, callback: Callable) -> None:
        """Execute a single shutdown callback (async or sync)."""
        if asyncio.iscoroutinefunction(callback):
            await asyncio.wait_for(callback(), timeout=5.0)
        else:
            callback()
    
    def _finalize_shutdown(self) -> None:
        """Finalize the shutdown process."""
        self._started = False
        logger.info("Application shutdown completed", file=sys.stderr)
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutdown_event.is_set()
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for application lifespan."""
        await self.startup()
        try:
            yield
        finally:
            await self.shutdown()


class HealthMonitor:
    """Monitors application health and resource status."""
    
    def __init__(self, resource_tracker: ResourceTracker):
        self._resource_tracker = resource_tracker
        self._health_checks: Dict[str, Callable[[], Any]] = {}
        self._last_check_results: Dict[str, Dict[str, Any]] = {}
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    def register_health_check(self, name: str, check_func: Callable[[], Any]):
        """Register a health check function."""
        self._health_checks[name] = check_func
    
    async def start_monitoring(self, check_interval: float = 60.0):
        """Start health monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(check_interval))
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        await self._cancel_monitor_task()
    
    async def _cancel_monitor_task(self) -> None:
        """Cancel the monitoring task if it exists."""
        if not self._monitor_task:
            return
        self._monitor_task.cancel()
        await self._wait_for_task_completion()
    
    async def _wait_for_task_completion(self) -> None:
        """Wait for monitor task to complete cancellation."""
        try:
            await self._monitor_task
        except asyncio.CancelledError:
            pass
    
    async def _monitor_loop(self, check_interval: float) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            await self._execute_monitoring_cycle(check_interval)
    
    async def _execute_monitoring_cycle(self, check_interval: float) -> None:
        """Execute a single monitoring cycle."""
        try:
            await self._perform_health_checks_and_wait(check_interval)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self._handle_monitoring_error(e, check_interval)
    
    async def _perform_health_checks_and_wait(self, check_interval: float) -> None:
        """Perform health checks and wait for next cycle."""
        await self.perform_health_checks()
        await asyncio.sleep(check_interval)
    
    async def _handle_monitoring_error(self, error: Exception, check_interval: float) -> None:
        """Handle monitoring error and wait before retry."""
        logger.error(f"Error in health monitoring: {error}", file=sys.stderr)
        await asyncio.sleep(check_interval)
    
    async def perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Perform all registered health checks."""
        results = {}
        for name, check_func in self._health_checks.items():
            check_result = await self._execute_single_health_check(name, check_func)
            results[name] = check_result
        self._last_check_results = results
        return results

    async def _execute_single_health_check(self, name: str, check_func: Callable) -> Dict[str, Any]:
        """Execute a single health check with error handling."""
        try:
            return await self._run_health_check_with_timing(check_func)
        except Exception as e:
            return self._create_error_health_result(e)

    async def _run_health_check_with_timing(self, check_func: Callable) -> Dict[str, Any]:
        """Run health check function with timing measurement."""
        start_time = datetime.now(UTC)
        result = await self._execute_health_check_function(check_func)
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        return self._create_success_health_result(result, duration, end_time)

    async def _execute_health_check_function(self, check_func: Callable) -> Any:
        """Execute health check function (async or sync)."""
        if asyncio.iscoroutinefunction(check_func):
            return await asyncio.wait_for(check_func(), timeout=10.0)
        else:
            return check_func()

    def _create_success_health_result(self, result: Any, duration: float, end_time: datetime) -> Dict[str, Any]:
        """Create successful health check result."""
        return {
            "status": "healthy" if result else "unhealthy",
            "result": result,
            "duration_seconds": duration,
            "timestamp": end_time.isoformat()
        }

    def _create_error_health_result(self, error: Exception) -> Dict[str, Any]:
        """Create error health check result."""
        return {
            "status": "unhealthy",
            "error": str(error),
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    def get_last_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get the results of the last health check."""
        return self._last_check_results.copy()
    
    def is_healthy(self) -> bool:
        """Check if all health checks are passing."""
        if not self._last_check_results:
            return True  # No checks means healthy by default
        
        return all(
            result.get("status") == "healthy"
            for result in self._last_check_results.values()
        )


# Global application lifecycle manager
_app_lifecycle = ApplicationLifecycle()


def get_app_lifecycle() -> ApplicationLifecycle:
    """Get the global application lifecycle manager."""
    return _app_lifecycle


def register_resource(
    name: str,
    resource: object,
    cleanup_callback: Optional[Callable[[], Any]] = None,
    shutdown_priority: int = 0
):
    """Register a resource with the global lifecycle manager."""
    _app_lifecycle.register_resource(name, resource, cleanup_callback, shutdown_priority)


def get_resource(name: str) -> Optional[Any]:
    """Get a resource from the global lifecycle manager."""
    return _app_lifecycle.get_resource(name)