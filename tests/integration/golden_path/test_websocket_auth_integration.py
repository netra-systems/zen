"""
Test WebSocket Authentication Integration for Golden Path

CRITICAL INTEGRATION TEST: This validates the complete WebSocket authentication flow
with real Auth service integration that enables secure Golden Path user connections.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Secure authentication foundation for $500K+ ARR chat platform
- Value Impact: Authentication failures = complete loss of chat functionality
- Strategic Impact: Security and user trust foundation for business growth

INTEGRATION POINTS TESTED:
1. JWT token validation with real Auth service
2. WebSocket connection establishment with authentication headers
3. User context creation and factory initialization  
4. Authentication failure handling and error responses
5. Multi-user authentication isolation

MUST use REAL services - NO MOCKS in integration tests per CLAUDE.md
"""

import asyncio
import pytest
import time
import json
import websockets
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_integration_test import BaseIntegrationTest
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketTestClient
from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWebSocketAuthIntegration(BaseIntegrationTest):
    """Test WebSocket authentication integration with real services."""
    
    async def async_setup_method(self, method=None):
        """Async setup for integration test components."""
        await super().async_setup_method(method)
        
        # Initialize auth helpers
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Test configuration
        self.backend_url = self.get_env_var("BACKEND_URL", "http://localhost:8000")
        self.websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Test metrics
        self.record_metric("test_category", "integration")
        self.record_metric("golden_path_component", "websocket_auth_integration")
        self.record_metric("real_services_required", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_jwt_token_validation_with_real_auth_service(self, real_services_fixture):
        """Test JWT token validation using real Auth service."""
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="auth_test_user@example.com",
            environment=self.environment,
            permissions=["read", "write", "execute_agents"],
            websocket_enabled=True
        )
        
        # Get JWT token from real auth service
        start_time = time.time()
        jwt_token = await self.auth_helper.get_staging_token_async(
            email=user_context.agent_context.get('user_email')
        )
        auth_time = time.time() - start_time
        
        # Assertions
        assert jwt_token is not None, "Auth service should return JWT token"
        assert len(jwt_token) > 50, f"JWT token should be substantial length: {len(jwt_token)}"
        assert auth_time < 5.0, f"Auth should complete within 5s: {auth_time:.2f}s"
        
        # Validate token structure (basic JWT format)
        jwt_parts = jwt_token.split('.')
        assert len(jwt_parts) == 3, f"JWT should have 3 parts: {len(jwt_parts)}"
        
        # Test token with auth headers
        auth_headers = self.auth_helper.get_auth_headers(jwt_token)
        assert "Authorization" in auth_headers, "Should create authorization header"
        assert auth_headers["Authorization"].startswith("Bearer "), \
            "Should use Bearer token format"
        
        self.record_metric("jwt_validation_test_passed", True)
        self.record_metric("auth_response_time", auth_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_connection_with_real_authentication(self, real_services_fixture):
        """Test WebSocket connection establishment with real authentication."""
        # Create authenticated user
        user_context = await create_authenticated_user_context(
            user_email="websocket_auth_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Get authentication token
        jwt_token = await self.auth_helper.get_staging_token_async(
            email=user_context.agent_context.get('user_email')
        )
        
        # Get WebSocket headers with authentication
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        
        # Verify headers structure
        assert "Authorization" in ws_headers, "WebSocket headers missing auth"
        assert "X-E2E-Test" in ws_headers, "WebSocket headers missing E2E detection"
        assert "X-User-ID" in ws_headers, "WebSocket headers missing user ID"
        
        # Establish WebSocket connection with authentication
        connection_start = time.time()
        websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=self.websocket_url,
            headers=ws_headers,
            timeout=10.0,
            user_id=str(user_context.user_id)
        )
        connection_time = time.time() - connection_start
        
        # Assertions
        assert websocket_connection is not None, "WebSocket connection should be established"
        assert connection_time < 10.0, f"Connection should be fast: {connection_time:.2f}s"
        
        try:
            # Test connection is authenticated by sending test message
            test_message = {
                "type": "connection_test",
                "user_id": str(user_context.user_id),
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(
                websocket_connection, test_message, timeout=5.0
            )
            
            # Should receive acknowledgment (connection works)
            response = await WebSocketTestHelpers.receive_test_message(
                websocket_connection, timeout=5.0
            )
            
            # Basic response validation
            assert response is not None, "Should receive response to test message"
            
        finally:
            # Cleanup connection
            await WebSocketTestHelpers.close_test_connection(websocket_connection)
        
        self.record_metric("websocket_auth_connection_test_passed", True)
        self.record_metric("connection_establishment_time", connection_time)
        
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.asyncio
    async def test_user_context_creation_with_factory_initialization(self, real_services_fixture):
        """Test user context creation and factory initialization with real services."""
        # Create multiple user contexts to test factory isolation
        user_contexts = []
        
        for i in range(3):
            user_context = await create_authenticated_user_context(
                user_email=f"factory_test_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True,
                permissions=["read", "write", "execute_agents"]
            )
            user_contexts.append(user_context)
        
        # Verify each context is unique and properly isolated
        user_ids = [ctx.user_id for ctx in user_contexts]
        thread_ids = [ctx.thread_id for ctx in user_contexts]
        run_ids = [ctx.run_id for ctx in user_contexts]
        
        # Check uniqueness
        assert len(set(user_ids)) == 3, "All user IDs should be unique"
        assert len(set(thread_ids)) == 3, "All thread IDs should be unique"
        assert len(set(run_ids)) == 3, "All run IDs should be unique"
        
        # Verify context structure for each user
        for i, context in enumerate(user_contexts):
            assert isinstance(context, StronglyTypedUserExecutionContext), \
                f"Context {i} should be properly typed"
            assert context.user_id is not None, f"Context {i} missing user ID"
            assert context.thread_id is not None, f"Context {i} missing thread ID"
            assert context.run_id is not None, f"Context {i} missing run ID"
            assert context.websocket_id is not None, f"Context {i} missing WebSocket ID"
            
            # Check agent context
            assert "user_email" in context.agent_context, \
                f"Context {i} missing user email in agent context"
            assert "permissions" in context.agent_context, \
                f"Context {i} missing permissions in agent context"
        
        # Test factory isolation - each context should be independent
        context_1_data = user_contexts[0].agent_context["user_email"]
        context_2_data = user_contexts[1].agent_context["user_email"]  
        context_3_data = user_contexts[2].agent_context["user_email"]
        
        assert context_1_data != context_2_data, "Contexts should have different emails"
        assert context_2_data != context_3_data, "Contexts should have different emails"
        assert context_1_data != context_3_data, "Contexts should have different emails"
        
        self.record_metric("user_context_factory_test_passed", True)
        self.record_metric("user_contexts_created", len(user_contexts))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_authentication_failure_handling(self, real_services_fixture):
        """Test handling of authentication failures with real services."""
        # Test case 1: Invalid JWT token
        invalid_token = "invalid.jwt.token"
        invalid_headers = self.websocket_helper.get_websocket_headers(invalid_token)
        
        # Should fail to connect with invalid token
        with pytest.raises(Exception) as exc_info:
            await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=invalid_headers,
                timeout=5.0,
                user_id="test_user"
            )
        
        # Verify it's an authentication-related failure
        error_str = str(exc_info.value).lower()
        auth_error_indicators = ["auth", "token", "unauthorized", "forbidden", "401", "403"]
        auth_error_found = any(indicator in error_str for indicator in auth_error_indicators)
        assert auth_error_found, f"Should be auth-related error: {exc_info.value}"
        
        # Test case 2: Expired token (simulate)
        # Note: In real integration, this would use an actually expired token
        # For this test, we'll use a malformed token that fails validation
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token"
        expired_headers = self.websocket_helper.get_websocket_headers(expired_token)
        
        with pytest.raises(Exception):
            await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=expired_headers,
                timeout=5.0,
                user_id="test_user"
            )
        
        # Test case 3: Missing authentication headers
        empty_headers = {}
        
        with pytest.raises(Exception):
            await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=empty_headers,
                timeout=5.0,
                user_id="test_user"
            )
        
        self.record_metric("auth_failure_handling_test_passed", True)
        self.record_metric("auth_failure_scenarios_tested", 3)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_concurrent_websocket_authentication(self, real_services_fixture):
        """Test concurrent WebSocket authentication for multiple users."""
        concurrent_users = 5
        connection_tasks = []
        
        # Create concurrent authentication tasks
        for i in range(concurrent_users):
            task = self._create_concurrent_auth_connection(
                f"concurrent_auth_user_{i}@example.com",
                i
            )
            connection_tasks.append(task)
        
        # Execute all authentications concurrently
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_connections = 0
        failed_connections = 0
        connection_times = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_connections += 1
                print(f"❌ Concurrent auth {i} failed: {result}")
            else:
                successful_connections += 1
                connection_times.append(result["connection_time"])
                print(f"✅ Concurrent auth {i} succeeded in {result['connection_time']:.2f}s")
        
        # Assertions
        success_rate = successful_connections / concurrent_users
        assert success_rate >= 0.8, \
            f"Should have 80%+ success rate for concurrent auth: {success_rate:.1%}"
        
        if connection_times:
            avg_connection_time = sum(connection_times) / len(connection_times)
            assert avg_connection_time < 10.0, \
                f"Average connection time should be reasonable: {avg_connection_time:.2f}s"
        
        assert total_time < 30.0, \
            f"All concurrent auths should complete within 30s: {total_time:.2f}s"
        
        self.record_metric("concurrent_auth_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("auth_success_rate", success_rate)
        self.record_metric("total_concurrent_time", total_time)
        
    async def _create_concurrent_auth_connection(
        self, 
        user_email: str, 
        user_index: int
    ) -> Dict[str, Any]:
        """Create a concurrent authentication connection for testing."""
        try:
            # Create user context
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment=self.environment,
                websocket_enabled=True
            )
            
            # Authenticate
            jwt_token = await self.auth_helper.get_staging_token_async(
                email=user_context.agent_context.get('user_email')
            )
            
            # Create WebSocket connection
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            
            connection_start = time.time()
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=10.0,
                user_id=str(user_context.user_id)
            )
            connection_time = time.time() - connection_start
            
            # Test connection with ping
            await WebSocketTestHelpers.send_test_message(
                connection, 
                {"type": "ping", "user_index": user_index},
                timeout=3.0
            )
            
            # Cleanup
            await WebSocketTestHelpers.close_test_connection(connection)
            
            return {
                "success": True,
                "user_index": user_index,
                "connection_time": connection_time,
                "user_id": str(user_context.user_id)
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_index": user_index,
                "error": str(e)
            }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_authentication_performance_benchmarks(self, real_services_fixture):
        """Test authentication performance meets business requirements."""
        performance_metrics = {
            "token_generation_times": [],
            "connection_establishment_times": [],
            "total_auth_times": []
        }
        
        # Run multiple authentication cycles to get performance data
        test_cycles = 10
        
        for i in range(test_cycles):
            total_start = time.time()
            
            # Create user context
            user_context = await create_authenticated_user_context(
                user_email=f"perf_test_user_{i}@example.com",
                environment=self.environment,
                websocket_enabled=True
            )
            
            # Measure token generation time
            token_start = time.time()
            jwt_token = await self.auth_helper.get_staging_token_async(
                email=user_context.agent_context.get('user_email')
            )
            token_time = time.time() - token_start
            performance_metrics["token_generation_times"].append(token_time)
            
            # Measure connection establishment time
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            
            connection_start = time.time()
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=10.0,
                user_id=str(user_context.user_id)
            )
            connection_time = time.time() - connection_start
            performance_metrics["connection_establishment_times"].append(connection_time)
            
            # Total auth time
            total_time = time.time() - total_start
            performance_metrics["total_auth_times"].append(total_time)
            
            # Cleanup
            await WebSocketTestHelpers.close_test_connection(connection)
        
        # Calculate performance statistics
        avg_token_time = sum(performance_metrics["token_generation_times"]) / test_cycles
        avg_connection_time = sum(performance_metrics["connection_establishment_times"]) / test_cycles
        avg_total_time = sum(performance_metrics["total_auth_times"]) / test_cycles
        
        max_token_time = max(performance_metrics["token_generation_times"])
        max_connection_time = max(performance_metrics["connection_establishment_times"])
        max_total_time = max(performance_metrics["total_auth_times"])
        
        # Business performance requirements
        assert avg_token_time < 3.0, \
            f"Average token generation should be < 3s: {avg_token_time:.2f}s"
        assert avg_connection_time < 5.0, \
            f"Average connection time should be < 5s: {avg_connection_time:.2f}s"
        assert avg_total_time < 8.0, \
            f"Average total auth time should be < 8s: {avg_total_time:.2f}s"
        
        # Peak performance requirements (95th percentile approximation)
        assert max_token_time < 5.0, \
            f"Max token generation should be < 5s: {max_token_time:.2f}s"
        assert max_connection_time < 10.0, \
            f"Max connection time should be < 10s: {max_connection_time:.2f}s"
        assert max_total_time < 15.0, \
            f"Max total auth time should be < 15s: {max_total_time:.2f}s"
        
        # Record performance metrics
        self.record_metric("auth_performance_test_passed", True)
        self.record_metric("avg_token_generation_time", avg_token_time)
        self.record_metric("avg_connection_establishment_time", avg_connection_time)
        self.record_metric("avg_total_auth_time", avg_total_time)
        self.record_metric("performance_test_cycles", test_cycles)
        
        print(f"\n📊 AUTHENTICATION PERFORMANCE METRICS:")
        print(f"   🔑 Avg Token Generation: {avg_token_time:.2f}s (max: {max_token_time:.2f}s)")
        print(f"   🔌 Avg Connection Time: {avg_connection_time:.2f}s (max: {max_connection_time:.2f}s)")  
        print(f"   ⏱️  Avg Total Auth Time: {avg_total_time:.2f}s (max: {max_total_time:.2f}s)")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_authentication_with_different_user_permissions(self, real_services_fixture):
        """Test authentication with different user permission levels."""
        permission_test_cases = [
            {
                "permissions": ["read"],
                "description": "Read-only user"
            },
            {
                "permissions": ["read", "write"],
                "description": "Read-write user"
            },
            {
                "permissions": ["read", "write", "execute_agents"],
                "description": "Full permissions user"
            },
            {
                "permissions": ["read", "write", "execute_agents", "admin"],
                "description": "Admin user"
            }
        ]
        
        for i, test_case in enumerate(permission_test_cases):
            permissions = test_case["permissions"]
            description = test_case["description"]
            
            # Create user context with specific permissions
            user_context = await create_authenticated_user_context(
                user_email=f"permissions_test_{i}@example.com",
                environment=self.environment,
                permissions=permissions,
                websocket_enabled=True
            )
            
            # Verify permissions are set correctly
            assert user_context.agent_context.get("permissions") == permissions, \
                f"Permissions should match for {description}"
            
            # Test authentication works for this permission level
            jwt_token = await self.auth_helper.get_staging_token_async(
                email=user_context.agent_context.get('user_email')
            )
            assert jwt_token is not None, f"Should authenticate {description}"
            
            # Test WebSocket connection works
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            connection = await WebSocketTestHelpers.create_test_websocket_connection(
                url=self.websocket_url,
                headers=ws_headers,
                timeout=10.0,
                user_id=str(user_context.user_id)
            )
            
            assert connection is not None, f"Should connect {description}"
            
            # Test basic message sending
            test_message = {
                "type": "permission_test",
                "permissions": permissions,
                "user_type": description
            }
            
            await WebSocketTestHelpers.send_test_message(connection, test_message)
            
            # Cleanup
            await WebSocketTestHelpers.close_test_connection(connection)
        
        self.record_metric("permissions_auth_test_passed", True)
        self.record_metric("permission_levels_tested", len(permission_test_cases))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])