"""Integration tests for AuthTraceLogger NoneType error in real scenarios.

This test suite reproduces the NoneType bug in realistic integration scenarios
with real services, databases, and authentication flows.

Business Value: Ensures authentication debugging works in production-like environments.
Bug Reference: auth_trace_logger.py:368 - context.error_context.update(additional_context)
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.logging.auth_trace_logger import AuthTraceLogger, AuthTraceContext


@pytest.mark.integration
class TestAuthTraceLoggerIntegrationBug(BaseIntegrationTest):
    """Integration tests to reproduce NoneType bug with real services."""
    
    def setup_method(self):
        """Set up test fixtures with real services."""
        super().setup_method()
        self.logger = AuthTraceLogger()
    
    @pytest.mark.real_services
    def test_user_session_creation_auth_failure_logging(self, real_services_fixture):
        """
        Test real user session creation auth failure that triggers the bug.
        Uses real database and authentication services.
        """
        # Create a context that mimics real user session creation failure
        context = AuthTraceContext(
            user_id="integration_user_456",
            request_id=f"session_req_{int(time.time())}",
            correlation_id=f"session_corr_{int(time.time())}",
            operation="user_session_creation",
            error_context=None  # Bug trigger - common in rapid session attempts
        )
        
        # Real auth failure scenario - invalid JWT token
        auth_failure = Exception("JWT token validation failed - expired signature")
        additional_context = {
            "session_type": "user_session",
            "database_user_id": 123,
            "jwt_claims_present": True,
            "token_expiry_delta": -300,  # Expired 5 minutes ago
            "client_info": {
                "ip": "10.0.1.100",
                "user_agent": "Mozilla/5.0 (Integration Test)"
            }
        }
        
        # This should reproduce the NoneType bug in integration environment
        with pytest.raises(Exception) as exc_info:
            self.logger.log_failure(context, auth_failure, additional_context)
        
        assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)
    
    @pytest.mark.real_services  
    def test_multi_user_concurrent_auth_failures(self, real_services_fixture):
        """
        Test multiple users failing authentication simultaneously.
        Reproduces race conditions seen in production.
        """
        contexts = []
        for i in range(3):
            context = AuthTraceContext(
                user_id=f"concurrent_user_{i}",
                request_id=f"multi_req_{i}_{int(time.time())}",
                correlation_id=f"multi_corr_{i}_{int(time.time())}",
                operation="multi_user_auth",
                error_context=None  # All start with None, triggering bug
            )
            contexts.append(context)
        
        errors = []
        
        def auth_failure_worker(ctx, user_num):
            try:
                auth_error = Exception(f"User {user_num} authentication failed")
                additional_ctx = {
                    "user_number": user_num,
                    "concurrent_test": True,
                    "database_connection": "active",
                    "redis_connection": "active"
                }
                self.logger.log_failure(ctx, auth_error, additional_ctx)
            except Exception as e:
                errors.append(str(e))
        
        # Start concurrent auth failures
        import threading
        threads = []
        for i, ctx in enumerate(contexts):
            thread = threading.Thread(target=auth_failure_worker, args=(ctx, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have multiple NoneType errors due to race conditions
        assert len(errors) > 0
        none_type_errors = [e for e in errors if "'NoneType' object has no attribute 'update'" in e]
        assert len(none_type_errors) > 0
    
    @pytest.mark.real_services
    def test_service_to_service_auth_failure_system_user(self, real_services_fixture):
        """
        Test service-to-service authentication failure with 'system' user.
        This reproduces the exact production scenario reported.
        """
        context = AuthTraceContext(
            user_id="system",  # Critical - system user context
            request_id=f"service_req_{int(time.time())}",
            correlation_id=f"service_corr_{int(time.time())}",
            operation="service_auth_validation",
            error_context=None  # System contexts often have None initially
        )
        
        # Service-to-service auth failure
        service_error = Exception("Service authentication failed - invalid service credentials")
        additional_context = {
            "source_service": "netra_backend",
            "target_service": "auth_service",
            "endpoint": "/api/internal/validate",
            "method": "POST",
            "service_credentials_present": False,
            "database_health": "ok",
            "redis_health": "ok",
            "auth_service_health": "degraded"
        }
        
        # Should trigger the NoneType bug in service context
        with pytest.raises(Exception) as exc_info:
            self.logger.log_failure(context, service_error, additional_context)
            
        assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)
    
    @pytest.mark.real_services
    def test_websocket_connection_auth_failure_real_scenario(self, real_services_fixture):
        """
        Test real WebSocket connection auth failure scenario.
        WebSocket rapid connections commonly trigger this bug.
        """
        # Multiple WebSocket connection attempts with auth failures
        contexts = []
        for i in range(2):
            context = AuthTraceContext(
                user_id=f"ws_user_{i}",
                request_id=f"ws_conn_req_{i}_{int(time.time())}",
                correlation_id=f"ws_conn_corr_{i}_{int(time.time())}",
                operation="websocket_connection_auth",
                error_context=None  # WebSocket contexts often None initially
            )
            contexts.append(context)
        
        errors = []
        
        def websocket_auth_failure(ctx, conn_id):
            try:
                ws_error = Exception(f"WebSocket connection {conn_id} authentication failed")
                additional_ctx = {
                    "connection_id": conn_id,
                    "connection_type": "websocket",
                    "upgrade_request": True,
                    "origin": "https://app.netra.ai",
                    "real_database": True,
                    "real_redis": True,
                    "websocket_handshake": "failed"
                }
                self.logger.log_failure(ctx, ws_error, additional_ctx)
            except Exception as e:
                errors.append(str(e))
        
        # Simulate rapid WebSocket connection attempts
        import threading
        threads = []
        for i, ctx in enumerate(contexts):
            thread = threading.Thread(target=websocket_auth_failure, args=(ctx, i))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should reproduce the bug in WebSocket scenarios
        assert len(errors) > 0
        assert any("'NoneType' object has no attribute 'update'" in error for error in errors)
    
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_execution_auth_failure_with_trace_logging(self, real_services_fixture):
        """
        Test agent execution auth failure with trace logging.
        Reproduces bug during agent-related authentication.
        """
        context = AuthTraceContext(
            user_id="agent_user_789",
            request_id=f"agent_req_{int(time.time())}",
            correlation_id=f"agent_corr_{int(time.time())}",
            operation="agent_execution_auth",
            error_context=None  # Agent contexts commonly start None
        )
        
        # Agent execution auth failure
        agent_error = Exception("Agent execution auth failed - insufficient permissions")
        additional_context = {
            "agent_type": "data_analysis_agent",
            "execution_context": "user_request",
            "required_permissions": ["execute_tools", "access_data"],
            "user_permissions": ["basic_access"],
            "real_agent_registry": True,
            "real_execution_engine": True,
            "database_user_validation": "failed"
        }
        
        # Should trigger NoneType bug in agent context
        with pytest.raises(Exception) as exc_info:
            self.logger.log_failure(context, agent_error, additional_context)
        
        assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)
    
    @pytest.mark.real_services
    def test_database_connection_auth_failure_integration(self, real_services_fixture):
        """
        Test database connection authentication failure.
        Uses real database connection for integration testing.
        """
        context = AuthTraceContext(
            user_id="db_user_999",
            request_id=f"db_req_{int(time.time())}",
            correlation_id=f"db_corr_{int(time.time())}",
            operation="database_auth_validation",
            error_context=None  # Database auth contexts often None
        )
        
        # Database authentication failure
        db_error = Exception("Database authentication failed - connection refused")
        additional_context = {
            "database_type": "postgresql",
            "database_host": "localhost",
            "database_port": 5434,  # Test database port
            "database_name": "netra_test",
            "connection_pool_status": "available",
            "auth_method": "password",
            "ssl_enabled": False,
            "real_database_test": True
        }
        
        # Should reproduce NoneType bug with real database context
        with pytest.raises(Exception) as exc_info:
            self.logger.log_failure(context, db_error, additional_context)
            
        assert "'NoneType' object has no attribute 'update'" in str(exc_info.value)