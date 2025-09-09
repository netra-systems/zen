"""
Service Health Monitoring for Real Services Manager
Part of the real services testing infrastructure.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tests.e2e.real_services_manager import RealServicesManager, ServiceProcess

logger = logging.getLogger(__name__)


async def check_service_health(url: str, timeout: float = 5.0) -> bool:
    """
    Simple health check for a service endpoint.
    
    Args:
        url: Health check URL
        timeout: Request timeout in seconds
    
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            return response.status_code == 200
    except Exception as e:
        logger.debug(f"Health check failed for {url}: {e}")
        return False


class ServiceHealthMonitor:
    """Monitor service health during tests."""
    
    def __init__(self, manager):
        """Initialize health monitor."""
        self.manager = manager
        self.monitoring = False
        self.check_interval = 5
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            await self._wait_for_task_completion()
        logger.info("Stopped health monitoring")
    
    async def _wait_for_task_completion(self) -> None:
        """Wait for monitor task to complete."""
        try:
            await self.monitor_task
        except asyncio.CancelledError:
            pass
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            await self._check_all_services()
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self) -> None:
        """Check health of all services."""
        for name, service in self.manager.services.items():
            if service.ready and not await self._is_service_healthy(service):
                logger.warning(f"Service {name} appears unhealthy")
                service.ready = False
    
    async def _is_service_healthy(self, service) -> bool:
        """Check if individual service is healthy."""
        return await self.manager._check_service_health(service)


class RealServicesContext:
    """Context manager for real services in tests."""
    
    def __init__(self, project_root=None):
        """Initialize context manager."""
        from tests.e2e.real_services_manager import RealServicesManager
        self.manager = RealServicesManager(project_root)
        self.monitor = ServiceHealthMonitor(self.manager)
    
    async def __aenter__(self):
        """Start services when entering context."""
        await self.manager.start_all_services()
        await self.monitor.start_monitoring()
        return self.manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop services when exiting context."""
        await self.monitor.stop_monitoring()
        await self.manager.stop_all_services()
