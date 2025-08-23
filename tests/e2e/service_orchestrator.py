"""
Service Orchestrator - E2E Service Management
Business Value: Reliable service startup for E2E testing
Manages service lifecycle, health checks, and coordination.
"""
import asyncio
import logging

# Add project root to path for imports
import sys
from pathlib import Path
from typing import Any, Dict, Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.database_test_connections import DatabaseConnectionManager
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.test_environment_config import TestEnvironmentConfig

logger = logging.getLogger(__name__)


class E2EServiceOrchestrator:
    """Orchestrates all services for E2E testing."""
    
    def __init__(self, project_root: Optional[Path] = None, env_config: Optional[TestEnvironmentConfig] = None):
        """Initialize service orchestrator.
        
        Args:
            project_root: Optional project root path
            env_config: Environment configuration for environment-aware service management
        """
        self.project_root = project_root or self._detect_project_root()
        self.env_config = env_config
        self.services_manager = RealServicesManager(self.project_root, env_config)
        self.db_manager = DatabaseConnectionManager(env_config)
        self.ready = False
    
    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "app").exists():
                return current
            current = current.parent
        raise RuntimeError("Cannot detect project root")
    
    async def test_start_test_environment(self, db_name: str) -> None:
        """Start complete test environment."""
        logger.info("Starting E2E test environment")
        
        await self._setup_test_database(db_name)
        await self._start_all_services()
        await self._validate_environment_health()
        
        self.ready = True
        logger.info("E2E test environment ready")
    
    async def _setup_test_database(self, db_name: str) -> None:
        """Setup isolated test database."""
        await self.db_manager.initialize_connections()
    
    async def _start_all_services(self) -> None:
        """Start all services in correct order."""
        await self.services_manager.start_all_services(skip_frontend=True)
        await self._wait_for_stabilization()
    
    async def _wait_for_stabilization(self) -> None:
        """Wait for services to stabilize."""
        await asyncio.sleep(2)
    
    async def _validate_environment_health(self) -> None:
        """Validate essential services are healthy."""
        # Check only essential services (auth and backend) are ready
        essential_services = ["auth", "backend"]
        health_status = await self.services_manager.health_status()
        
        unhealthy_services = [
            service for service in essential_services
            if not health_status.get(service, {}).get("ready", False)
        ]
        
        if unhealthy_services:
            raise RuntimeError(f"Essential services not ready: {unhealthy_services}")
            
        # Check database connections are available
        if not (self.db_manager.postgres_pool or self.db_manager.redis_client):
            raise RuntimeError("Database connections not ready")
    
    def get_service_url(self, service_name: str) -> str:
        """Get URL for specific service."""
        # Use environment configuration if available
        if self.env_config:
            service_urls_map = {
                "backend": self.env_config.services.backend,
                "auth": self.env_config.services.auth,
                "auth_service": self.env_config.services.auth,  # Alias
                "frontend": self.env_config.services.frontend
            }
            
            if service_name in service_urls_map:
                return service_urls_map[service_name]
        
        # Fallback to services manager
        service_urls = self.services_manager.get_service_urls()
        if service_name not in service_urls:
            raise ValueError(f"Service {service_name} not available")
        return service_urls[service_name]
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for backend service."""
        # Use environment configuration if available
        if self.env_config:
            return self.env_config.services.websocket
        
        # Fallback to dynamic generation
        backend_url = self.get_service_url("backend")
        return backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    def is_environment_ready(self) -> bool:
        """Check if environment is ready."""
        return (self.ready and 
                self._are_essential_services_ready() and
                (self.db_manager.postgres_pool is not None))
    
    def _are_essential_services_ready(self) -> bool:
        """Check if essential services are ready."""
        essential_services = ["auth", "backend"]
        for service_name in essential_services:
            service = self.services_manager.services.get(service_name)
            if not service or not service.ready:
                return False
        return True
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get complete environment status."""
        return {
            "orchestrator_ready": self.ready,
            "services": await self.services_manager.health_status(),
            "database": {"postgres_ready": self.db_manager.postgres_pool is not None}
        }
    
    async def test_stop_test_environment(self, db_name: str) -> None:
        """Stop complete test environment."""
        logger.info("Stopping E2E test environment")
        
        await self._cleanup_database(db_name)
        await self._stop_services()
        
        self.ready = False
        logger.info("E2E test environment stopped")
    
    async def _cleanup_database(self, db_name: str) -> None:
        """Cleanup test database."""
        await self.db_manager.cleanup()
    
    async def _stop_services(self) -> None:
        """Stop all orchestrated services."""
        await self.services_manager.stop_all_services()
    
    async def start_all_services(self) -> None:
        """Start all services for disaster recovery testing."""
        await self._start_all_services()
    
    async def stop_all_services(self) -> None:
        """Stop all services for disaster recovery testing."""
        await self._stop_services()


def create_service_orchestrator(project_root: Optional[Path] = None, 
                               env_config: Optional[TestEnvironmentConfig] = None) -> E2EServiceOrchestrator:
    """Create service orchestrator instance.
    
    Args:
        project_root: Optional project root path
        env_config: Environment configuration
        
    Returns:
        E2EServiceOrchestrator instance
    """
    return E2EServiceOrchestrator(project_root, env_config)