"""
SSOT Docker Test Manager

This module provides the Single Source of Truth for Docker test management functions
that are referenced from test_framework.ssot.docker_test_manager imports.

Business Value: Platform/Internal - Test Infrastructure Stability
- Eliminates broken imports causing test collection failures
- Provides SSOT compatibility layer for legacy imports
- Ensures seamless migration to unified Docker utilities

CRITICAL: This module serves as a compatibility bridge while tests migrate to
the main SSOT Docker utilities in test_framework.ssot.docker
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import SSOT Docker utilities
from test_framework.ssot.docker import (
    DockerTestUtility,
    DockerTestEnvironmentType,
    DockerTestMetrics,
    get_docker_test_utility
)

logger = logging.getLogger(__name__)


async def ensure_services_running(
    services: List[str], 
    timeout: int = 60,
    environment_type: DockerTestEnvironmentType = DockerTestEnvironmentType.ISOLATED
) -> Dict[str, Any]:
    """
    Ensure specified Docker services are running for tests.
    
    This function provides compatibility for legacy imports while delegating
    to the SSOT DockerTestUtility implementation.
    
    Args:
        services: List of service names to ensure are running
        timeout: Maximum time to wait for services to start
        environment_type: Type of Docker test environment to use
        
    Returns:
        Dictionary with service status information
        
    Raises:
        RuntimeError: If services fail to start within timeout
    """
    logger.info(f"Ensuring services are running: {services}")
    
    try:
        # Use SSOT Docker utility for actual implementation
        async with DockerTestUtility(environment_type=environment_type) as docker:
            # Start the requested services
            result = await docker.start_services(services, timeout=timeout)
            
            if not result.success:
                raise RuntimeError(f"Failed to start services: {result.error_message}")
            
            # Get service status information
            service_urls = docker.get_all_service_urls()
            
            return {
                "success": True,
                "services": services,
                "service_urls": service_urls,
                "startup_time": result.startup_time,
                "message": f"Successfully started {len(services)} services"
            }
            
    except Exception as e:
        logger.error(f"Failed to ensure services running: {e}")
        raise RuntimeError(f"Service startup failed: {str(e)}") from e


class DockerTestManager:
    """
    Compatibility class for legacy test_framework.ssot.docker_test_manager imports.
    
    This class provides a compatibility layer for existing imports while
    encouraging migration to the SSOT DockerTestUtility.
    
    DEPRECATED: New tests should use test_framework.ssot.docker.DockerTestUtility directly.
    """
    
    def __init__(self, environment_type: DockerTestEnvironmentType = DockerTestEnvironmentType.ISOLATED):
        """Initialize Docker test manager with SSOT utilities."""
        self._environment_type = environment_type
        self._docker_utility = None
        logger.warning(
            "DockerTestManager is deprecated. Use test_framework.ssot.docker.DockerTestUtility directly."
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._docker_utility = DockerTestUtility(environment_type=self._environment_type)
        return await self._docker_utility.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._docker_utility:
            return await self._docker_utility.__aexit__(exc_type, exc_val, exc_tb)
    
    async def ensure_services_running(self, services: List[str], timeout: int = 60) -> Dict[str, Any]:
        """Delegate to the standalone ensure_services_running function."""
        return await ensure_services_running(services, timeout, self._environment_type)


# Export functions for compatibility
__all__ = [
    "ensure_services_running",
    "DockerTestManager",
    "DockerTestEnvironmentType"
]