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
from .service_manager import ServiceManager, TestDataSeeder, HealthMonitor

logger = logging.getLogger(__name__)


class UnifiedTestHarnessComplete(UnifiedTestHarness):
    """
    Complete implementation of the Unified Test Harness.
    Extends the base class with all required functionality.
    """
    
    def __init__(self, test_name: str = "unified_test"):
        """Initialize complete test harness with all managers."""
        super().__init__(test_name)
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
        logger.info("Test harness shutdown complete")


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