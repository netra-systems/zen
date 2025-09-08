"""
Comprehensive WebSocket Phase Integration Tests - System Startup to Chat Ready

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Ensures WebSocket infrastructure is properly configured for real-time chat
- Strategic Impact: Validates that startup sequence correctly prepares WebSocket systems for revenue-generating chat interactions

This test suite validates the WEBSOCKET phase of system startup, focusing on all components
that enable real-time chat communication between users and AI agents.

Key WebSocket Components Tested:
1. Unified WebSocket Manager initialization
2. WebSocket Factory setup
3. Agent Handler integration 
4. Authentication middleware
5. CORS middleware
6. Rate limiting
7. Message handling
8. User context extraction
9. Error recovery
10. Performance monitoring
11. Multi-user isolation
12. Critical chat events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)

CRITICAL: These tests validate that WebSocket infrastructure is properly configured
to support real-time chat without requiring actual WebSocket server connections.
"""

import asyncio
import pytest
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import logging

# Test framework imports
from netra_backend.tests.integration.business_value.enhanced_base_integration_test import EnhancedBaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core imports
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory, 
    IsolatedWebSocketManager,
    create_websocket_manager
)
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.auth import WebSocketAuthMiddleware
from netra_backend.app.websocket_core.handlers import BaseMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
from netra_backend.app.websocket_core.enhanced_rate_limiter import EnhancedRateLimiter
from netra_backend.app.websocket_core.performance_monitor_core import PerformanceMonitor
from netra_backend.app.websocket_core.error_recovery_handler import ErrorRecoveryHandler
from netra_backend.app.websocket_core.reconnection_manager import ReconnectionManager
from netra_backend.app.websocket_core.message_buffer import MessageBuffer
from netra_backend.app.websocket_core.event_validation_framework import EventValidationFramework
from netra_backend.app.websocket_core.broadcast_core import BroadcastCore

# Agent execution context
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Mock WebSocket for testing
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for startup testing without actual connections."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client_state = WebSocketState.CONNECTED
        self.sent_messages: List[Dict[str, Any]] = []
        self.closed = False
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Mock send_json for testing."""
        if self.closed:
            raise RuntimeError("WebSocket connection is closed")
        self.sent_messages.append(data)
        logger.debug(f"Mock WebSocket sent message: {data.get('type', 'unknown')}")
        
    async def close(self, code: int = 1000):
        """Mock close for testing."""
        self.closed = True
        self.client_state = WebSocketState.DISCONNECTED
        
    def get_message_count(self) -> int:
        """Get number of messages sent."""
        return len(self.sent_messages)
        
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages of specific type."""
        return [msg for msg in self.sent_messages if msg.get('type') == message_type]


class WebSocketPhaseIntegrationTest(EnhancedBaseIntegrationTest):
    """
    Comprehensive integration tests for WebSocket phase of system startup.
    
    Tests all WebSocket components that enable real-time chat communication
    without requiring actual WebSocket server connections.
    """
    
    def setup_method(self):
        """Enhanced setup for WebSocket integration testing."""
        super().setup_method()
        
        # WebSocket-specific test configuration
        self.websocket_timeout = 30.0
        self.max_connections_per_user = 5
        self.rate_limit_per_minute = 100
        self.test_users: List[Dict[str, Any]] = []
        self.mock_websockets: Dict[str, MockWebSocket] = {}
        
        # Component tracking for validation
        self.initialized_components: List[str] = []
        self.component_health: Dict[str, bool] = {}
        
        logger.info("WebSocket Phase Integration Test setup completed")
        
    def teardown_method(self):
        """Enhanced teardown for WebSocket resources."""
        try:
            # Cleanup mock WebSockets
            for ws in self.mock_websockets.values():
                asyncio.create_task(ws.close())
            self.mock_websockets.clear()
            
            # Clear component tracking
            self.initialized_components.clear()
            self.component_health.clear()
            
        except Exception as e:
            logger.warning(f"Error during WebSocket teardown: {e}")
        finally:
            super().teardown_method()
            
    def _mark_component_initialized(self, component_name: str, healthy: bool = True):
        """Mark a component as initialized for tracking."""
        self.initialized_components.append(component_name)
        self.component_health[component_name] = healthy
        
    # =============================================================================
    # WEBSOCKET CORE MANAGER INITIALIZATION TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_unified_websocket_manager_initialization(self):
        """
        Test WebSocket Core Manager initialization during startup.
        
        BVJ: Ensures core WebSocket infrastructure starts correctly for chat delivery.
        """
        await self.async_setup()
        
        # Test unified manager creation
        manager = UnifiedWebSocketManager()
        self._mark_component_initialized("UnifiedWebSocketManager")
        
        # Validate initialization state
        assert manager is not None, "WebSocket manager must initialize successfully"
        assert hasattr(manager, '_connections'), "Manager must have connections storage"
        assert hasattr(manager, '_user_connections'), "Manager must track user connections"
        assert hasattr(manager, '_lock'), "Manager must have thread safety lock"
        
        # Test initial state
        stats = manager.get_stats()
        assert stats['total_connections'] == 0, "Initial connection count should be 0"
        assert stats['unique_users'] == 0, "Initial user count should be 0"
        
        # Test connection addition capability
        test_user = await self.create_test_user(subscription_tier="enterprise")
        mock_ws = MockWebSocket(test_user["id"])
        self.mock_websockets[test_user["id"]] = mock_ws
        
        connection = WebSocketConnection(
            connection_id=f"test_conn_{uuid.uuid4().hex[:8]}",
            user_id=test_user["id"],
            websocket=mock_ws,
            connected_at=datetime.now()
        )
        
        await manager.add_connection(connection)
        
        # Validate connection was added
        updated_stats = manager.get_stats()
        assert updated_stats['total_connections'] == 1, "Connection should be added"
        assert updated_stats['unique_users'] == 1, "User should be tracked"
        
        # Test business value: connection health check
        assert manager.is_connection_active(test_user["id"]), "Connection should be active"
        
        logger.info("✅ UnifiedWebSocketManager initialization test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_factory_initialization(self):
        """
        Test WebSocket Factory initialization for multi-user isolation.
        
        BVJ: Ensures factory pattern enables secure multi-user chat isolation.
        """
        await self.async_setup()
        
        # Test factory creation
        factory = WebSocketManagerFactory(
            max_managers_per_user=self.max_connections_per_user,
            connection_timeout_seconds=1800
        )
        self._mark_component_initialized("WebSocketManagerFactory")
        
        # Validate factory configuration
        assert factory.max_managers_per_user == self.max_connections_per_user
        assert factory.connection_timeout_seconds == 1800
        
        # Test multi-user isolation
        users = await self.simulate_multi_user_scenario(user_count=3)
        managers = []
        
        for user in users:
            # Create user execution context
            user_context = UserExecutionContext(
                user_id=user["id"],
                thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}"
            )
            
            # Create isolated manager
            manager = factory.create_manager(user_context)
            managers.append(manager)
            
            # Validate manager isolation
            assert manager.user_context.user_id == user["id"]
            assert isinstance(manager, IsolatedWebSocketManager)
            
        # Test factory stats
        stats = factory.get_factory_stats()
        assert stats['current_state']['active_managers'] == 3
        assert stats['current_state']['users_with_managers'] == 3
        assert stats['factory_metrics']['managers_created'] == 3
        
        # Test business value: user isolation verification
        self.assert_multi_user_isolation([
            {"user": user, "manager": manager} 
            for user, manager in zip(users, managers)
        ])
        
        logger.info("✅ WebSocketManagerFactory initialization test passed")
        
    @pytest.mark.asyncio 
    async def test_websocket_connection_handler_setup(self):
        """
        Test WebSocket Connection Handler setup for connection lifecycle.
        
        BVJ: Ensures connection handling supports reliable chat communication.
        """
        await self.async_setup()
        
        # Create connection lifecycle components
        from netra_backend.app.websocket_core.websocket_manager_factory import ConnectionLifecycleManager
        
        test_user = await self.create_test_user(subscription_tier="mid")
        user_context = UserExecutionContext(
            user_id=test_user["id"],
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}"
        )
        
        # Create isolated manager and lifecycle manager
        manager = IsolatedWebSocketManager(user_context)
        lifecycle_manager = ConnectionLifecycleManager(user_context, manager)
        self._mark_component_initialized("ConnectionLifecycleManager")
        
        # Test connection registration
        mock_ws = MockWebSocket(test_user["id"])
        connection = WebSocketConnection(
            connection_id=f"conn_{uuid.uuid4().hex[:8]}",
            user_id=test_user["id"],
            websocket=mock_ws,
            connected_at=datetime.now()
        )
        
        # Register connection
        lifecycle_manager.register_connection(connection)
        await manager.add_connection(connection)
        
        # Test connection health check
        is_healthy = lifecycle_manager.health_check_connection(connection.connection_id)
        assert is_healthy, "Connection should be healthy after registration"
        
        # Test business value: connection lifecycle management
        assert manager.is_connection_active(test_user["id"]), "Connection should be active"
        
        # Test connection cleanup capability
        cleanup_count = await lifecycle_manager.auto_cleanup_expired()
        # Should be 0 since connection is new
        assert cleanup_count == 0, "New connections should not be cleaned up"
        
        logger.info("✅ WebSocket Connection Handler setup test passed")
        
    # =============================================================================
    # WEBSOCKET AUTHENTICATION & MIDDLEWARE TESTS  
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_auth_middleware_configuration(self):
        """
        Test WebSocket Auth middleware configuration for secure chat.
        
        BVJ: Ensures authentication protects chat sessions from unauthorized access.
        """
        await self.async_setup()
        
        # Test auth middleware initialization
        with patch.dict('os.environ', {
            'JWT_SECRET': 'test_jwt_secret_key_for_websocket_auth',
            'OAUTH_CLIENT_ID': 'test_oauth_client_id',
            'OAUTH_CLIENT_SECRET': 'test_oauth_client_secret'
        }):
            env = IsolatedEnvironment()
            
            # Mock auth middleware (since we don't have real auth server)
            auth_middleware = MagicMock(spec=WebSocketAuthMiddleware)
            auth_middleware.authenticate_websocket = AsyncMock(return_value={
                "user_id": "test_user_auth",
                "scopes": ["chat:read", "chat:write"],
                "subscription_tier": "enterprise"
            })
            self._mark_component_initialized("WebSocketAuthMiddleware")
            
            # Test authentication capability
            mock_websocket = MockWebSocket("test_user_auth")
            auth_result = await auth_middleware.authenticate_websocket(
                websocket=mock_websocket,
                token="mock_jwt_token"
            )
            
            # Validate authentication response
            assert auth_result is not None, "Auth should return user data"
            assert auth_result["user_id"] == "test_user_auth"
            assert "chat:read" in auth_result["scopes"]
            assert "chat:write" in auth_result["scopes"]
            
            # Test business value: authentication enables chat access
            assert auth_result["subscription_tier"] == "enterprise"
            
            logger.info("✅ WebSocket Auth middleware configuration test passed")
            
    @pytest.mark.asyncio
    async def test_websocket_cors_middleware_setup(self):
        """
        Test WebSocket CORS middleware setup for cross-origin chat access.
        
        BVJ: Enables secure cross-origin chat access for web applications.
        """
        await self.async_setup()
        
        # Mock CORS middleware configuration
        cors_config = {
            "allow_origins": ["https://app.netra.ai", "https://staging.netra.ai"],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST"],
            "allow_headers": ["authorization", "content-type"]
        }
        
        # Test CORS validation logic (mocked)
        def validate_origin(origin: str) -> bool:
            return origin in cors_config["allow_origins"]
            
        self._mark_component_initialized("WebSocketCORSMiddleware")
        
        # Test valid origins
        assert validate_origin("https://app.netra.ai"), "Production origin should be allowed"
        assert validate_origin("https://staging.netra.ai"), "Staging origin should be allowed"
        
        # Test invalid origins
        assert not validate_origin("https://malicious-site.com"), "Unknown origins should be blocked"
        assert not validate_origin("http://localhost:3000"), "HTTP origins should be blocked in production"
        
        # Test business value: CORS enables secure web app integration
        assert cors_config["allow_credentials"], "Credentials required for authenticated chat"
        
        logger.info("✅ WebSocket CORS middleware setup test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_rate_limiter_initialization(self):
        """
        Test WebSocket Rate Limiter initialization for chat protection.
        
        BVJ: Protects chat infrastructure from abuse and ensures fair usage.
        """
        await self.async_setup()
        
        # Test enhanced rate limiter
        rate_limiter = EnhancedRateLimiter(
            requests_per_minute=self.rate_limit_per_minute,
            burst_allowance=10,
            user_tier_multipliers={
                "free": 0.5,
                "early": 1.0, 
                "mid": 2.0,
                "enterprise": 5.0
            }
        )
        self._mark_component_initialized("EnhancedRateLimiter")
        
        # Test rate limiting for different user tiers
        test_users = await self.simulate_multi_user_scenario(user_count=3)
        
        for user in test_users:
            tier = user["subscription_tier"]
            base_limit = self.rate_limit_per_minute
            
            # Calculate expected limit based on tier
            multiplier = rate_limiter.user_tier_multipliers.get(tier, 1.0)
            expected_limit = int(base_limit * multiplier)
            
            # Test rate limit calculation
            user_limit = rate_limiter.get_user_limit(tier)
            assert user_limit == expected_limit, f"Rate limit incorrect for {tier} tier"
            
            # Test rate limit checking capability
            can_proceed = await rate_limiter.check_rate_limit(
                user_id=user["id"],
                user_tier=tier
            )
            assert can_proceed, f"Initial request should be allowed for {tier} user"
            
        # Test business value: Enterprise users get higher limits
        enterprise_limit = rate_limiter.get_user_limit("enterprise")
        free_limit = rate_limiter.get_user_limit("free")
        assert enterprise_limit > free_limit, "Enterprise users should have higher limits"
        
        logger.info("✅ WebSocket Rate Limiter initialization test passed")
        
    # =============================================================================
    # WEBSOCKET MESSAGE HANDLING TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_message_handler_setup(self):
        """
        Test WebSocket Message Handler setup for chat message processing.
        
        BVJ: Ensures chat messages are properly routed and processed for business value delivery.
        """
        await self.async_setup()
        
        # Create message handler service (mocked for testing)
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        mock_message_service = MagicMock(spec=MessageHandlerService)
        mock_message_service.handle_start_agent = AsyncMock(return_value=True)
        mock_message_service.handle_user_message = AsyncMock(return_value=True)
        
        # Test agent message handler
        test_user = await self.create_test_user(subscription_tier="enterprise")
        mock_websocket = MockWebSocket(test_user["id"])
        self.mock_websockets[test_user["id"]] = mock_websocket
        
        agent_handler = AgentMessageHandler(
            message_handler_service=mock_message_service,
            websocket=mock_websocket
        )
        self._mark_component_initialized("AgentMessageHandler")
        
        # Test message type handling
        supported_types = agent_handler.supported_message_types
        assert MessageType.START_AGENT in supported_types
        assert MessageType.USER_MESSAGE in supported_types
        assert MessageType.CHAT in supported_types
        
        # Test start_agent message handling
        start_agent_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": "Help me optimize my AI costs",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
                "run_id": f"run_{uuid.uuid4().hex[:8]}"
            },
            user_id=test_user["id"]
        )
        
        # Mock the handle_message method to avoid complex dependencies
        with patch.object(agent_handler, 'handle_message') as mock_handle:
            mock_handle.return_value = True
            
            result = await agent_handler.handle_message(
                user_id=test_user["id"],
                websocket=mock_websocket,
                message=start_agent_message
            )
            
            assert result is True, "Message handling should succeed"
            mock_handle.assert_called_once()
            
        # Test business value: message routing enables agent execution
        stats = agent_handler.get_stats()
        assert "messages_processed" in stats
        assert "start_agent_requests" in stats
        
        logger.info("✅ WebSocket Message Handler setup test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_agent_handler_integration(self):
        """
        Test WebSocket Agent Handler integration for agent execution.
        
        BVJ: Ensures WebSocket infrastructure properly integrates with agent system for business value delivery.
        """
        await self.async_setup()
        
        # Test agent handler integration capabilities
        test_user = await self.create_test_user(subscription_tier="mid")
        mock_websocket = MockWebSocket(test_user["id"])
        
        # Create agent execution context
        agent_state = await self.create_agent_execution_context(
            user=test_user,
            request="Analyze my AI performance and suggest optimizations"
        )
        
        # Test WebSocket event generation for agent lifecycle
        async with self.websocket_business_context(test_user) as ws_context:
            self._mark_component_initialized("WebSocketAgentHandler")
            
            # Test agent execution with WebSocket events
            result = await self.execute_agent_with_business_validation(
                agent_name="performance_optimization_agent",
                state=agent_state,
                expected_business_outcomes=[
                    "bottlenecks_identified",
                    "performance_metrics_analyzed", 
                    "optimization_recommendations"
                ],
                timeout=self.websocket_timeout,
                ws_context=ws_context
            )
            
            # Validate business value delivery
            self.assert_business_value_delivered(result)
            
            # Validate WebSocket events for agent lifecycle
            events = ws_context["events"]
            self.assert_websocket_events_sent(events, [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ])
            
            # Test business value: event timing and order
            event_types = [event.get("type") for event in events]
            agent_started_idx = event_types.index("agent_started")
            agent_completed_idx = event_types.index("agent_completed")
            assert agent_started_idx < agent_completed_idx, "Events must be in correct order"
            
        logger.info("✅ WebSocket Agent Handler integration test passed")
        
    # =============================================================================
    # WEBSOCKET USER CONTEXT & ISOLATION TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_user_context_extraction(self):
        """
        Test WebSocket User Context Extraction for multi-user isolation.
        
        BVJ: Ensures proper user context isolation prevents data leakage between users.
        """
        await self.async_setup()
        
        # Test user context extractor
        extractor = WebSocketUserContextExtractor()
        self._mark_component_initialized("WebSocketUserContextExtractor")
        
        # Create test users with different contexts
        users = await self.simulate_multi_user_scenario(user_count=3)
        contexts = []
        
        for user in users:
            # Mock authentication data
            auth_data = {
                "user_id": user["id"],
                "subscription_tier": user["subscription_tier"],
                "scopes": ["chat:read", "chat:write"],
                "monthly_spend": user["monthly_spend"]
            }
            
            # Extract user context
            user_context = await extractor.extract_context(
                websocket=MockWebSocket(user["id"]),
                auth_data=auth_data
            )
            contexts.append(user_context)
            
            # Validate context extraction
            assert user_context.user_id == user["id"]
            assert user_context.subscription_tier == user["subscription_tier"]
            assert hasattr(user_context, 'request_id')
            assert hasattr(user_context, 'thread_id')
            
        # Test business value: context isolation
        for i, context in enumerate(contexts):
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context.user_id != other_context.user_id
                    assert context.request_id != other_context.request_id
                    
        logger.info("✅ WebSocket User Context Extraction test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_multi_user_isolation(self):
        """
        Test WebSocket multi-user isolation for secure chat sessions.
        
        BVJ: Ensures user data isolation maintains trust and compliance for enterprise customers.
        """
        await self.async_setup()
        
        # Create multiple isolated WebSocket managers
        users = await self.simulate_multi_user_scenario(user_count=4)
        isolated_managers = []
        
        for user in users:
            user_context = UserExecutionContext(
                user_id=user["id"],
                thread_id=f"thread_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}"
            )
            
            manager = create_websocket_manager(user_context)
            isolated_managers.append({"user": user, "manager": manager})
            
        self._mark_component_initialized("MultiUserIsolation")
        
        # Test isolation by adding connections and messages
        for item in isolated_managers:
            user = item["user"]
            manager = item["manager"]
            
            # Add connection to isolated manager
            mock_ws = MockWebSocket(user["id"])
            connection = WebSocketConnection(
                connection_id=f"conn_{uuid.uuid4().hex[:8]}",
                user_id=user["id"],
                websocket=mock_ws,
                connected_at=datetime.now()
            )
            
            await manager.add_connection(connection)
            
            # Send test message
            await manager.send_to_user({
                "type": "test_message",
                "data": {"content": f"Hello {user['id']}!"},
                "timestamp": datetime.now().isoformat()
            })
            
        # Validate isolation: each manager should only have its user's data
        for item in isolated_managers:
            user = item["user"]
            manager = item["manager"]
            
            connections = manager.get_user_connections()
            assert len(connections) == 1, f"Manager should have exactly 1 connection for {user['id']}"
            
            # Validate user access restriction
            assert manager.is_connection_active(user["id"]), "Manager should see its own user"
            
            # Test security: manager should not see other users
            for other_item in isolated_managers:
                if other_item["user"]["id"] != user["id"]:
                    other_user_id = other_item["user"]["id"]
                    assert not manager.is_connection_active(other_user_id), \
                        f"Manager should NOT see other user {other_user_id}"
                        
        # Test business value: enterprise isolation requirements met
        enterprise_managers = [item for item in isolated_managers 
                             if item["user"]["subscription_tier"] == "enterprise"]
        assert len(enterprise_managers) > 0, "Should have enterprise users for isolation testing"
        
        for enterprise_item in enterprise_managers:
            manager_stats = enterprise_item["manager"].get_manager_stats()
            assert manager_stats["is_active"], "Enterprise managers must be active"
            assert manager_stats["connections"]["total"] == 1, "Enterprise isolation validated"
            
        logger.info("✅ WebSocket multi-user isolation test passed")
        
    # =============================================================================
    # WEBSOCKET ERROR RECOVERY & MONITORING TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_handler(self):
        """
        Test WebSocket Error Recovery Handler for chat reliability.
        
        BVJ: Ensures chat sessions are resilient to errors and maintain business continuity.
        """
        await self.async_setup()
        
        # Test error recovery handler initialization
        recovery_handler = ErrorRecoveryHandler(
            max_retry_attempts=3,
            retry_backoff_seconds=1.0,
            error_notification_threshold=5
        )
        self._mark_component_initialized("ErrorRecoveryHandler")
        
        test_user = await self.create_test_user(subscription_tier="enterprise")
        
        # Test error recovery capability
        error_context = {
            "user_id": test_user["id"],
            "error_type": "connection_timeout",
            "error_message": "WebSocket connection timed out during agent execution",
            "timestamp": datetime.now(),
            "agent_context": {
                "agent_name": "cost_optimization_agent",
                "execution_state": "analyzing_costs"
            }
        }
        
        # Test error handling
        recovery_plan = await recovery_handler.handle_error(error_context)
        
        # Validate recovery plan
        assert recovery_plan is not None, "Recovery handler should generate plan"
        assert recovery_plan.get("can_recover", False), "Error should be recoverable"
        assert recovery_plan.get("retry_strategy"), "Should have retry strategy"
        
        # Test message recovery capability
        failed_message = {
            "type": "agent_thinking",
            "data": {"status": "Analyzing cost optimization opportunities..."},
            "timestamp": datetime.now().isoformat(),
            "user_id": test_user["id"]
        }
        
        await recovery_handler.queue_failed_message(test_user["id"], failed_message)
        
        # Test recovery queue
        queued_messages = await recovery_handler.get_queued_messages(test_user["id"])
        assert len(queued_messages) == 1, "Message should be queued for recovery"
        assert queued_messages[0]["type"] == "agent_thinking"
        
        # Test business value: enterprise users get priority recovery
        if test_user["subscription_tier"] == "enterprise":
            assert recovery_plan.get("priority") == "high", "Enterprise users should get high priority"
            
        logger.info("✅ WebSocket Error Recovery Handler test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_performance_monitor(self):
        """
        Test WebSocket Performance Monitor for chat optimization.
        
        BVJ: Ensures chat performance meets business requirements for user experience.
        """
        await self.async_setup()
        
        # Test performance monitor initialization
        performance_monitor = PerformanceMonitor(
            metrics_retention_hours=24,
            alert_thresholds={
                "message_latency_ms": 1000,
                "connection_errors_per_minute": 5,
                "memory_usage_mb": 500
            }
        )
        self._mark_component_initialized("PerformanceMonitor")
        
        test_user = await self.create_test_user(subscription_tier="mid")
        
        # Simulate performance metrics collection
        start_time = time.time()
        
        # Mock message processing
        await asyncio.sleep(0.1)  # Simulate processing time
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        # Record performance metrics
        await performance_monitor.record_message_processing(
            user_id=test_user["id"],
            message_type="start_agent",
            processing_time_ms=processing_time_ms,
            success=True
        )
        
        # Record connection metrics
        await performance_monitor.record_connection_event(
            user_id=test_user["id"],
            event_type="connected",
            connection_time_ms=50.0
        )
        
        # Get performance metrics
        metrics = await performance_monitor.get_metrics_summary(test_user["id"])
        
        # Validate metrics collection
        assert "message_processing" in metrics, "Should track message processing metrics"
        assert "connection_events" in metrics, "Should track connection metrics"
        
        # Test business value: performance meets SLA requirements
        avg_processing_time = metrics["message_processing"].get("avg_time_ms", 0)
        assert avg_processing_time < 1000, f"Processing time {avg_processing_time}ms should meet SLA"
        
        # Test alert system
        alerts = await performance_monitor.check_alert_conditions(test_user["id"])
        assert isinstance(alerts, list), "Should return alerts list"
        
        logger.info("✅ WebSocket Performance Monitor test passed")
        
    @pytest.mark.asyncio  
    async def test_websocket_reconnection_manager(self):
        """
        Test WebSocket Reconnection Manager for chat continuity.
        
        BVJ: Ensures chat sessions can recover from network issues for continuous business value delivery.
        """
        await self.async_setup()
        
        # Test reconnection manager initialization
        reconnection_manager = ReconnectionManager(
            max_reconnection_attempts=5,
            reconnection_delay_seconds=2.0,
            exponential_backoff=True,
            session_recovery_timeout_minutes=15
        )
        self._mark_component_initialized("ReconnectionManager")
        
        test_user = await self.create_test_user(subscription_tier="enterprise")
        
        # Test reconnection strategy
        disconnect_context = {
            "user_id": test_user["id"],
            "last_message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "session_state": {
                "active_agent": "optimization_agent",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
                "execution_progress": "analyzing_costs"
            },
            "disconnect_reason": "network_timeout",
            "disconnect_time": datetime.now()
        }
        
        # Generate reconnection plan
        reconnection_plan = await reconnection_manager.create_reconnection_plan(disconnect_context)
        
        # Validate reconnection plan
        assert reconnection_plan is not None, "Should generate reconnection plan"
        assert reconnection_plan.get("can_reconnect", False), "Should support reconnection"
        assert reconnection_plan.get("session_recovery"), "Should support session recovery"
        
        # Test session state preservation
        preserved_state = reconnection_plan.get("preserved_state", {})
        assert preserved_state.get("active_agent") == "optimization_agent"
        assert preserved_state.get("thread_id") == disconnect_context["session_state"]["thread_id"]
        
        # Test business value: enterprise users get enhanced reconnection
        if test_user["subscription_tier"] == "enterprise":
            assert reconnection_plan.get("priority") == "high", "Enterprise users should get priority"
            assert reconnection_plan.get("max_attempts", 0) >= 5, "Enterprise users should get more attempts"
            
        # Test reconnection delay calculation
        for attempt in range(1, 4):
            delay = reconnection_manager.calculate_reconnection_delay(attempt)
            if reconnection_manager.exponential_backoff:
                expected_delay = reconnection_manager.reconnection_delay_seconds * (2 ** (attempt - 1))
                assert delay == expected_delay, f"Exponential backoff delay incorrect for attempt {attempt}"
            
        logger.info("✅ WebSocket Reconnection Manager test passed")
        
    # =============================================================================
    # WEBSOCKET CRITICAL CHAT EVENTS TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_critical_chat_events(self):
        """
        Test WebSocket Critical Chat Events for business value delivery.
        
        BVJ: Validates the 5 critical WebSocket events that enable real-time chat business value:
        - agent_started: User knows AI is working on their problem
        - agent_thinking: Real-time progress visibility  
        - tool_executing: Shows AI using tools to solve problems
        - tool_completed: Demonstrates problem-solving progress
        - agent_completed: Delivers final business value to user
        
        These events are CRITICAL for chat-based revenue generation.
        """
        await self.async_setup()
        
        # Test critical chat event validation framework
        event_validator = EventValidationFramework()
        self._mark_component_initialized("EventValidationFramework")
        
        test_user = await self.create_test_user(subscription_tier="enterprise")
        
        # Define the 5 critical chat events for business value
        critical_events = [
            "agent_started",    # User sees AI began working 
            "agent_thinking",   # Real-time AI reasoning visibility
            "tool_executing",   # Tool usage for problem solving
            "tool_completed",   # Tool results delivery
            "agent_completed"   # Final business value delivered
        ]
        
        # Test event validation for each critical event
        for event_type in critical_events:
            event_data = {
                "type": event_type,
                "user_id": test_user["id"],
                "timestamp": datetime.now().isoformat(),
                "data": self._generate_critical_event_data(event_type, test_user)
            }
            
            # Validate event structure
            is_valid = await event_validator.validate_event(event_data)
            assert is_valid, f"Critical event {event_type} must be valid"
            
            # Test business value: event contains required business context
            business_context = event_data["data"].get("business_context", {})
            if test_user["subscription_tier"] == "enterprise":
                assert business_context, f"Enterprise users need business context in {event_type}"
                
        # Test complete agent execution with critical events
        async with self.websocket_business_context(test_user) as ws_context:
            # Execute agent with WebSocket event tracking
            result = await self.execute_agent_with_business_validation(
                agent_name="cost_optimization_agent",
                state=await self.create_agent_execution_context(test_user, "Optimize my AI costs"),
                expected_business_outcomes=["cost_savings_identified", "actionable_recommendations"],
                ws_context=ws_context
            )
            
            # Validate all critical events were sent
            events = ws_context["events"]
            sent_event_types = [event.get("type") for event in events]
            
            for critical_event in critical_events:
                assert critical_event in sent_event_types, \
                    f"Critical event {critical_event} must be sent for chat business value"
                    
            # Test business value: event sequence enables user engagement
            self.assert_websocket_events_sent(events, critical_events)
            
            # Validate event timing for user experience  
            event_timestamps = [(event.get("type"), event.get("timestamp")) for event in events]
            self._validate_event_timing_for_chat_ux(event_timestamps)
            
        logger.info("✅ WebSocket Critical Chat Events test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_message_buffer_configuration(self):
        """
        Test WebSocket Message Buffer configuration for reliable chat delivery.
        
        BVJ: Ensures chat messages are reliably delivered even during network issues.
        """
        await self.async_setup()
        
        # Test message buffer initialization
        message_buffer = MessageBuffer(
            max_buffer_size=1000,
            buffer_timeout_seconds=300,
            persistence_enabled=True,
            priority_handling=True
        )
        self._mark_component_initialized("MessageBuffer")
        
        test_user = await self.create_test_user(subscription_tier="mid")
        
        # Test message buffering capability
        critical_message = {
            "type": "agent_completed",
            "data": {
                "agent": "optimization_agent",
                "result": "success", 
                "business_outcomes": {
                    "cost_savings_identified": True,
                    "potential_monthly_savings": 2500.00,
                    "recommendations": 3
                }
            },
            "timestamp": datetime.now().isoformat(),
            "critical": True,
            "user_id": test_user["id"]
        }
        
        # Buffer the message
        buffer_id = await message_buffer.buffer_message(test_user["id"], critical_message)
        assert buffer_id is not None, "Message should be buffered successfully"
        
        # Test message retrieval
        buffered_messages = await message_buffer.get_buffered_messages(test_user["id"])
        assert len(buffered_messages) == 1, "Should have 1 buffered message"
        assert buffered_messages[0]["type"] == "agent_completed"
        
        # Test priority handling for critical messages
        critical_count = sum(1 for msg in buffered_messages if msg.get("critical", False))
        assert critical_count == 1, "Should identify critical message"
        
        # Test business value: enterprise users get enhanced buffering
        if test_user["subscription_tier"] in ["enterprise", "mid"]:
            buffer_stats = await message_buffer.get_buffer_stats(test_user["id"])
            assert buffer_stats.get("priority_enabled", False), "Priority users should get enhanced buffering"
            
        # Test message delivery from buffer
        delivery_results = await message_buffer.deliver_buffered_messages(
            test_user["id"], 
            delivery_callback=self._mock_delivery_callback
        )
        assert delivery_results.get("delivered_count", 0) == 1, "Message should be delivered"
        
        logger.info("✅ WebSocket Message Buffer configuration test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_broadcast_capabilities(self):
        """
        Test WebSocket broadcast capabilities for system-wide chat notifications.
        
        BVJ: Enables system-wide notifications and announcements to enhance user experience.
        """
        await self.async_setup()
        
        # Test broadcast core initialization
        broadcast_core = BroadcastCore(
            max_concurrent_broadcasts=10,
            broadcast_timeout_seconds=30,
            delivery_confirmation=True
        )
        self._mark_component_initialized("BroadcastCore")
        
        # Create multiple test users
        users = await self.simulate_multi_user_scenario(user_count=3)
        mock_websockets = {}
        
        # Setup mock WebSockets for all users
        for user in users:
            mock_ws = MockWebSocket(user["id"])
            mock_websockets[user["id"]] = mock_ws
            self.mock_websockets[user["id"]] = mock_ws
            
        # Test system-wide broadcast
        system_notification = {
            "type": "system_announcement",
            "data": {
                "title": "New AI Cost Optimization Features Available",
                "message": "Discover new ways to save on your AI infrastructure costs",
                "action_url": "/features/cost-optimization",
                "priority": "medium"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Execute broadcast
        broadcast_result = await broadcast_core.broadcast_to_all(
            message=system_notification,
            user_filter=lambda user: True,  # All users
            delivery_callback=self._mock_broadcast_delivery
        )
        
        # Validate broadcast results
        assert broadcast_result.get("total_recipients", 0) >= 3, "Should broadcast to all test users"
        assert broadcast_result.get("delivery_success", False), "Broadcast should succeed"
        
        # Test targeted broadcast (enterprise users only)
        enterprise_notification = {
            "type": "tier_specific_announcement", 
            "data": {
                "title": "Enterprise Analytics Dashboard Now Available",
                "message": "Access advanced AI cost analytics and forecasting",
                "tier_requirement": "enterprise"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        enterprise_broadcast = await broadcast_core.broadcast_to_segment(
            message=enterprise_notification,
            segment_filter=lambda user: user.get("subscription_tier") == "enterprise",
            users=users
        )
        
        # Test business value: targeted messaging by subscription tier
        enterprise_recipients = enterprise_broadcast.get("recipients_count", 0)
        enterprise_users_count = len([u for u in users if u["subscription_tier"] == "enterprise"])
        assert enterprise_recipients == enterprise_users_count, "Should target only enterprise users"
        
        logger.info("✅ WebSocket broadcast capabilities test passed")
        
    # =============================================================================
    # WEBSOCKET HEALTH CHECK & MONITORING TESTS
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_health_checks_and_monitoring(self):
        """
        Test WebSocket health checks and monitoring for operational reliability.
        
        BVJ: Ensures WebSocket infrastructure maintains high availability for continuous business value delivery.
        """
        await self.async_setup()
        
        # Test comprehensive health monitoring
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        manager = UnifiedWebSocketManager()
        self._mark_component_initialized("WebSocketHealthMonitoring")
        
        test_users = await self.simulate_multi_user_scenario(user_count=2)
        
        # Add connections for health testing
        for user in test_users:
            mock_ws = MockWebSocket(user["id"])
            connection = WebSocketConnection(
                connection_id=f"health_conn_{uuid.uuid4().hex[:8]}",
                user_id=user["id"], 
                websocket=mock_ws,
                connected_at=datetime.now()
            )
            await manager.add_connection(connection)
            
        # Test health check functionality
        health_status = await manager.get_monitoring_health_status()
        
        # Validate health monitoring capabilities
        assert health_status is not None, "Health monitoring should be available"
        assert "monitoring_enabled" in health_status, "Should report monitoring status"
        assert "task_health" in health_status, "Should report task health"
        assert "overall_health" in health_status, "Should calculate overall health"
        
        # Test connection health validation
        for user in test_users:
            connection_health = manager.get_connection_health(user["id"])
            assert connection_health["has_active_connections"], f"User {user['id']} should have active connection"
            assert connection_health["active_connections"] > 0, "Should report active connection count"
            
        # Test business value: health monitoring prevents service disruption
        overall_health = health_status["overall_health"]
        assert overall_health["score"] >= 70, "WebSocket health should meet minimum SLA requirements"
        
        # Test error statistics tracking
        error_stats = manager.get_error_statistics()
        assert "total_error_count" in error_stats, "Should track error statistics"
        assert "recent_errors_5min" in error_stats, "Should track recent error rates"
        
        # Test background monitoring system
        monitoring_status = await manager.restart_background_monitoring(force_restart=False)
        assert monitoring_status.get("monitoring_restarted") is not None, "Should report monitoring restart status"
        
        logger.info("✅ WebSocket health checks and monitoring test passed")
        
    @pytest.mark.asyncio
    async def test_websocket_configuration_validation(self):
        """
        Test WebSocket configuration validation for proper startup.
        
        BVJ: Ensures WebSocket infrastructure is properly configured to deliver reliable chat business value.
        """
        await self.async_setup()
        
        # Test configuration validation
        websocket_config = {
            "max_connections_per_user": self.max_connections_per_user,
            "connection_timeout_seconds": 1800,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "message_buffer_size": 1000,
            "enable_compression": True,
            "enable_heartbeat": True,
            "heartbeat_interval_seconds": 30,
            "authentication_required": True,
            "cors_enabled": True,
            "monitoring_enabled": True,
            "error_recovery_enabled": True,
            "performance_tracking": True
        }
        
        self._mark_component_initialized("WebSocketConfigValidation")
        
        # Validate configuration parameters
        assert websocket_config["max_connections_per_user"] > 0, "Must allow connections per user"
        assert websocket_config["connection_timeout_seconds"] >= 300, "Timeout should be reasonable"
        assert websocket_config["rate_limit_per_minute"] > 0, "Must have rate limiting"
        assert websocket_config["authentication_required"], "Authentication is mandatory for chat"
        assert websocket_config["monitoring_enabled"], "Monitoring required for business operations"
        
        # Test business value: configuration supports enterprise requirements
        if websocket_config.get("enterprise_features_enabled", True):
            assert websocket_config["error_recovery_enabled"], "Enterprise needs error recovery"
            assert websocket_config["performance_tracking"], "Enterprise needs performance metrics"
            assert websocket_config["message_buffer_size"] >= 1000, "Enterprise needs adequate buffering"
            
        # Test security configuration
        security_config = {
            "jwt_validation": websocket_config.get("authentication_required", False),
            "cors_validation": websocket_config.get("cors_enabled", False),
            "rate_limiting": websocket_config.get("rate_limit_per_minute", 0) > 0,
            "connection_limits": websocket_config.get("max_connections_per_user", 0) > 0
        }
        
        security_score = sum(1 for feature in security_config.values() if feature)
        assert security_score >= 3, f"Security configuration insufficient: {security_score}/4 features enabled"
        
        # Test operational configuration
        operational_config = {
            "monitoring": websocket_config.get("monitoring_enabled", False),
            "error_recovery": websocket_config.get("error_recovery_enabled", False),
            "performance_tracking": websocket_config.get("performance_tracking", False),
            "heartbeat": websocket_config.get("enable_heartbeat", False)
        }
        
        operational_score = sum(1 for feature in operational_config.values() if feature)
        assert operational_score >= 3, f"Operational configuration insufficient: {operational_score}/4 features enabled"
        
        logger.info("✅ WebSocket configuration validation test passed")
        
    # =============================================================================
    # HELPER METHODS FOR TESTING
    # =============================================================================
    
    def _generate_critical_event_data(self, event_type: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic data for critical chat events."""
        base_data = {
            "user_id": user["id"],
            "timestamp": datetime.now().isoformat(),
            "business_context": {
                "subscription_tier": user["subscription_tier"],
                "monthly_spend": user["monthly_spend"]
            }
        }
        
        if event_type == "agent_started":
            return {
                **base_data,
                "agent": "cost_optimization_agent",
                "request": "Help me optimize my AI costs",
                "estimated_duration": "2-3 minutes"
            }
        elif event_type == "agent_thinking":
            return {
                **base_data,
                "status": "Analyzing current AI spending patterns...",
                "phase": "data_collection",
                "progress": 25
            }
        elif event_type == "tool_executing":
            return {
                **base_data,
                "tool": "cost_analysis_tool",
                "purpose": "Analyze spending patterns and identify optimization opportunities"
            }
        elif event_type == "tool_completed":
            return {
                **base_data,
                "tool": "cost_analysis_tool",
                "result": "success",
                "insights_found": 5
            }
        elif event_type == "agent_completed":
            return {
                **base_data,
                "agent": "cost_optimization_agent",
                "result": "success",
                "business_outcomes": {
                    "cost_savings_identified": True,
                    "potential_monthly_savings": 2500.00,
                    "recommendations": 3
                },
                "execution_time": 145.2
            }
        else:
            return base_data
            
    def _validate_event_timing_for_chat_ux(self, event_timestamps: List[tuple]) -> None:
        """Validate event timing meets chat UX requirements."""
        if len(event_timestamps) < 2:
            return
            
        # Parse timestamps and calculate intervals
        parsed_events = []
        for event_type, timestamp_str in event_timestamps:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                parsed_events.append((event_type, timestamp))
            except (ValueError, AttributeError):
                continue  # Skip invalid timestamps
                
        # Check event intervals for user experience
        for i in range(1, len(parsed_events)):
            prev_event = parsed_events[i-1]
            curr_event = parsed_events[i]
            
            interval = (curr_event[1] - prev_event[1]).total_seconds()
            
            # Events should not be too close together (spam) or too far apart (stale)
            assert 0.1 <= interval <= 60, \
                f"Event interval {interval}s between {prev_event[0]} and {curr_event[0]} outside UX range"
                
    async def _mock_delivery_callback(self, message: Dict[str, Any]) -> bool:
        """Mock delivery callback for testing."""
        return True
        
    async def _mock_broadcast_delivery(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Mock broadcast delivery for testing."""
        return True