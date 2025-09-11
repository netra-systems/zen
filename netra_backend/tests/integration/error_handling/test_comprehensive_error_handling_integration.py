"""
Comprehensive Error Handling Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure system reliability across service boundaries
- Value Impact: Validates error propagation and recovery with real services
- Strategic Impact: Prevents cascade failures that could cause platform outages

These tests validate error handling with real PostgreSQL, Redis, WebSocket
connections, and service integrations. NO MOCKS for infrastructure components.

CRITICAL: Integration-level error handling prevents single component failures
from bringing down the entire platform, protecting customer experience.
"""

import asyncio
import json
import time
import uuid
import pytest
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

# SSOT imports - absolute imports from package root
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.websocket import WebSocketTestUtility
from test_framework.conftest_real_services import real_services_fixture
from shared.isolated_environment import get_env
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.configuration.base import UnifiedConfigManager

class TestDatabaseErrorRecovery(SSotAsyncTestCase):
    """
    Test database error recovery with real PostgreSQL and Redis.
    
    BVJ: Database reliability is fundamental to platform operation.
    Proper error handling ensures customer data remains accessible
    even during database connectivity issues.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_postgresql_connection_error_recovery(self, real_services_fixture):
        """
        Test PostgreSQL connection error recovery.
        
        BUSINESS IMPACT: Database connection failures should not prevent
        users from accessing cached data or receiving helpful error messages.
        """
        db_utility = DatabaseTestUtilities()
        real_db = real_services_fixture["database"]
        
        # Ensure real database connection is working first
        await db_utility.verify_connection(real_db)
        
        db_manager = DatabaseManager()
        await db_manager.initialize_with_real_connection(real_db)
        
        # Test connection recovery after simulated failure
        original_execute = db_manager._execute_query
        failure_count = 0
        
        async def failing_execute(query, params=None):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise ConnectionError("Database connection lost")
            return await original_execute(query, params)
        
        # Patch execution to simulate transient failures
        with patch.object(db_manager, '_execute_query', failing_execute):
            # Should recover after retries
            result = await db_manager.get_user_threads("test_user_123")
            
            # Verify recovery worked
            self.assertIsNotNone(result)
            self.assertGreaterEqual(failure_count, 2)  # Confirmed retries occurred
            
            # Verify error context was captured
            error_context = db_manager.get_last_error_context()
            if error_context:
                self.assertEqual(error_context["category"], "database_recovery")
                self.assertIn("recovered_after_retries", error_context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_cache_fallback(self, real_services_fixture):
        """
        Test Redis cache error fallback to database.
        
        BUSINESS IMPACT: Cache failures should not impact user experience,
        system should seamlessly fall back to database with acceptable performance.
        """
        real_redis = real_services_fixture["redis"]
        real_db = real_services_fixture["database"]
        
        db_manager = DatabaseManager()
        await db_manager.initialize_with_real_services(real_db, real_redis)
        
        # Create test data in database
        test_user_id = f"test_user_{uuid.uuid4()}"
        await db_manager.create_user_thread(test_user_id, "Test thread")
        
        # Simulate Redis failure
        with patch.object(db_manager.redis_client, 'get') as mock_redis_get:
            mock_redis_get.side_effect = ConnectionError("Redis unavailable")
            
            # Should fallback to database successfully
            result = await db_manager.get_user_threads(test_user_id)
            
            self.assertIsNotNone(result)
            self.assertTrue(result["from_database_fallback"])
            self.assertIn("cache_unavailable", result["degradation_reason"])
            
            # Verify performance is still acceptable (< 500ms)
            self.assertLess(result["response_time_ms"], 500)
            
            # Verify user-friendly error context
            self.assertNotIn("redis", result.get("user_message", "").lower())
            self.assertNotIn("cache", result.get("user_message", "").lower())
    
    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_database_transaction_error_handling(self, real_services_fixture):
        """
        Test database transaction error handling with real database.
        
        BUSINESS IMPACT: Transaction failures must be handled properly to
        prevent data corruption and maintain data consistency.
        """
        real_db = real_services_fixture["database"]
        db_utility = DatabaseTestUtilities()
        
        # Set up transaction scenario with real database
        async with db_utility.get_transaction_context(real_db) as tx:
            try:
                # Create test data 
                user_id = f"tx_test_user_{uuid.uuid4()}"
                thread_id = await tx.create_user_thread(user_id, "Transaction test")
                
                # Simulate constraint violation
                with self.assertRaises(Exception) as context:
                    await tx.execute(
                        "INSERT INTO user_threads (id, user_id, title) VALUES (%s, %s, %s)",
                        (thread_id, user_id, "Duplicate test")  # Should violate unique constraint
                    )
                
                # Transaction should be rolled back automatically
                await tx.rollback()
                
            except Exception as e:
                # Verify proper error handling occurred
                self.assertIn("constraint", str(e).lower())
                
        # Verify rollback worked - data should not exist
        verification_result = await db_utility.verify_transaction_rollback(
            real_db, 
            "user_threads",
            {"user_id": user_id}
        )
        self.assertTrue(verification_result["rollback_successful"])

class TestWebSocketErrorResilience(SSotAsyncTestCase):
    """
    Test WebSocket error resilience with real connections.
    
    BVJ: WebSocket reliability is critical for real-time chat features.
    Users must receive consistent updates and error recovery should be transparent.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_recovery(self, real_services_fixture):
        """
        Test WebSocket connection recovery mechanisms.
        
        BUSINESS IMPACT: WebSocket failures disrupt real-time chat experience.
        Recovery must be fast and transparent to maintain user engagement.
        """
        websocket_utility = WebSocketTestUtility()
        real_services = real_services_fixture
        
        # Create real WebSocket connection
        ws_manager = UnifiedWebSocketManager()
        await ws_manager.initialize_with_real_services(real_services)
        
        test_user_id = f"ws_test_user_{uuid.uuid4()}"
        
        # Establish connection
        connection = await websocket_utility.create_authenticated_connection(
            user_id=test_user_id,
            base_url=real_services["backend_url"]
        )
        
        # Simulate connection interruption
        await connection.close(code=1006)  # Abnormal closure
        
        # Manager should detect and attempt recovery
        recovery_result = await ws_manager.handle_connection_loss(
            user_id=test_user_id,
            close_code=1006
        )
        
        # Verify recovery was attempted
        self.assertTrue(recovery_result["recovery_attempted"])
        self.assertLess(recovery_result["recovery_time_ms"], 5000)  # < 5 seconds
        
        # Verify new connection is functional
        if recovery_result["recovery_successful"]:
            # Test message sending on recovered connection
            test_message = {
                "type": "ping",
                "timestamp": int(time.time() * 1000)
            }
            
            send_result = await ws_manager.send_message(test_user_id, test_message)
            self.assertTrue(send_result["delivered"])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_delivery_errors(self, real_services_fixture):
        """
        Test WebSocket message delivery error handling.
        
        BUSINESS IMPACT: Failed message delivery must be detected and handled
        to prevent users from losing important agent responses.
        """
        websocket_utility = WebSocketTestUtility()
        real_services = real_services_fixture
        
        ws_manager = UnifiedWebSocketManager()
        await ws_manager.initialize_with_real_services(real_services)
        
        test_user_id = f"msg_test_user_{uuid.uuid4()}"
        
        # Create connection
        connection = await websocket_utility.create_authenticated_connection(
            user_id=test_user_id,
            base_url=real_services["backend_url"]
        )
        
        # Test various message delivery scenarios
        test_messages = [
            {
                "type": "agent_started",
                "agent_id": "test_agent",
                "expected_critical": True
            },
            {
                "type": "agent_thinking", 
                "content": "Analyzing your request...",
                "expected_critical": False
            },
            {
                "type": "agent_completed",
                "result": "Analysis complete",
                "expected_critical": True
            }
        ]
        
        for msg in test_messages:
            # Simulate delivery failure
            with patch.object(connection, 'send') as mock_send:
                mock_send.side_effect = ConnectionError("Connection lost during send")
                
                delivery_result = await ws_manager.send_message_with_retry(
                    test_user_id, 
                    msg
                )
                
                if msg["expected_critical"]:
                    # Critical messages should trigger aggressive retry
                    self.assertTrue(delivery_result["retry_attempted"])
                    self.assertGreaterEqual(delivery_result["retry_count"], 3)
                    
                    # Should store for later delivery if connection recovers
                    stored_messages = await ws_manager.get_pending_messages(test_user_id)
                    self.assertGreater(len(stored_messages), 0)
                else:
                    # Non-critical messages may be dropped with logging
                    self.assertIn("message_dropped", delivery_result["status"])

class TestAuthenticationErrorFlows(SSotAsyncTestCase):
    """
    Test authentication error flows with real auth service integration.
    
    BVJ: Authentication errors directly impact user onboarding and retention.
    Clear error handling reduces support burden and improves conversion.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_validation_error_handling(self, real_services_fixture):
        """
        Test JWT validation error handling with real auth service.
        
        BUSINESS IMPACT: JWT errors should provide clear guidance to users
        about re-authentication without exposing security details.
        """
        real_auth_service = real_services_fixture["auth_service"]
        
        auth_service = UnifiedAuthenticationService()
        await auth_service.initialize_with_real_service(real_auth_service)
        
        # Test various JWT error scenarios
        jwt_test_cases = [
            {
                "token": "invalid.jwt.token",
                "expected_error": "invalid_token_format",
                "expected_user_message": "Please log in again to continue"
            },
            {
                "token": None,
                "expected_error": "missing_token",
                "expected_user_message": "Authentication required to access this feature"
            },
            {
                "token": self._create_expired_jwt(),
                "expected_error": "token_expired",
                "expected_user_message": "Your session has expired. Please log in again"
            }
        ]
        
        for case in jwt_test_cases:
            validation_result = await auth_service.validate_jwt_token(case["token"])
            
            self.assertFalse(validation_result["valid"])
            self.assertEqual(validation_result["error_code"], case["expected_error"])
            self.assertEqual(validation_result["user_message"], case["expected_user_message"])
            
            # Verify no sensitive information leaked
            self.assertNotIn("secret", validation_result.get("debug_info", "").lower())
            self.assertNotIn("private_key", validation_result.get("debug_info", "").lower())
            
    def _create_expired_jwt(self):
        """Create an expired JWT token for testing."""
        import jwt
        import time
        
        payload = {
            "user_id": "test_user",
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }
        return jwt.encode(payload, "test_secret", algorithm="HS256")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_flow_error_handling(self, real_services_fixture):
        """
        Test OAuth flow error handling with real service integration.
        
        BUSINESS IMPACT: OAuth errors during registration/login directly
        impact conversion rates. Clear error handling improves user experience.
        """
        real_auth_service = real_services_fixture["auth_service"]
        
        auth_service = UnifiedAuthenticationService()
        await auth_service.initialize_with_real_service(real_auth_service)
        
        # Test OAuth error scenarios
        oauth_error_cases = [
            {
                "error": "invalid_grant",
                "description": "Authorization code has expired",
                "expected_user_message": "Please try logging in again"
            },
            {
                "error": "access_denied", 
                "description": "User cancelled authorization",
                "expected_user_message": "Login was cancelled. Please try again if you'd like to continue"
            },
            {
                "error": "server_error",
                "description": "OAuth provider temporary error",
                "expected_user_message": "We're experiencing technical difficulties. Please try again in a few moments"
            }
        ]
        
        for case in oauth_error_cases:
            result = await auth_service.handle_oauth_error(
                case["error"],
                case["description"]
            )
            
            self.assertFalse(result["success"])
            self.assertEqual(result["user_message"], case["expected_user_message"])
            
            # Verify appropriate retry guidance
            if case["error"] in ["server_error", "invalid_grant"]:
                self.assertTrue(result["should_retry"])
            else:
                self.assertFalse(result["should_retry"])

class TestAgentExecutionErrorPropagation(SSotAsyncTestCase):
    """
    Test agent execution error propagation across service boundaries.
    
    BVJ: Agent failures must be communicated clearly to users while
    maintaining system stability. Poor error handling reduces trust in AI features.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_llm_error_propagation(self, real_services_fixture):
        """
        Test agent LLM error propagation to WebSocket clients.
        
        BUSINESS IMPACT: LLM API failures should not leave users waiting
        indefinitely. Clear error communication maintains user trust.
        """
        real_services = real_services_fixture
        websocket_utility = WebSocketTestUtility()
        
        # Initialize agent registry with real services
        agent_registry = AgentRegistry()
        await agent_registry.initialize_with_real_services(real_services)
        
        test_user_id = f"agent_test_user_{uuid.uuid4()}"
        
        # Create real WebSocket connection for agent events
        connection = await websocket_utility.create_authenticated_connection(
            user_id=test_user_id,
            base_url=real_services["backend_url"]
        )
        
        # Mock LLM API failure
        with patch('netra_backend.app.llm.llm_manager.LLMManager._call_api') as mock_llm:
            mock_llm.side_effect = Exception("LLM API rate limit exceeded")
            
            # Execute agent with LLM dependency
            execution_result = await agent_registry.execute_agent(
                agent_type="triage_agent",
                user_id=test_user_id,
                message="Help me optimize costs"
            )
            
            # Should handle error gracefully
            self.assertFalse(execution_result["success"])
            self.assertEqual(execution_result["error_category"], "llm_service")
            
            # Verify WebSocket error event was sent
            events = await websocket_utility.collect_events(connection, timeout=5)
            error_events = [e for e in events if e.get("type") == "agent_error"]
            
            self.assertGreater(len(error_events), 0)
            
            error_event = error_events[0]
            self.assertIn("temporarily unavailable", error_event["user_message"].lower())
            self.assertNotIn("rate limit", error_event["user_message"].lower())  # No technical details
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_agent_database_error_recovery(self, real_services_fixture):
        """
        Test agent database error recovery with real database.
        
        BUSINESS IMPACT: Database errors during agent execution should not
        crash the agent workflow or leave users without responses.
        """
        real_services = real_services_fixture
        db_utility = DatabaseTestUtilities()
        
        agent_registry = AgentRegistry()
        await agent_registry.initialize_with_real_services(real_services)
        
        test_user_id = f"db_error_test_{uuid.uuid4()}"
        
        # Simulate database error during agent execution
        with patch.object(
            agent_registry.database_manager, 
            'save_agent_execution_state'
        ) as mock_save:
            mock_save.side_effect = ConnectionError("Database temporarily unavailable")
            
            # Agent should continue execution and provide response
            execution_result = await agent_registry.execute_agent(
                agent_type="data_helper_agent",
                user_id=test_user_id,
                message="Show me my recent activity"
            )
            
            # Should degrade gracefully
            self.assertTrue(execution_result.get("degraded_mode", False))
            self.assertIn("response", execution_result)
            
            # Should indicate state couldn't be saved but provide value
            self.assertIn("state_persistence_failed", execution_result["warnings"])
            
            # User should still receive helpful response
            self.assertNotIn("database", execution_result["response"].lower())
            self.assertIn("recent activity", execution_result["response"].lower())

class TestSystemWideErrorCoordination(SSotAsyncTestCase):
    """
    Test system-wide error coordination and circuit breakers.
    
    BVJ: Coordinated error handling prevents cascade failures that could
    bring down the entire platform, protecting all customer segments.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascade_failure_prevention(self, real_services_fixture):
        """
        Test cascade failure prevention across services.
        
        BUSINESS IMPACT: Single component failures should not bring down
        the entire platform, protecting revenue and customer trust.
        """
        real_services = real_services_fixture
        
        # Initialize multiple service managers
        config_manager = UnifiedConfigManager()
        db_manager = DatabaseManager()
        ws_manager = UnifiedWebSocketManager()
        auth_service = UnifiedAuthenticationService()
        
        # Initialize all with real services
        await config_manager.initialize_with_real_services(real_services)
        await db_manager.initialize_with_real_services(
            real_services["database"], 
            real_services["redis"]
        )
        await ws_manager.initialize_with_real_services(real_services)
        await auth_service.initialize_with_real_service(real_services["auth_service"])
        
        # Simulate database failure
        with patch.object(db_manager, '_execute_query') as mock_db:
            mock_db.side_effect = ConnectionError("Database cluster down")
            
            # Other services should continue functioning
            
            # Auth service should still validate cached tokens
            auth_result = await auth_service.validate_cached_token("test_token")
            self.assertIn("degraded", auth_result.get("mode", ""))
            
            # WebSocket should still accept connections
            ws_health = await ws_manager.get_health_status()
            self.assertEqual(ws_health["status"], "degraded")
            self.assertIn("database_unavailable", ws_health["degradation_reasons"])
            
            # Configuration should still serve cached values
            config_health = config_manager.get_health_status()
            self.assertTrue(config_health["operational"])
            
        # Verify circuit breaker prevents overwhelming failed service
        circuit_status = db_manager.get_circuit_breaker_status()
        self.assertTrue(circuit_status["database_circuit_open"])
        self.assertGreater(circuit_status["failure_count"], 0)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_check_error_aggregation(self, real_services_fixture):
        """
        Test health check error aggregation across services.
        
        BUSINESS IMPACT: Comprehensive health monitoring enables rapid
        incident response and proactive issue resolution.
        """
        real_services = real_services_fixture
        
        from netra_backend.app.core.health.health_monitor import HealthMonitor
        
        health_monitor = HealthMonitor()
        await health_monitor.initialize_with_real_services(real_services)
        
        # Perform comprehensive health check
        health_report = await health_monitor.get_comprehensive_health()
        
        # Verify all critical components are checked
        required_components = [
            "database_postgresql",
            "database_redis", 
            "websocket_manager",
            "auth_service",
            "agent_registry"
        ]
        
        for component in required_components:
            self.assertIn(component, health_report["components"])
            
            component_health = health_report["components"][component]
            self.assertIn("status", component_health)
            self.assertIn("response_time_ms", component_health)
            
            if component_health["status"] != "healthy":
                self.assertIn("error_details", component_health)
                self.assertIn("user_impact", component_health)
        
        # Verify overall status calculation
        if health_report["overall_status"] == "unhealthy":
            self.assertGreater(len(health_report["critical_errors"]), 0)
            self.assertIn("estimated_recovery_time", health_report)
            self.assertIn("mitigation_steps", health_report)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--real-services'])
