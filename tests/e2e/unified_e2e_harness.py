"""
Unified E2E Test Harness - Complete Service Orchestration
Business Value: $500K+ MRR protection via comprehensive E2E validation
Main harness composing service orchestration and user journey execution.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
import os
from pathlib import Path
# Ensure absolute imports work
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tests.e2e.service_orchestrator import E2EServiceOrchestrator
from tests.e2e.user_journey_executor import TestUser, UserJourneyExecutor
from tests.e2e.config import (
    TestEnvironmentConfig,
    TestEnvironmentType,
    get_test_environment_config,
)

logger = logging.getLogger(__name__)


@dataclass
class E2ETestSession:
    """E2E test session container."""
    session_id: str
    test_database_name: str
    cleanup_tasks: List[callable]


class UnifiedE2ETestHarness:
    """
    Unified E2E Test Harness for complete service orchestration.
    Manages Auth, Backend, Frontend with health checks and cleanup.
    Supports test, dev, and staging environments with automatic detection.
    """
    
    def __init__(self, 
                 project_root: Optional[Path] = None,
                 environment: Optional[TestEnvironmentType] = None):
        """Initialize E2E test harness.
        
        Args:
            project_root: Optional project root path
            environment: Optional environment override (test, dev, staging)
        """
        # Setup environment configuration first
        self.env_config = get_test_environment_config(environment=environment)
        self.orchestrator = E2EServiceOrchestrator(project_root, self.env_config)
        self.journey_executor = UserJourneyExecutor(self.orchestrator)
        self.session = self._create_test_session()
        self.ready = False
        
        logger.info(f"E2E Harness initialized for {self.env_config.environment_type.value} environment")
    
    def _create_test_session(self) -> E2ETestSession:
        """Create new test session."""
        return E2ETestSession(
            session_id=str(uuid.uuid4()),
            test_database_name=f"test_e2e_{uuid.uuid4().hex[:8]}",
            cleanup_tasks=[]
        )
    
    @asynccontextmanager
    async def test_environment(self):
        """Context manager for complete test environment."""
        try:
            await self.start_test_environment()
            yield self
        finally:
            await self.cleanup_test_environment()
    
    async def test_start_test_environment(self) -> None:
        """Start complete test environment."""
        logger.info("Starting unified E2E test environment")
        
        await self.orchestrator.test_start_test_environment(
            self.session.test_database_name
        )
        
        self.ready = True
        logger.info("E2E test environment ready")
    
    async def create_test_user(self, 
                             email: Optional[str] = None,
                             password: str = "testpass123") -> TestUser:
        """Create and register test user."""
        return await self.journey_executor.create_test_user(email, password)
    
    def create_test_tokens(self, user_id: str) -> Dict[str, str]:
        """Create test tokens for user ID."""
        return {
            "access_token": f"test-token-{user_id[:16]}",
            "refresh_token": f"refresh-{user_id[:16]}",
            "expires_in": 3600
        }
    
    async def create_websocket_connection(self, user: TestUser):
        """Create authenticated WebSocket connection."""
        return await self.journey_executor.create_websocket_connection(user)
    
    async def simulate_user_journey(self, user: TestUser) -> Dict[str, Any]:
        """Simulate complete user journey flow."""
        return await self.journey_executor.simulate_user_journey(user)
    
    async def run_concurrent_user_test(self, user_count: int = 3) -> List[Dict[str, Any]]:
        """Run concurrent user journey tests."""
        return await self.journey_executor.run_concurrent_user_test(user_count)
    
    def get_service_url(self, service_name: str) -> str:
        """Get URL for specific service."""
        # Use environment-aware service URLs
        service_urls_map = {
            "backend": self.env_config.services.backend,
            "auth": self.env_config.services.auth,
            "auth_service": self.env_config.services.auth,  # Alias for backward compatibility
            "frontend": self.env_config.services.frontend
        }
        
        if service_name in service_urls_map:
            return service_urls_map[service_name]
        
        # Fallback to orchestrator for other services
        return self.orchestrator.get_service_url(service_name)
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for backend service."""
        # Derive WebSocket URL from backend URL
        backend_url = self.env_config.services.backend
        if backend_url.startswith("https://"):
            return backend_url.replace("https://", "wss://") + "/ws"
        elif backend_url.startswith("http://"):
            return backend_url.replace("http://", "ws://") + "/ws"
        else:
            # Default to localhost WebSocket URL
            return "ws://localhost:8000/ws"
    
    def is_environment_ready(self) -> bool:
        """Check if test environment is ready."""
        return self.ready and self.orchestrator.is_environment_ready()
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get complete environment status."""
        status = await self.orchestrator.get_environment_status()
        status.update({
            "harness_ready": self.ready,
            "environment": self.env_config.environment.value,
            "session_id": self.session.session_id,
            "active_users": len(self.journey_executor.test_users),
            "active_connections": len(self.journey_executor.websocket_connections),
            "service_urls": {
                "backend": self.env_config.services.backend,
                "auth": self.env_config.services.auth,
                "frontend": self.env_config.services.frontend,
                "websocket": self.env_config.services.websocket
            },
            "database_url": self.env_config.database.url
        })
        return status
    
    async def test_cleanup_test_environment(self) -> None:
        """Cleanup complete test environment."""
        logger.info("Cleaning up E2E test environment")
        
        await self.journey_executor.cleanup_users_and_connections()
        await self.orchestrator.test_stop_test_environment(
            self.session.test_database_name
        )
        
        # Run custom cleanup tasks
        for cleanup_task in reversed(self.session.cleanup_tasks):
            try:
                await cleanup_task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
        
        self.ready = False
        logger.info("E2E test environment cleaned up")
    
    def add_cleanup_task(self, cleanup_fn: callable) -> None:
        """Add custom cleanup task."""
        self.session.cleanup_tasks.append(cleanup_fn)


# Factory functions for easy instantiation
def create_e2e_harness(project_root: Optional[Path] = None, 
                      environment: Optional[TestEnvironmentType] = None) -> UnifiedE2ETestHarness:
    """Create unified E2E test harness instance.
    
    Args:
        project_root: Optional project root path
        environment: Optional environment override (test, dev, staging)
        
    Returns:
        UnifiedE2ETestHarness instance configured for the specified environment
    """
    return UnifiedE2ETestHarness(project_root, environment)


async def quick_e2e_test(environment: Optional[TestEnvironmentType] = None) -> Dict[str, Any]:
    """Quick E2E test for validation.
    
    Args:
        environment: Optional environment override
        
    Returns:
        Test results dictionary
    """
    async with create_e2e_harness(environment=environment).test_environment() as harness:
        user = await harness.create_test_user()
        return await harness.simulate_user_journey(user)
