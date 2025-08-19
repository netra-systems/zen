"""Agent Startup E2E Test Utilities - Core Module

Core utilities for agent startup end-to-end testing.
Provides service orchestration and test coordination capabilities.
Split into focused modules to maintain 300-line architectural limit.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise 
- Business Goal: Ensure agent reliability and startup performance
- Value Impact: Prevents agent startup failures affecting customer experience
- Revenue Impact: Protects conversion rates through reliable agent interactions

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Modular design for comprehensive E2E testing
- Real service integration without mocking
"""

import asyncio
import time
import logging
from typing import Dict, Any
from dataclasses import dataclass

from .real_services_manager import create_real_services_manager
from .real_client_factory import create_real_client_factory
from .load_test_utilities import SystemResourceMonitor

logger = logging.getLogger(__name__)


@dataclass
class StartupMetrics:
    """Agent startup performance metrics tracker."""
    agent_init_time: float = 0.0
    service_ready_time: float = 0.0
    first_response_time: float = 0.0
    connection_count: int = 0
    memory_usage_mb: float = 0.0
    error_count: int = 0


class ServiceOrchestrator:
    """Orchestrates service startup and coordination for E2E tests."""
    
    def __init__(self):
        self.services_manager = create_real_services_manager()
        self.client_factory = create_real_client_factory()
        self.startup_metrics = StartupMetrics()
        self.resource_monitor = SystemResourceMonitor()
        
    async def start_all_services(self) -> Dict[str, str]:
        """Start all services and return service URLs."""
        start_time = time.time()
        await self.services_manager.start_all_services()
        self.startup_metrics.service_ready_time = time.time() - start_time
        return self.services_manager.get_service_urls()
        
    async def stop_all_services(self) -> None:
        """Stop all services and cleanup resources."""
        await self.services_manager.stop_all_services()
        await self.client_factory.cleanup()
        
    async def wait_for_service_health(self, timeout: int = 30) -> bool:
        """Wait for all services to be healthy."""
        return await self._check_services_health(timeout)
        
    async def _check_services_health(self, timeout: int) -> bool:
        """Check if all services are healthy within timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.services_manager.is_all_ready():
                return True
            await asyncio.sleep(1)
        return False


def create_startup_test_suite(
    auth_url: str = "http://localhost:8001",
    backend_url: str = "http://localhost:8000", 
    websocket_url: str = "ws://localhost:8000"
) -> Dict[str, Any]:
    """Create complete agent startup test suite.
    
    Usage Example:
        suite = create_startup_test_suite()
        
        # Start all services
        await suite["orchestrator"].start_all_services()
        
        # Create test users
        users = await suite["user_manager"].create_multiple_users(5)
        
        # Establish WebSocket connections
        connections = []
        for user in users:
            conn_id = await suite["websocket_manager"].connect_user(user)
            connections.append(conn_id)
            
        # Start performance measurement
        suite["performance_measurer"].start_measurement()
        
        # Simulate failures during testing
        await suite["failure_simulator"].simulate_database_failure(3)
        
        # Send messages and measure performance
        for conn_id in connections:
            start_time = time.time()
            await suite["websocket_manager"].send_message(conn_id, {"test": "message"})
            response = await suite["websocket_manager"].wait_for_response(conn_id)
            response_time = time.time() - start_time
            suite["performance_measurer"].record_response_time(response_time)
            
        # Get performance summary
        summary = suite["performance_measurer"].get_performance_summary()
        
        # Cleanup
        await suite["websocket_manager"].disconnect_all()
        await suite["user_manager"].cleanup_users()
        await suite["orchestrator"].stop_all_services()
    """
    from .agent_startup_user_manager import UserManager
    from .agent_startup_websocket_manager import WebSocketManager
    from .agent_startup_performance_measurer import PerformanceMeasurer
    from .agent_startup_failure_simulator import FailureSimulator
    
    return {
        "orchestrator": ServiceOrchestrator(),
        "user_manager": UserManager(auth_url),
        "websocket_manager": WebSocketManager(websocket_url),
        "performance_measurer": PerformanceMeasurer(),
        "failure_simulator": FailureSimulator()
    }


# Export key classes and functions for easy importing
__all__ = [
    'ServiceOrchestrator',
    'StartupMetrics', 
    'create_startup_test_suite'
]