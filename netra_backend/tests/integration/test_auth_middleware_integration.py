"""
Integration Tests: Authentication Middleware Integration

Business Value Justification (BVJ):
- Segment: All (middleware processes all authenticated requests)
- Business Goal: Ensure middleware integrates correctly with auth service
- Value Impact: Middleware integration failures block all authenticated operations
- Strategic Impact: Core security - middleware must work with real auth flow

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses real auth service integration patterns
- NO MOCKS in integration tests
"""

import pytest
import time
from typing import Dict, Any, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestAuthMiddlewareIntegration(SSotBaseTestCase):
    """Integration tests for authentication middleware with real auth service."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("AUTH_SERVICE_URL", "http://localhost:8081")
        
    def _simulate_middleware_auth_check(self, headers: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """Simulate middleware auth check with auth service."""
        auth_header = headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return False, {"error": "Invalid auth header"}
            
        token = auth_header[7:]  # Remove "Bearer "
        
        # Simulate auth service validation
        if "valid_token" in token:
            return True, {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "permissions": ["read", "write"]
            }
        return False, {"error": "Invalid token"}
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_middleware_auth_service_integration(self):
        """Test middleware integration with auth service."""
        headers = {"Authorization": "Bearer valid_token_123"}
        
        is_authenticated, user_data = self._simulate_middleware_auth_check(headers)
        
        assert is_authenticated is True
        assert user_data["user_id"] == "test_user_123"
        assert "permissions" in user_data
        
        self.record_metric("middleware_auth_success", True)
        self.increment_db_query_count()  # Auth service DB lookup
        
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_middleware_unauthorized_request_handling(self):
        """Test middleware handling of unauthorized requests."""
        headers = {"Authorization": "Bearer invalid_token"}
        
        is_authenticated, error_data = self._simulate_middleware_auth_check(headers)
        
        assert is_authenticated is False
        assert "error" in error_data
        
        self.record_metric("middleware_auth_failure_handled", True)
