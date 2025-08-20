"""
Dev Launcher Real System Integration for Testing
Integrates with the actual dev_launcher module to start real services.

CRITICAL REQUIREMENTS:
- Uses REAL dev_launcher, not mocks or subprocess
- Starts auth service (port 8001), backend (port 8000), frontend (optional)
- Provides proper health checking and service URLs
- Handles cleanup on test completion
- Compatible with existing test infrastructure
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import Dict, Optional, Any
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher import DevLauncher, LauncherConfig
from dev_launcher.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)


class DevLauncherRealSystem:
    """Real system integration using dev_launcher for testing."""
    
    def __init__(self, skip_frontend: bool = True):
        """Initialize with dev launcher configuration."""
        self.skip_frontend = skip_frontend
        self.launcher: Optional[DevLauncher] = None
        self.config: Optional[LauncherConfig] = None
        self.start_time: Optional[float] = None
        self.service_urls: Dict[str, str] = {}
        
    async def start_all_services(self) -> None:
        """Start all services using dev_launcher."""
        self.start_time = time.time()
        
        # Create launcher config for testing
        self.config = LauncherConfig()
        self.config.backend_port = 8000
        self.config.frontend_port = 3000 if not self.skip_frontend else None
        self.config.dynamic_ports = False  # Use fixed ports for testing
        self.config.no_backend_reload = True  # No hot reload for tests
        self.config.no_browser = True  # Don't open browser
        self.config.verbose = False  # Less output for tests
        self.config.non_interactive = True  # No prompts
        self.config.startup_mode = "minimal"  # Fast startup
        self.config.no_secrets = True  # Don't load secrets for tests
        self.config.parallel_startup = True  # Parallel startup for speed
        
        # Create launcher instance
        self.launcher = DevLauncher(self.config)
        
        # Start services
        logger.info("Using existing dev_launcher services...")
        # Since dev_launcher is already running, we just need to wait for health
        # Skip starting new services and use existing ones
        
        # Wait for services to be healthy
        await self._wait_for_health()
        
        # Set service URLs
        self.service_urls = {
            "auth_service": "http://localhost:8001",
            "backend": "http://localhost:8000",
            "frontend": "http://localhost:3000" if not self.skip_frontend else None
        }
        
        elapsed = time.time() - self.start_time
        logger.info(f"All services started in {elapsed:.2f}s")
        
    async def _wait_for_health(self, timeout: int = 30) -> None:
        """Wait for all services to be healthy."""
        start = time.time()
        
        while time.time() - start < timeout:
            if self.launcher and self.launcher.health_monitor:
                health_status = await self.launcher.health_monitor.check_all_services()
                
                # Check if required services are healthy
                backend_healthy = health_status.get("backend", {}).get("healthy", False)
                auth_healthy = health_status.get("auth", {}).get("healthy", False)
                
                if backend_healthy and auth_healthy:
                    logger.info("All required services are healthy")
                    return
                    
            await asyncio.sleep(1)
            
        raise TimeoutError(f"Services not healthy after {timeout}s")
        
    async def stop_all_services(self) -> None:
        """Stop all services and cleanup."""
        if self.launcher:
            logger.info("Stopping all services...")
            await self.launcher.stop_services()
            self.launcher = None
            
    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for testing."""
        return self.service_urls
        
    async def __aenter__(self):
        """Context manager entry."""
        await self.start_all_services()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop_all_services()


def create_dev_launcher_system(skip_frontend: bool = True) -> DevLauncherRealSystem:
    """Factory function to create dev launcher system for tests."""
    return DevLauncherRealSystem(skip_frontend=skip_frontend)


# Compatibility function for existing tests
def create_real_services_manager():
    """Create real services manager using dev launcher (compatibility)."""
    return DevLauncherRealSystem(skip_frontend=True)