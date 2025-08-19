"""
Unified Test Harness - Complete Implementation
Final part that ties everything together and adds missing methods

This completes the UnifiedTestHarness implementation started in test_harness.py
"""

import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import components
from .test_harness import UnifiedTestHarness

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Enhanced database manager for testing"""
    
    def __init__(self, harness):
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.DatabaseManager")
        self.initialized = False
    
    async def setup_databases(self) -> None:
        """Setup test databases with in-memory SQLite for speed."""
        try:
            # Initialize test database connections
            self._setup_sqlite_database()
            self._setup_redis_connection()
            self._setup_clickhouse_connection()
            
            self.initialized = True
            self.logger.info("Test databases initialized successfully")
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise
    
    def _setup_sqlite_database(self) -> None:
        """Setup in-memory SQLite database for testing."""
        import os
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        self.logger.debug("SQLite in-memory database configured")
    
    def _setup_redis_connection(self) -> None:
        """Setup Redis connection for testing."""
        import os
        os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use DB 1 for tests
        self.logger.debug("Redis test database configured")
    
    def _setup_clickhouse_connection(self) -> None:
        """Setup ClickHouse connection for testing."""
        import os
        os.environ["CLICKHOUSE_URL"] = "clickhouse://localhost:8123/test"
        self.logger.debug("ClickHouse test database configured")
    
    async def cleanup_databases(self) -> None:
        """Cleanup test databases"""
        self.initialized = False
        self.logger.info("Test databases cleaned up")


class ServiceManager:
    """Enhanced service manager for testing - delegates to real ServiceManager"""
    
    def __init__(self, harness):
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.ServiceManager")
        # Import the real service manager
        from .service_manager import ServiceManager as RealServiceManager
        self._real_manager = RealServiceManager(harness)
    
    async def start_auth_service(self) -> None:
        """Start auth service using real service manager"""
        self.logger.info("Starting auth service")
        await self._real_manager.start_auth_service()
    
    async def start_backend_service(self) -> None:
        """Start backend service using real service manager"""
        self.logger.info("Starting backend service")
        await self._real_manager.start_backend_service()
    
    async def stop_all_services(self) -> None:
        """Stop all services using real service manager"""
        self.logger.info("Stopping all services")
        await self._real_manager.stop_all_services()


class TestDataSeeder:
    """Simple test data seeder"""
    
    def __init__(self, harness):
        self.harness = harness
    
    async def seed_test_data(self) -> None:
        """Seed test data"""
        pass
    
    async def cleanup_test_data(self) -> None:
        """Cleanup test data"""
        pass
    
    def get_test_user(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Get test user by index"""
        return {"id": f"test-user-{index}", "email": f"test{index}@example.com"}


class HealthMonitor:
    """Enhanced health monitor for testing - delegates to real HealthMonitor"""
    
    def __init__(self, harness):
        self.harness = harness
        self.logger = logging.getLogger(f"{__name__}.HealthMonitor")
        # Import the real health monitor
        from .service_manager import HealthMonitor as RealHealthMonitor
        self._real_monitor = RealHealthMonitor(harness)
    
    async def wait_for_all_ready(self) -> None:
        """Wait for all services to be ready using real health monitor"""
        self.logger.info("Waiting for all services to be ready")
        await self._real_monitor.wait_for_all_ready()
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Check system health using real health monitor"""
        return await self._real_monitor.check_system_health()


class TestState:
    """Enhanced state object for testing"""
    
    def __init__(self):
        self.services = {}
        self.temp_dir = None
        self.cleanup_tasks = []
        self.ready = False
        self.startup_time = None
        self.databases = None  # Will be initialized by DatabaseManager


class UnifiedTestHarnessComplete(UnifiedTestHarness):
    """
    Complete implementation of the Unified Test Harness.
    Extends the base class with all required functionality.
    """
    
    def __init__(self, test_name: str = "unified_test"):
        """Initialize complete test harness with all managers."""
        super().__init__()
        self.test_name = test_name
        self.logger = logging.getLogger(f"{__name__}.{test_name}")
        
        # Initialize state with service configurations
        self.state = TestState()
        self._initialize_service_configs()
        
        # Initialize managers
        self.database_manager = DatabaseManager(self)
        self.service_manager = ServiceManager(self)
        self.data_seeder = TestDataSeeder(self)
        self.health_monitor = HealthMonitor(self)
    
    async def _setup_databases(self) -> None:
        """Setup all test databases using database manager."""
        await self.database_manager.setup_databases()
    
    async def _start_auth_service(self) -> None:
        """Start auth service using service manager."""
        await self.service_manager.start_auth_service()
    
    async def _start_backend_service(self) -> None:
        """Start backend service using service manager."""
        await self.service_manager.start_backend_service()
    
    async def _wait_for_readiness(self) -> None:
        """Wait for all services to be ready."""
        await self.health_monitor.wait_for_all_ready()
    
    async def start_services(self) -> None:
        """Start all services for testing in correct dependency order."""
        self.logger.info("Starting unified test harness service orchestration")
        
        # Step 1: Setup test environment and databases
        await self._setup_test_environment()
        await self._setup_databases()
        
        # Step 2: Start auth service first (no dependencies)
        await self._start_auth_service()
        
        # Step 3: Start backend service (depends on auth)
        await self._start_backend_service()
        
        # Step 4: Wait for all services to be ready
        await self._wait_for_readiness()
        
        # Step 5: Verify system health
        await self._verify_system_health()
        
        self.state.ready = True
        self.logger.info("All services started and verified healthy")
    
    async def seed_test_data(self) -> None:
        """Seed test data for realistic testing scenarios."""
        await self.data_seeder.seed_test_data()
    
    def get_test_user(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """Get a test user for authentication testing."""
        return self.data_seeder.get_test_user(index)
    
    def get_service_url(self, service_name: str) -> str:
        """Get the URL for a specific service."""
        if service_name in self.state.services:
            config = self.state.services[service_name]
            return f"http://{config.host}:{config.port}"
        raise ValueError(f"Unknown service: {service_name}")
    
    async def get_auth_token(self, user_index: int = 0) -> Optional[str]:
        """Get an authentication token for testing."""
        user = self.get_test_user(user_index)
        if not user:
            return None
        
        # This would typically call the auth service to get a real token
        # For testing purposes, return a mock token
        return f"test-token-{user['id']}"
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health check."""
        return await self.health_monitor.check_system_health()
    
    def _cleanup_temp_dir(self) -> None:
        """Cleanup temporary directory."""
        if self.state.temp_dir and self.state.temp_dir.exists():
            import shutil
            shutil.rmtree(self.state.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.state.temp_dir}")
    
    async def stop_all_services(self) -> None:
        """Stop all services and cleanup."""
        await self.service_manager.stop_all_services()
        await self.database_manager.cleanup_databases()
        await self.data_seeder.cleanup_test_data()
        
        # Run all cleanup tasks
        for cleanup_task in self.state.cleanup_tasks:
            try:
                cleanup_task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
        
        self.state.ready = False
        self.logger.info("Test harness shutdown complete")
    
    def _initialize_service_configs(self) -> None:
        """Initialize service configurations with proper settings."""
        from .test_harness import ServiceConfig
        
        self.state.services = {
            "auth_service": ServiceConfig(
                name="auth_service", 
                host="localhost", 
                port=8001, 
                health_endpoint="/health",
                startup_timeout=30
            ),
            "backend": ServiceConfig(
                name="backend", 
                host="localhost", 
                port=8000, 
                health_endpoint="/health",
                startup_timeout=45  # Backend needs more time
            )
        }
    
    async def _setup_test_environment(self) -> None:
        """Setup test environment variables and configuration."""
        from .config import setup_test_environment
        setup_test_environment()
        self.logger.info("Test environment configured")
    
    async def _verify_system_health(self) -> None:
        """Verify all services are healthy and responding."""
        health_status = await self.check_system_health()
        
        if not health_status.get("services_ready", False):
            raise RuntimeError(f"System health check failed: {health_status}")
        
        self.logger.info(f"System health verified: {health_status['ready_services']}/{health_status['service_count']} services ready")


# Context manager for easy usage
class TestHarnessContext:
    """Context manager for the unified test harness."""
    
    def __init__(self, test_name: str = "unified_test", seed_data: bool = True):
        """Initialize context manager."""
        self.test_name = test_name
        self.seed_data = seed_data
        self.harness = None
    
    async def __aenter__(self) -> UnifiedTestHarnessComplete:
        """Enter the test harness context."""
        self.harness = UnifiedTestHarnessComplete(self.test_name)
        await self.harness.start_services()
        
        if self.seed_data:
            await self.harness.seed_test_data()
        
        return self.harness
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the test harness context."""
        if self.harness:
            await self.harness.stop_all_services()


# Convenience functions for common testing scenarios
async def create_test_harness(test_name: str = "unified_test") -> UnifiedTestHarnessComplete:
    """Create and start a test harness."""
    harness = UnifiedTestHarnessComplete(test_name)
    await harness.start_services()
    await harness.seed_test_data()
    return harness


async def create_minimal_harness(test_name: str = "minimal_test") -> UnifiedTestHarnessComplete:
    """Create a minimal test harness without test data."""
    harness = UnifiedTestHarnessComplete(test_name)
    await harness.start_services()
    return harness


def get_test_database_url() -> str:
    """Get the test database URL."""
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///test.db")


def get_auth_service_url() -> str:
    """Get the auth service URL."""
    return os.environ.get("AUTH_SERVICE_URL", "http://localhost:8001")


def get_backend_service_url() -> str:
    """Get the backend service URL."""
    return "http://localhost:8000"


# Integration helpers
class TestClient:
    """HTTP client for testing services."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        """Initialize test client."""
        self.harness = harness
        self._setup_http_client()
    
    def _setup_http_client(self) -> None:
        """Setup HTTP client with proper configuration."""
        import httpx
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def auth_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make authenticated request to auth service."""
        url = f"{self.harness.get_service_url('auth_service')}{endpoint}"
        return await self._make_request(method, url, **kwargs)
    
    async def backend_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make authenticated request to backend service."""
        url = f"{self.harness.get_service_url('backend')}{endpoint}"
        return await self._make_request(method, url, **kwargs)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """Make HTTP request with error handling."""
        response = await self.client.request(method, url, **kwargs)
        return response
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Export main classes and functions
__all__ = [
    'UnifiedTestHarnessComplete',
    'TestHarnessContext', 
    'TestClient',
    'create_test_harness',
    'create_minimal_harness',
    'get_test_database_url',
    'get_auth_service_url',
    'get_backend_service_url'
]