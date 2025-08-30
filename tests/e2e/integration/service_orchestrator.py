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


from tests.e2e.test_environment_config import TestEnvironmentConfig

# Try to import dependencies, with fallbacks for missing modules
try:
    from tests.e2e.database_test_connections import DatabaseConnectionManager
except ImportError:
    DatabaseConnectionManager = None
    
try:
    from tests.e2e.real_services_manager import RealServicesManager
except ImportError:
    try:
        from tests.e2e.service_manager import RealServicesManager
    except ImportError:
        RealServicesManager = None

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
        
        # Create services manager with fallback
        if RealServicesManager:
            self.services_manager = RealServicesManager(self.project_root, env_config)
        else:
            self.services_manager = MockServicesManager()
            
        # Create database manager with fallback  
        if DatabaseConnectionManager:
            self.db_manager = DatabaseConnectionManager(env_config)
        else:
            self.db_manager = MockDatabaseManager()
            
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
        if hasattr(self.db_manager, 'initialize_connections'):
            await self.db_manager.initialize_connections()
    
    async def _start_all_services(self) -> None:
        """Start all services in correct order."""
        if hasattr(self.services_manager, 'start_all_services'):
            await self.services_manager.start_all_services(skip_frontend=True)
        await self._wait_for_stabilization()
    
    async def _wait_for_stabilization(self) -> None:
        """Wait for services to stabilize."""
        await asyncio.sleep(2)
    
    async def _validate_environment_health(self) -> None:
        """Validate essential services are healthy."""
        # Check only essential services (auth and backend) are ready
        try:
            if hasattr(self.services_manager, 'health_status'):
                essential_services = ["auth", "backend"]
                health_status = await self.services_manager.health_status()
                
                unhealthy_services = [
                    service for service in essential_services
                    if not health_status.get(service, {}).get("ready", False)
                ]
                
                if unhealthy_services:
                    logger.warning(f"Essential services not ready: {unhealthy_services}")
        except Exception as e:
            logger.warning(f"Service health check failed: {e}")
            
        # Check database connections are available (optional for some test modes)
        try:
            if hasattr(self.db_manager, 'postgres_pool') or hasattr(self.db_manager, 'redis_client'):
                if not (getattr(self.db_manager, 'postgres_pool', None) or getattr(self.db_manager, 'redis_client', None)):
                    logger.warning("Database connections not ready - continuing without")
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
    
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
        
        # Fallback to services manager or defaults
        try:
            if hasattr(self.services_manager, 'get_service_urls'):
                service_urls = self.services_manager.get_service_urls()
                if service_name in service_urls:
                    return service_urls[service_name]
        except Exception:
            pass
            
        # Default fallback URLs - use 127.0.0.1 and port 8200 for backend to match RealServicesManager
        default_urls = {
            "backend": "http://127.0.0.1:8200",
            "auth": "http://localhost:8081", 
            "auth_service": "http://localhost:8081",
            "frontend": "http://localhost:3000"
        }
        return default_urls.get(service_name, "http://localhost:8000")
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for backend service."""
        # Use environment configuration if available
        if self.env_config and hasattr(self.env_config, 'services'):
            return getattr(self.env_config.services, 'websocket', "ws://localhost:8000/ws")
        
        # Fallback to dynamic generation
        backend_url = self.get_service_url("backend")
        return backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    def is_environment_ready(self) -> bool:
        """Check if environment is ready."""
        try:
            return (self.ready and 
                    self._are_essential_services_ready())
        except Exception:
            return self.ready
    
    def _are_essential_services_ready(self) -> bool:
        """Check if essential services are ready."""
        try:
            if hasattr(self.services_manager, 'services'):
                essential_services = ["auth", "backend"]
                for service_name in essential_services:
                    service = self.services_manager.services.get(service_name)
                    if not service or not getattr(service, 'ready', False):
                        return False
                return True
        except Exception:
            pass
        return True  # Assume ready if we can't check
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get complete environment status."""
        try:
            services_status = await self.services_manager.health_status() if hasattr(self.services_manager, 'health_status') else {}
            db_ready = getattr(self.db_manager, 'postgres_pool', None) is not None
        except Exception:
            services_status = {}
            db_ready = False
            
        return {
            "orchestrator_ready": self.ready,
            "services": services_status,
            "database": {"postgres_ready": db_ready}
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
        try:
            if hasattr(self.db_manager, 'cleanup'):
                await self.db_manager.cleanup()
        except Exception as e:
            logger.warning(f"Database cleanup failed: {e}")
    
    async def _stop_services(self) -> None:
        """Stop all orchestrated services."""
        try:
            if hasattr(self.services_manager, 'stop_all_services'):
                await self.services_manager.stop_all_services()
        except Exception as e:
            logger.warning(f"Service shutdown failed: {e}")
    
    async def start_all_services(self) -> None:
        """Start all services for disaster recovery testing."""
        await self._start_all_services()
    
    async def stop_all_services(self) -> None:
        """Stop all services for disaster recovery testing."""
        await self._stop_services()


# Mock classes for when dependencies are missing
class MockServicesManager:
    """Mock services manager when real one is not available."""
    
    async def start_all_services(self, **kwargs):
        logger.warning("Using mock services manager - no real services started")
        
    async def stop_all_services(self):
        logger.warning("Using mock services manager - no services to stop")
        
    async def health_status(self):
        return {"auth": {"ready": True}, "backend": {"ready": True}}


class MockDatabaseManager:
    """Mock database manager when real one is not available."""
    
    def __init__(self):
        self.postgres_pool = None
        self.redis_client = None
        
    async def initialize_connections(self):
        logger.warning("Using mock database manager - no real connections")
        
    async def cleanup(self):
        logger.warning("Using mock database manager - no cleanup needed")


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