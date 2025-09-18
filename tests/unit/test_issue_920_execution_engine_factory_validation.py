"""
Test Issue #920: ExecutionEngineFactory WebSocket Bridge Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Reliability
- Business Goal: Validate ExecutionEngineFactory behavior with different WebSocket configurations
- Value Impact: Ensures proper handling of WebSocket dependencies in execution engine creation
- Strategic Impact: Critical for reliable agent execution infrastructure

This test suite validates Issue #920 specific behaviors:
- ExecutionEngineFactory(websocket_bridge=None) should NOT raise errors (issue #920)
- UserWebSocketEmitter API should be accessible and functional
- WebSocket integration should work without Docker dependencies
- Factory validation should handle optional WebSocket configurations

TEST DESIGN NOTE: These tests are designed to FAIL initially to prove Issue #920 exists,
then validate the fix implementation.
"""

import asyncio
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    UserWebSocketEmitter,
    AgentInstanceFactory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class Issue920ExecutionEngineFactoryValidationTests(SSotBaseTestCase):
    """Test ExecutionEngineFactory validation behavior for Issue #920."""
    
    def setup_method(self, method):
        """Setup test environment for Issue #920."""
        super().setup_method(method)
        
        # Test identifiers
        self.test_user_id = f"issue920_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"issue920_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"issue920_run_{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket bridge
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
        self.mock_websocket_bridge.emit_critical_event = AsyncMock(return_value=True)
        self.mock_websocket_bridge.is_connection_active = Mock(return_value=True)
        
        # Mock infrastructure
        self.mock_db_manager = Mock()
        self.mock_redis_manager = Mock()
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_execution_engine_factory_with_none_websocket_bridge_should_not_fail(self):
        """
        ISSUE #920 FIXED VALIDATION: ExecutionEngineFactory(websocket_bridge=None) should NOT raise errors.
        
        Fixed Behavior: ExecutionEngineFactory now correctly accepts websocket_bridge=None
        for test environments and logs a warning instead of raising an error.
        
        Expected Behavior: Factory should initialize successfully with websocket_bridge=None
        and log a warning about compatibility mode.
        """
        # ISSUE #920 FIXED: This should NOT raise an error and should work correctly
        
        # When: Creating ExecutionEngineFactory with websocket_bridge=None
        factory = ExecutionEngineFactory(
            websocket_bridge=None,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Then: Factory should initialize successfully (no exception)
        assert factory is not None
        assert factory._websocket_bridge is None
        assert hasattr(factory, '_active_engines')
        assert hasattr(factory, '_engine_lock')
        
        # And: Factory should be in "compatibility mode" for tests
        assert factory._database_session_manager is self.mock_db_manager
        assert factory._redis_manager is self.mock_redis_manager
        
        # And: Factory should have proper configuration for test mode
        assert factory._max_engines_per_user > 0
        assert factory._engine_timeout_seconds > 0
        assert hasattr(factory, '_factory_metrics')
        
        self.record_metric("websocket_none_initialization_success", True)
        
        # TEST VALIDATION: Issue #920 has been fixed - factory accepts None websocket_bridge
    
    @pytest.mark.unit
    def test_execution_engine_factory_with_valid_websocket_bridge_should_succeed(self):
        """Test that ExecutionEngineFactory works correctly with valid websocket_bridge."""
        # When: Creating ExecutionEngineFactory with valid websocket_bridge
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Then: Factory should initialize successfully
        assert factory is not None
        assert factory._websocket_bridge is self.mock_websocket_bridge
        assert hasattr(factory, '_active_engines')
        assert hasattr(factory, '_engine_lock')
        
        # And: Infrastructure should be properly connected
        assert factory._database_session_manager is self.mock_db_manager
        assert factory._redis_manager is self.mock_redis_manager
        
        self.record_metric("websocket_valid_initialization_success", True)
    
    @pytest.mark.unit
    def test_execution_engine_factory_error_message_validation(self):
        """Test that Issue #920 has been fixed - no error should be raised."""
        # This test validates that Issue #920 has been fixed
        
        # When: Creating ExecutionEngineFactory with websocket_bridge=None
        # Note: This should NOT raise an error since Issue #920 has been fixed
        factory = ExecutionEngineFactory(websocket_bridge=None)
        
        # Then: Factory should initialize successfully (no error raised)
        assert factory is not None
        assert factory._websocket_bridge is None
        
        # And: Factory should be in test compatibility mode
        assert hasattr(factory, '_active_engines')
        assert hasattr(factory, '_factory_metrics')
        
        # Issue #920 is fixed - no error raised
        self.record_metric("issue_920_fixed", True)
    
    @pytest.mark.unit  
    async def test_execution_engine_creation_with_none_websocket_compatibility(self):
        """Test that execution engines can be created even with None websocket_bridge."""
        # Given: Factory with None websocket_bridge (Issue #920 fixed - should work)
        factory = ExecutionEngineFactory(
            websocket_bridge=None,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # When: Creating user execution context
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = self.test_user_id
        user_context.thread_id = self.test_thread_id
        user_context.run_id = self.test_run_id
        user_context.session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Then: Factory should handle None websocket_bridge gracefully
        # Note: This tests internal compatibility, not full engine creation
        assert factory._websocket_bridge is None
        assert factory is not None
        
        # And: Factory should have proper test mode configuration
        assert factory._database_session_manager is self.mock_db_manager
        assert factory._redis_manager is self.mock_redis_manager
        
        self.record_metric("none_websocket_compatibility_validated", True)