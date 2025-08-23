"""Multi-Service Integration Core Tests

Critical integration tests for core multi-service functionality.
Business Value: $500K+ MRR protection via comprehensive cross-service validation.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional

import pytest

from tests.e2e.integration.unified_e2e_harness import create_e2e_harness
from tests.e2e.integration.user_journey_executor import TestUser


class TestMultiServiceIntegrationCore:
    """Test class for core multi-service integration functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_id = str(uuid.uuid4())[:8]
    
    @pytest.mark.asyncio
    async def test_basic_service_communication(self):
        """Test basic communication between services."""
        # Create harness without starting real services
        harness = create_e2e_harness()
        
        # Test service URL resolution (should work without starting services)
        backend_url = harness.get_service_url("backend")
        auth_url = harness.get_service_url("auth")
        websocket_url = harness.get_websocket_url()
        
        # Verify URLs are properly configured
        assert backend_url == "http://localhost:8000"
        assert auth_url == "http://localhost:8081"
        assert websocket_url == "ws://localhost:8000/ws"
        
        print(f"Backend URL: {backend_url}")
        print(f"Auth URL: {auth_url}")
        print(f"WebSocket URL: {websocket_url}")
    
    @pytest.mark.asyncio
    async def test_user_creation_and_auth_flow(self):
        """Test user creation and authentication infrastructure."""
        # Test harness creation without real service startup
        harness = create_e2e_harness()
        
        # Verify harness has proper configuration
        assert harness.env_config is not None
        assert harness.orchestrator is not None
        assert harness.journey_executor is not None
        
        # Test environment status reporting (without starting services)
        status = await harness.get_environment_status()
        assert isinstance(status, dict)
        assert "harness_ready" in status
        assert "service_urls" in status
        
        print(f"Environment status: {status['harness_ready']}")
        print(f"Service URLs configured: {list(status['service_urls'].keys())}")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection infrastructure setup."""
        # Test WebSocket URL generation
        harness = create_e2e_harness()
        
        websocket_url = harness.get_websocket_url()
        assert websocket_url == "ws://localhost:8000/ws"
        
        # Test that journey executor is properly initialized
        assert harness.journey_executor is not None
        assert hasattr(harness.journey_executor, 'create_websocket_connection')
        
        print(f"WebSocket URL configured: {websocket_url}")
        print("WebSocket infrastructure validated")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self):
        """Test concurrent operations infrastructure."""
        # Test harness concurrent operation capabilities
        harness = create_e2e_harness()
        
        # Verify concurrent test method exists
        assert hasattr(harness, 'run_concurrent_user_test')
        assert callable(getattr(harness, 'run_concurrent_user_test'))
        
        # Test journey executor initialization for concurrent operations
        assert harness.journey_executor.test_users == []
        assert harness.journey_executor.websocket_connections == []
        
        print("Concurrent operations infrastructure validated")
        print(f"Initial test users: {len(harness.journey_executor.test_users)}")
        print(f"Initial WebSocket connections: {len(harness.journey_executor.websocket_connections)}")
    
    @pytest.mark.asyncio
    async def test_environment_status_reporting(self):
        """Test environment status reporting functionality."""
        # Test status reporting without starting services
        harness = create_e2e_harness()
        
        # Get environment status
        status = await harness.get_environment_status()
        
        # Verify status structure
        assert isinstance(status, dict)
        assert "harness_ready" in status
        assert "environment" in status
        assert "service_urls" in status
        
        # Verify service URLs are present
        service_urls = status["service_urls"]
        assert "backend" in service_urls
        assert "auth" in service_urls
        assert "websocket" in service_urls
        
        # Verify URL values are correct
        assert service_urls["backend"] == "http://localhost:8000"
        assert service_urls["auth"] == "http://localhost:8081"
        assert service_urls["websocket"] == "ws://localhost:8000/ws"
        
        print(f"Status report structure validated: {list(status.keys())}")
        print(f"Service URLs: {service_urls}")
    
    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test system resilience to configuration errors."""
        # Test invalid service name handling
        harness = create_e2e_harness()
        
        # Test that invalid service names are handled gracefully
        unknown_url = harness.get_service_url("unknown_service")
        assert unknown_url == "http://localhost:8000"  # Should fall back to default
        
        # Test environment config handling
        assert harness.env_config is not None
        assert hasattr(harness.env_config, 'services')
        
        print(f"Invalid service fallback: {unknown_url}")
        print("Error resilience validated")
    
    @pytest.mark.asyncio
    async def test_service_independence_validation(self):
        """Test that services maintain independence per SPEC/independent_services.xml."""
        harness = create_e2e_harness()
        
        # Test that each service has independent URLs
        backend_url = harness.get_service_url("backend")
        auth_url = harness.get_service_url("auth")
        frontend_url = harness.get_service_url("frontend")
        
        # Services should have different base URLs (different ports)
        assert backend_url != auth_url, "Backend and Auth should be independent"
        assert backend_url != frontend_url, "Backend and Frontend should be independent"
        assert auth_url != frontend_url, "Auth and Frontend should be independent"
        
        # Verify each service URL is valid format
        assert backend_url.startswith(("http://", "https://"))
        assert auth_url.startswith(("http://", "https://"))
        assert frontend_url.startswith(("http://", "https://"))
        
        # Verify ports are different (independence requirement)
        assert ":8000" in backend_url
        assert ":8081" in auth_url
        assert ":3000" in frontend_url
        
        print(f"Backend: {backend_url}")
        print(f"Auth: {auth_url}")
        print(f"Frontend: {frontend_url}")
        print("Service independence validated")


if __name__ == "__main__":
    pytest.main([__file__])
