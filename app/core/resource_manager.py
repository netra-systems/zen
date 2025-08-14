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
        if self._shutdown_in_progress:
            raise ServiceError(message="Cannot register resources during shutdown")
        
        self._resources[name] = resource
        if cleanup_callback:
            self._cleanup_callbacks[name] = cleanup_callback
        
        # Insert in shutdown order based on priority (higher priority shuts down first)
        inserted = False
        for i, existing_name in enumerate(self._shutdown_order):
            existing_priority = getattr(self._resources.get(existing_name), '_shutdown_priority', 0)
            if shutdown_priority > existing_priority:
                self._shutdown_order.insert(i, name)
                inserted = True
                break
        
        if not inserted:
            self._shutdown_order.append(name)
        
        # Store priority for reference
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
        
        # Shutdown in reverse registration order (LIFO)
        for name in reversed(self._shutdown_order):
            try:
                resource = self._resources.get(name)
                cleanup_callback = self._cleanup_callbacks.get(name)
                
                if cleanup_callback:
                    if asyncio.iscoroutinefunction(cleanup_callback):
                        await asyncio.wait_for(cleanup_callback(), timeout=timeout / len(self._shutdown_order))
                    else:
                        cleanup_callback()
                elif hasattr(resource, 'shutdown') and callable(resource.shutdown):
                    if asyncio.iscoroutinefunction(resource.shutdown):
                        await asyncio.wait_for(resource.shutdown(), timeout=timeout / len(self._shutdown_order))
                    else:
                        resource.shutdown()
                elif hasattr(resource, 'close') and callable(resource.close):
                    if asyncio.iscoroutinefunction(resource.close):
                        await asyncio.wait_for(resource.close(), timeout=timeout / len(self._shutdown_order))
                    else:
                        resource.close()
                        
            except Exception as e:
                # Log error but continue shutdown
                logger.error(f"Error shutting down resource {name}: {e}", file=sys.stderr)
        
        # Clear all resources
        self._resources.clear()
        self._cleanup_callbacks.clear()
        self._shutdown_order.clear()
    
    def get_resource_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered resources."""
        info = {}
        for name, resource in self._resources.items():
            info[name] = {
                "type": type(resource).__name__,
                "has_cleanup": name in self._cleanup_callbacks,
                "shutdown_priority": getattr(resource, '_shutdown_priority', 0)
            }
        return info


class ApplicationLifecycle:
    """Manages application lifecycle and graceful shutdown."""
    
    def __init__(self):
        self._resource_tracker = ResourceTracker()
        self._startup_callbacks: List[Callable[[], Any]] = []
        self._shutdown_callbacks: List[Callable[[], Any]] = []
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30.0
        self._started = False
        
        # Register signal handlers
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            try:
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, self._signal_handler)
            except (RuntimeError, NotImplementedError):
                # Fallback for environments where signal handlers aren't supported
                pass
        
        # Register atexit handler as fallback
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
    
    async def startup(self):
        """Run startup procedures."""
        if self._started:
            return
        
        try:
            # Run startup callbacks
            for callback in self._startup_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            
            self._started = True
            logger.info("Application startup completed successfully", file=sys.stderr)
            
        except Exception as e:
            logger.error(f"Startup failed: {e}", file=sys.stderr)
            await self.shutdown()
            raise
    
    async def shutdown(self, timeout: Optional[float] = None):
        """Run shutdown procedures."""
        if not self._started:
            return
        
        timeout = timeout or self._shutdown_timeout
        
        try:
            logger.info("Starting application shutdown...", file=sys.stderr)
            
            # Run shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await asyncio.wait_for(callback(), timeout=5.0)
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in shutdown callback: {e}", file=sys.stderr)
            
            # Shutdown all resources
            await self._resource_tracker.shutdown_all(timeout=timeout)
            
            self._started = False
            logger.info("Application shutdown completed", file=sys.stderr)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", file=sys.stderr)
    
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
    
    async def stop_monitoring(self):
        """Stop health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, check_interval: float):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self.perform_health_checks()
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}", file=sys.stderr)
                await asyncio.sleep(check_interval)
    
    async def perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Perform all registered health checks."""
        results = {}
        
        for name, check_func in self._health_checks.items():
            try:
                start_time = datetime.now(UTC)
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await asyncio.wait_for(check_func(), timeout=10.0)
                else:
                    result = check_func()
                
                end_time = datetime.now(UTC)
                duration = (end_time - start_time).total_seconds()
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "result": result,
                    "duration_seconds": duration,
                    "timestamp": end_time.isoformat()
                }
                
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now(UTC).isoformat()
                }
        
        self._last_check_results = results
        return results
    
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