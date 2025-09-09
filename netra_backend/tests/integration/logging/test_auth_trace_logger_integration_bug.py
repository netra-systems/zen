"""
Integration Tests for AuthTraceLogger in Real Authentication Flows

Business Value Justification (BVJ):
- Segment: Platform Security & Reliability (all tiers)
- Business Goal: Ensure auth debugging works in real multi-service scenarios
- Value Impact: Prevent auth debugging crashes during critical failure investigation
- Strategic Impact: Reliable authentication debugging across all services

CRITICAL: These tests simulate REAL authentication scenarios where the bug occurs.
They use real services, real database connections, and real auth flows.
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext, auth_tracer
from netra_backend.app.models import User


class TestAuthTraceLoggerIntegrationBug(BaseIntegrationTest):
    """Integration tests for AuthTraceLogger bug in real authentication scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_creation_auth_failure_logging(self, real_services_fixture):
        """
        INTEGRATION BUG TEST: User session creation failure triggers auth logging with None error_context.
        
        This simulates real WebSocket connection auth failures that use AuthTraceLogger.
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create test user
        test_user = User(
            email=f"integration_test_{uuid.uuid4()}@example.com",
            name="Integration Test User"
        )
        db.add(test_user)
        await db.commit()
        
        # Create auth tracer context (this will have error_context=None initially)
        request_id = f"integration_req_{int(time.time())}"
        correlation_id = f"integration_corr_{int(time.time())}"
        
        context = AuthTraceContext(
            user_id=str(test_user.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation="user_session_creation"
        )
        
        # Verify precondition: error_context is None
        assert context.error_context is None
        
        # Simulate auth failure during session creation (common scenario)
        auth_error = Exception("403 Not authenticated - Session creation failed")
        
        # Additional context that would be provided in real session creation failure
        additional_context = {
            "user_id": str(test_user.id),
            "session_creation_attempt": True,
            "database_connection": "active",
            "redis_connection": "active",
            "auth_method": "jwt_validation",
            "request_source": "websocket_connection",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should trigger the bug during real auth failure logging
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            auth_tracer.log_failure(context, auth_error, additional_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_concurrent_auth_failures(self, real_services_fixture):
        """
        INTEGRATION RACE CONDITION TEST: Multiple users experiencing concurrent auth failures.
        
        This simulates the real-world scenario where multiple WebSocket connections
        fail authentication simultaneously.
        """
        db = real_services_fixture["db"]
        
        # Create multiple test users
        num_users = 5
        test_users = []
        for i in range(num_users):
            user = User(
                email=f"concurrent_test_{i}_{uuid.uuid4()}@example.com",
                name=f"Concurrent Test User {i}"
            )
            db.add(user)
            test_users.append(user)
        
        await db.commit()
        
        async def simulate_user_auth_failure(user: User, user_index: int) -> Dict[str, Any]:
            """Simulate auth failure for a specific user."""
            context = AuthTraceContext(
                user_id=str(user.id),
                request_id=f"concurrent_req_{user_index}_{int(time.time())}",
                correlation_id=f"concurrent_corr_{user_index}_{int(time.time())}",
                operation=f"websocket_auth_user_{user_index}"
            )
            
            assert context.error_context is None
            
            # Simulate different types of auth errors
            error_messages = [
                "403 Not authenticated - JWT validation failed",
                "403 Not authenticated - Session expired", 
                "403 Not authenticated - Token malformed",
                "403 Not authenticated - User not found",
                "403 Not authenticated - Permission denied"
            ]
            
            auth_error = Exception(error_messages[user_index % len(error_messages)])
            
            additional_context = {
                "user_id": str(user.id),
                "user_email": user.email,
                "user_index": user_index,
                "connection_type": "websocket",
                "auth_attempt_timestamp": time.time(),
                "client_ip": f"192.168.1.{100 + user_index}",
                "user_agent": f"TestAgent_{user_index}",
                "request_method": "WebSocket",
                "session_state": "establishing"
            }
            
            try:
                auth_tracer.log_failure(context, auth_error, additional_context)
                return {"user_index": user_index, "success": True, "error": None}
            except Exception as e:
                return {"user_index": user_index, "success": False, "error": str(e)}
        
        # Run concurrent auth failures
        tasks = [simulate_user_auth_failure(user, i) for i, user in enumerate(test_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "user_index": i,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        # Analyze results - expect NoneType errors from concurrent access
        failed_results = [r for r in processed_results if not r["success"]]
        none_type_errors = [r for r in failed_results if "'NoneType' object has no attribute 'update'" in r["error"]]
        
        assert len(none_type_errors) > 0, f"Expected 'NoneType' errors from concurrent auth failures: {[r['error'] for r in failed_results]}"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_to_service_auth_failure_system_user(self, real_services_fixture):
        """
        INTEGRATION BUG TEST: Service-to-service auth failure with system user.
        
        This tests the specific scenario where system user auth fails during
        inter-service communication.
        """
        # This simulates service-to-service authentication failure
        context = AuthTraceContext(
            user_id="system",  # System user for service calls
            request_id="service_req_123",
            correlation_id="service_corr_123", 
            operation="inter_service_authentication"
        )
        
        assert context.error_context is None
        
        # System service auth failure (common in microservice environments)
        service_auth_error = Exception("403 Not authenticated - Service authentication failed")
        
        # Additional context for service-to-service auth
        additional_context = {
            "source_service": "netra_backend",
            "target_service": "auth_service", 
            "service_token_present": True,
            "service_secret_valid": False,  # This might cause the failure
            "jwt_validation_result": "failed",
            "service_endpoint": "/api/internal/validate_service_auth",
            "request_headers": {
                "Authorization": "Bearer service_token_***",
                "Service-ID": "netra_backend",
                "Content-Type": "application/json"
            },
            "environment": get_env().get("ENVIRONMENT", "test"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should trigger the bug at line 368 and potentially at system user special logging
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            auth_tracer.log_failure(context, service_auth_error, additional_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_websocket_connection_auth_failure_real_scenario(self, real_services_fixture):
        """
        INTEGRATION BUG TEST: Real WebSocket connection auth failure scenario.
        
        This simulates the exact scenario where WebSocket connections fail auth
        and trigger AuthTraceLogger with None error_context.
        """
        db = real_services_fixture["db"]
        
        # Create test user for WebSocket auth test
        ws_user = User(
            email=f"websocket_test_{uuid.uuid4()}@example.com",
            name="WebSocket Test User"
        )
        db.add(ws_user)
        await db.commit()
        
        # Simulate WebSocket connection auth context
        context = AuthTraceContext(
            user_id=str(ws_user.id),
            request_id=f"ws_req_{int(time.time())}",
            correlation_id=f"ws_corr_{int(time.time())}",
            operation="websocket_connection_auth"
        )
        
        assert context.error_context is None
        
        # WebSocket auth failure (typical scenario)
        ws_auth_error = Exception("403 Not authenticated - WebSocket connection refused")
        
        # Realistic WebSocket auth failure context
        additional_context = {
            "connection_id": f"ws_conn_{uuid.uuid4()}",
            "user_id": str(ws_user.id),
            "websocket_protocol": "ws",
            "connection_origin": "https://netra-frontend.com",
            "auth_token_provided": True,
            "auth_token_valid": False,
            "connection_state": "authenticating",
            "client_info": {
                "user_agent": "Mozilla/5.0 WebSocket Client",
                "ip_address": "192.168.1.50",
                "connection_time": time.time()
            },
            "auth_validation_steps": {
                "token_format_check": "passed",
                "token_signature_check": "failed", 
                "token_expiry_check": "not_reached",
                "user_lookup": "not_reached"
            },
            "error_details": {
                "auth_middleware": "jwt_auth",
                "validation_error": "invalid_signature",
                "suggested_action": "client_should_refresh_token"
            }
        }
        
        # This should trigger the bug during WebSocket auth failure logging
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            auth_tracer.log_failure(context, ws_auth_error, additional_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_auth_failure_with_trace_logging(self, real_services_fixture):
        """
        INTEGRATION BUG TEST: Agent execution auth failure triggers auth trace logging.
        
        This simulates auth failures during agent execution that would use AuthTraceLogger.
        """
        db = real_services_fixture["db"]
        
        # Create test user for agent execution
        agent_user = User(
            email=f"agent_test_{uuid.uuid4()}@example.com",
            name="Agent Test User"
        )
        db.add(agent_user)
        await db.commit()
        
        # Agent execution auth context
        context = AuthTraceContext(
            user_id=str(agent_user.id),
            request_id=f"agent_req_{int(time.time())}",
            correlation_id=f"agent_corr_{int(time.time())}",
            operation="agent_execution_auth_validation"
        )
        
        assert context.error_context is None
        
        # Agent execution auth failure
        agent_auth_error = Exception("403 Not authenticated - Agent execution not authorized")
        
        # Agent-specific additional context
        additional_context = {
            "user_id": str(agent_user.id),
            "agent_name": "cost_optimizer",
            "agent_request_id": f"agent_exec_{uuid.uuid4()}",
            "thread_id": f"thread_{uuid.uuid4()}",
            "run_id": f"run_{uuid.uuid4()}",
            "execution_context": {
                "agent_type": "optimization",
                "execution_mode": "standard",
                "user_subscription": "enterprise",
                "resource_requirements": ["llm_access", "database_read"]
            },
            "auth_requirements": {
                "user_authenticated": True,
                "agent_permissions": "missing",
                "resource_access": "denied",
                "subscription_valid": True
            },
            "failure_point": "agent_permission_check",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should trigger the bug during agent auth failure logging
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            auth_tracer.log_failure(context, agent_auth_error, additional_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_auth_failure_integration(self, real_services_fixture):
        """
        INTEGRATION BUG TEST: Database session auth failure with real database connection.
        
        This tests auth failures during database session creation/management.
        """
        # Database session auth failure context
        context = AuthTraceContext(
            user_id="system",  # Database operations often use system user
            request_id=f"db_req_{int(time.time())}",
            correlation_id=f"db_corr_{int(time.time())}",
            operation="database_session_auth"
        )
        
        assert context.error_context is None
        
        # Database auth failure
        db_auth_error = Exception("403 Not authenticated - Database session authentication failed")
        
        # Database-specific additional context
        additional_context = {
            "database_host": "localhost",
            "database_port": 5434,  # Test database port
            "database_name": "netra_test",
            "connection_pool": "active",
            "session_factory": "request_scoped",
            "auth_method": "database_credentials",
            "connection_state": "authenticating",
            "isolation_level": "READ_COMMITTED",
            "transaction_active": False,
            "connection_timeout": 30,
            "retry_attempt": 1,
            "max_retries": 3,
            "error_source": "database_connection_auth"
        }
        
        # This should trigger the bug during database auth failure logging
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
            auth_tracer.log_failure(context, db_auth_error, additional_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_auth_trace_bug_comprehensive(self, real_services_fixture):
        """
        COMPREHENSIVE INTEGRATION BUG TEST: Cross-service auth failures with detailed context.
        
        This test combines multiple failure scenarios that could occur in production.
        """
        # Test cross-service authentication failure
        contexts_and_errors = [
            {
                "context": AuthTraceContext(
                    user_id="system_backend",
                    request_id="cross_service_req_1", 
                    correlation_id="cross_service_corr_1",
                    operation="backend_to_auth_service"
                ),
                "error": Exception("403 Not authenticated - Cross-service auth failed"),
                "additional_context": {
                    "source_service": "netra_backend",
                    "target_service": "auth_service",
                    "service_endpoint": "/api/internal/validate",
                    "auth_method": "service_token"
                }
            },
            {
                "context": AuthTraceContext(
                    user_id="system_auth",
                    request_id="cross_service_req_2",
                    correlation_id="cross_service_corr_2", 
                    operation="auth_to_backend_service"
                ),
                "error": Exception("403 Not authenticated - Service validation failed"),
                "additional_context": {
                    "source_service": "auth_service",
                    "target_service": "netra_backend",
                    "validation_type": "service_credentials",
                    "failure_reason": "invalid_service_secret"
                }
            }
        ]
        
        # Test each cross-service scenario
        for scenario in contexts_and_errors:
            context = scenario["context"]
            error = scenario["error"]
            additional_context = scenario["additional_context"]
            
            # Verify precondition
            assert context.error_context is None
            
            # This should trigger the bug for each cross-service scenario
            with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'update'"):
                auth_tracer.log_failure(context, error, additional_context)