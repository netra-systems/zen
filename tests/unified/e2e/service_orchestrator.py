"""
Service Orchestrator - E2E Service Management
Business Value: Reliable service startup for E2E testing
Manages service lifecycle, health checks, and coordination.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unified.real_services_manager import RealServicesManager
from tests.unified.database_test_connections import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class E2EServiceOrchestrator:
    """Orchestrates all services for E2E testing."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize service orchestrator."""
        self.project_root = project_root or self._detect_project_root()
        self.services_manager = RealServicesManager(self.project_root)
        self.db_manager = DatabaseConnectionManager()
        self.ready = False
    
    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "app").exists():
                return current
            current = current.parent
        raise RuntimeError("Cannot detect project root")
    
    async def start_test_environment(self, db_name: str) -> None:
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
        await self.services_manager.start_all_services()
        await self._wait_for_stabilization()
    
    async def _wait_for_stabilization(self) -> None:
        """Wait for services to stabilize."""
        await asyncio.sleep(2)
    
    async def _validate_environment_health(self) -> None:
        """Validate all services are healthy."""
        if not self.services_manager.is_all_ready():
            raise RuntimeError("Services not ready")
        # Check database connections are available
        if not (self.db_manager.postgres_pool or self.db_manager.redis_client):
            raise RuntimeError("Database connections not ready")
    
    def get_service_url(self, service_name: str) -> str:
        """Get URL for specific service."""
        service_urls = self.services_manager.get_service_urls()
        if service_name not in service_urls:
            raise ValueError(f"Service {service_name} not available")
        return service_urls[service_name]
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for backend service."""
        backend_url = self.get_service_url("backend")
        return backend_url.replace("http://", "ws://") + "/ws"
    
    def is_environment_ready(self) -> bool:
        """Check if environment is ready."""
        return (self.ready and 
                self.services_manager.is_all_ready() and
                (self.db_manager.postgres_pool is not None))
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get complete environment status."""
        return {
            "orchestrator_ready": self.ready,
            "services": await self.services_manager.health_status(),
            "database": {"postgres_ready": self.db_manager.postgres_pool is not None}
        }
    
    async def stop_test_environment(self, db_name: str) -> None:
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


def create_service_orchestrator(project_root: Optional[Path] = None) -> E2EServiceOrchestrator:
    """Create service orchestrator instance."""
    return E2EServiceOrchestrator(project_root)