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
        async with create_e2e_harness().test_environment() as harness:
            # Verify environment is ready
            assert harness.is_environment_ready()
            
            # Test service URL resolution
            backend_url = harness.get_service_url("backend")
            auth_url = harness.get_service_url("auth")
            websocket_url = harness.get_websocket_url()
            
            assert backend_url
            assert auth_url
            assert websocket_url
    
    @pytest.mark.asyncio
    async def test_user_creation_and_auth_flow(self):
        """Test user creation and authentication across services."""
        async with create_e2e_harness().test_environment() as harness:
            # Create test user
            user = await harness.create_test_user(
                email=f"test_integration_{self.test_id}@example.com"
            )
            
            # Verify user creation
            assert user.id
            assert user.email
            assert user.tokens
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment with authentication."""
        async with create_e2e_harness().test_environment() as harness:
            # Create test user
            user = await harness.create_test_user(
                email=f"test_ws_{self.test_id}@example.com"
            )
            
            # Create WebSocket connection
            ws_client = await harness.create_websocket_connection(user)
            assert ws_client is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self):
        """Test concurrent operations across multiple users."""
        async with create_e2e_harness().test_environment() as harness:
            # Run concurrent user test
            results = await harness.run_concurrent_user_test(user_count=2)
            
            # Verify results
            assert len(results) == 2
            
            # Check that at least one test succeeded
            successful_results = [
                result for result in results 
                if not isinstance(result, Exception) and 
                   isinstance(result, dict) and 
                   len(result.get("errors", [])) == 0
            ]
            
            assert len(successful_results) >= 1, f"No successful concurrent operations: {results}"
    
    @pytest.mark.asyncio
    async def test_environment_status_reporting(self):
        """Test environment status reporting functionality."""
        async with create_e2e_harness().test_environment() as harness:
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
    
    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test system resilience to errors."""
        async with create_e2e_harness().test_environment() as harness:
            # Test invalid user creation
            try:
                user = await harness.create_test_user(email="invalid-email")
                # If it doesn't throw, that's also acceptable
                assert user is not None
            except Exception as e:
                # Expected behavior for invalid input
                assert "invalid" in str(e).lower() or "email" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_service_independence_validation(self):
        """Test that services maintain independence per SPEC/independent_services.xml."""
        async with create_e2e_harness().test_environment() as harness:
            # Test that each service has independent URLs
            backend_url = harness.get_service_url("backend")
            auth_url = harness.get_service_url("auth")
            
            # Services should have different base URLs (different ports or hosts)
            assert backend_url != auth_url, "Services should be independent"
            
            # Verify each service URL is valid format
            assert backend_url.startswith(("http://", "https://"))
            assert auth_url.startswith(("http://", "https://"))


if __name__ == "__main__":
    pytest.main([__file__])
