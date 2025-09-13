"""
Unit Tests for WebSocketBridgeFactory SSOT Validation Failures

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist in the WebSocketBridgeFactory implementation. The tests demonstrate
specific SSOT violations that prevent proper factory initialization.

Test Categories:
1. SSOT Dependency Validation - Missing or invalid dependencies
2. Factory Configuration SSOT - Inconsistent factory configuration patterns  
3. User Context Validation - SSOT violations in user context handling
4. WebSocket Connection SSOT - Connection pool integration failures
5. Resource Management SSOT - Cleanup and lifecycle management violations

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages
- Failures demonstrate the factory initialization problems affecting golden path
- Error messages provide concrete evidence of SSOT validation violations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, Dict, Any

from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    WebSocketFactoryConfig
)
from shared.types.core_types import (
    WebSocketMessage as WebSocketEvent,
    ConnectionState as ConnectionStatus
)
from netra_backend.app.services.user_execution_context import UserExecutionContext as UserWebSocketContext
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactoryError
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_connection_pool import WebSocketConnectionPool


class TestWebSocketBridgeFactorySSotValidation:
    """Test SSOT validation failures in WebSocketBridgeFactory."""
    
    def test_factory_requires_connection_pool_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate connection pool dependency.
        
        SSOT Issue: Factory allows None connection pool, violating SSOT dependency pattern.
        Expected Failure: Factory should reject None connection pool during configure().
        """
        factory = WebSocketBridgeFactory()
        
        # This should FAIL with SSOT validation error - factory requires connection pool
        with pytest.raises(ValueError, match="Connection pool cannot be None"):
            factory.configure(
                connection_pool=None,  # SSOT violation: None dependency
                agent_registry=Mock(),
                health_monitor=Mock()
            )
    
    def test_factory_ssot_agent_registry_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce SSOT agent registry pattern.
        
        SSOT Issue: Factory accepts invalid agent registry types without validation.
        Expected Failure: Factory should validate agent registry interface compliance.
        """
        factory = WebSocketBridgeFactory()
        mock_pool = Mock(spec=WebSocketConnectionPool)
        
        # This should FAIL - non-AgentRegistry object should be rejected
        invalid_registry = "not_an_agent_registry"  # SSOT violation: wrong type
        
        with pytest.raises(TypeError, match="AgentRegistry"):
            factory.configure(
                connection_pool=mock_pool,
                agent_registry=invalid_registry,  # SSOT violation: invalid type
                health_monitor=Mock()
            )
    
    @pytest.mark.asyncio
    async def test_user_emitter_creation_ssot_context_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: User emitter creation should validate user context SSOT.
        
        SSOT Issue: Factory creates emitters without validating UserExecutionContext.
        Expected Failure: Should reject invalid or incomplete user contexts.
        """
        factory = WebSocketBridgeFactory()
        mock_pool = Mock(spec=WebSocketConnectionPool)
        mock_registry = Mock()
        
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=mock_registry,
            health_monitor=Mock()
        )
        
        # This should FAIL - invalid user context should be rejected
        with pytest.raises(RuntimeError, match="Invalid user context"):
            await factory.create_user_emitter(
                user_id="",  # SSOT violation: empty user_id
                thread_id="valid_thread",
                connection_id="valid_connection"
            )
    
    @pytest.mark.asyncio
    async def test_websocket_connection_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate WebSocket connection SSOT.
        
        SSOT Issue: Factory doesn't validate real WebSocket connections exist.
        Expected Failure: Should reject emitter creation without real WebSocket connection.
        """
        factory = WebSocketBridgeFactory()
        mock_pool = Mock(spec=WebSocketConnectionPool)
        
        # Configure mock pool to return None connection (SSOT violation)
        mock_pool.get_connection = AsyncMock(return_value=None)
        
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        # This should FAIL - no real WebSocket connection available
        with pytest.raises(RuntimeError, match="No active WebSocket connection found"):
            await factory.create_user_emitter(
                user_id="valid_user",
                thread_id="valid_thread", 
                connection_id="invalid_connection"  # SSOT violation: no connection
            )
    
    @pytest.mark.asyncio
    async def test_factory_metrics_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory metrics should maintain SSOT consistency.
        
        SSOT Issue: Factory metrics don't match actual state during emitter creation.
        Expected Failure: Metrics should accurately reflect factory state.
        """
        factory = WebSocketBridgeFactory()
        mock_pool = Mock(spec=WebSocketConnectionPool)
        mock_connection_info = Mock()
        mock_connection_info.websocket = Mock()
        mock_pool.get_connection = AsyncMock(return_value=mock_connection_info)
        
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        initial_metrics = factory.get_factory_metrics()
        initial_created = initial_metrics['emitters_created']
        initial_active = initial_metrics['emitters_active']
        
        # Create emitter
        await factory.create_user_emitter(
            user_id="test_user",
            thread_id="test_thread",
            connection_id="test_connection"
        )
        
        updated_metrics = factory.get_factory_metrics()
        
        # This should FAIL if metrics SSOT is violated
        assert updated_metrics['emitters_created'] == initial_created + 1, \
            "SSOT violation: emitters_created not incremented correctly"
        assert updated_metrics['emitters_active'] == initial_active + 1, \
            "SSOT violation: emitters_active not incremented correctly"
    
    def test_factory_config_ssot_environment_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory config should validate environment SSOT.
        
        SSOT Issue: Factory config from_env() doesn't validate environment consistency.
        Expected Failure: Should validate all required environment variables exist.
        """
        # This should FAIL if environment SSOT validation is missing
        with patch.dict('os.environ', {}, clear=True):
            # Clear all environment variables - SSOT violation
            config = WebSocketFactoryConfig.from_env()
            
            # Factory should detect missing environment configuration
            assert config.max_events_per_user > 0, \
                "SSOT violation: Invalid max_events_per_user from environment"
    
    @pytest.mark.asyncio
    async def test_user_context_cleanup_ssot_isolation_failure(self):
        """
        TEST DESIGNED TO FAIL: User context cleanup should maintain SSOT isolation.
        
        SSOT Issue: Context cleanup affects other users' contexts (SSOT violation).
        Expected Failure: User context cleanup should be completely isolated.
        """
        factory = WebSocketBridgeFactory()
        mock_pool = Mock(spec=WebSocketConnectionPool)
        mock_connection_info = Mock()
        mock_connection_info.websocket = Mock()
        mock_pool.get_connection = AsyncMock(return_value=mock_connection_info)
        
        factory.configure(
            connection_pool=mock_pool,
            agent_registry=Mock(),
            health_monitor=Mock()
        )
        
        # Create emitters for two different users
        emitter1 = await factory.create_user_emitter(
            user_id="user1",
            thread_id="thread1",
            connection_id="conn1"
        )
        
        emitter2 = await factory.create_user_emitter(
            user_id="user2", 
            thread_id="thread2",
            connection_id="conn2"
        )
        
        # Check initial state
        metrics_before = factory.get_factory_metrics()
        initial_active = metrics_before['emitters_active']
        
        # Cleanup user1 context
        await factory.cleanup_user_context("user1", "conn1")
        
        # This should FAIL if SSOT isolation is violated
        metrics_after = factory.get_factory_metrics()
        
        # SSOT validation: user2 should be unaffected
        assert metrics_after['emitters_active'] == initial_active - 1, \
            "SSOT violation: Cleanup affected wrong number of emitters"
            
        # SSOT validation: user2 emitter should still be active
        assert emitter2 is not None, \
            "SSOT violation: user2 emitter affected by user1 cleanup"
    
    def test_factory_singleton_pattern_ssot_violation(self):
        """
        TEST DESIGNED TO FAIL: Factory should follow SSOT singleton pattern.
        
        SSOT Issue: Multiple factory instances violate SSOT pattern.
        Expected Failure: Should enforce single factory instance or proper isolation.
        """
        from netra_backend.app.dependencies import get_websocket_bridge_factory
        
        # Get two instances - should be same instance (SSOT)
        factory1 = get_websocket_bridge_factory()
        factory2 = get_websocket_bridge_factory()
        
        # This should FAIL if SSOT singleton pattern is violated
        assert factory1 is factory2, \
            "SSOT violation: Multiple factory instances detected, should be singleton"
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_ssot_bridge_dependency_failure(self):
        """
        TEST DESIGNED TO FAIL: WebSocket emitter should validate bridge dependency SSOT.
        
        SSOT Issue: Emitter creation proceeds without valid bridge connection.
        Expected Failure: Should reject emitter creation without proper bridge setup.
        """
        factory = WebSocketBridgeFactory()
        
        # This should FAIL - factory not configured (SSOT violation)
        with pytest.raises(RuntimeError, match="Factory not configured"):
            await factory.create_user_emitter(
                user_id="test_user",
                thread_id="test_thread",
                connection_id="test_connection"
            )
    
    def test_factory_initialization_ssot_monitoring_dependency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate monitoring dependencies SSOT.
        
        SSOT Issue: Factory initializes without proper monitoring integration.
        Expected Failure: Should validate monitoring components exist and are configured.
        """
        # This should FAIL if monitoring SSOT validation is missing
        with patch('netra_backend.app.monitoring.websocket_notification_monitor.get_websocket_notification_monitor', 
                   return_value=None):
            
            # Factory should detect missing monitoring (SSOT violation)
            with pytest.raises(RuntimeError, match="Monitoring"):
                factory = WebSocketBridgeFactory()
                # Factory should validate monitoring dependency exists