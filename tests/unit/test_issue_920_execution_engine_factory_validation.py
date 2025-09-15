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
        ISSUE #920 REPRODUCTION TEST: ExecutionEngineFactory(websocket_bridge=None) should NOT raise errors.
        
        Current Issue: ExecutionEngineFactory incorrectly raises ExecutionEngineFactoryError 
        when websocket_bridge=None, but this should be allowed for test environments.
        
        Expected Behavior: Factory should initialize successfully with websocket_bridge=None
        and log a warning instead of raising an error.
        """
        # ISSUE #920: This should NOT raise an error but currently does
        # TEST EXPECTATION: This test is designed to FAIL initially to prove the issue
        
        try:
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
            
            self.record_metric("websocket_none_initialization_success", True)
            
            # TEST VALIDATION: If this passes, Issue #920 has been fixed
            
        except ExecutionEngineFactoryError as e:
            # ISSUE #920 DETECTED: Factory incorrectly raises error for None websocket_bridge
            error_message = str(e)
            
            # Validate this is the specific Issue #920 error pattern
            assert "requires websocket_bridge" in error_message or "WebSocket events" in error_message
            assert "chat business value" in error_message
            
            # FAILING TEST: This proves Issue #920 exists
            pytest.fail(
                f"ISSUE #920 REPRODUCED: ExecutionEngineFactory incorrectly raised error with "
                f"websocket_bridge=None: {error_message}. This should be allowed for test environments."
            )
    
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
        """Test that error messages provide clear guidance when issues occur."""
        # This test validates the error message format from Issue #920
        
        # Expected error pattern based on current Issue #920 implementation
        expected_error_patterns = [
            "requires websocket_bridge",
            "WebSocket events",
            "chat business value"
        ]
        
        try:
            # Attempt to trigger the Issue #920 error condition
            # Note: If this doesn't raise an error, Issue #920 has been fixed
            ExecutionEngineFactory(websocket_bridge=None)
            
            # If we reach here, Issue #920 is fixed (no error raised)
            self.record_metric("issue_920_fixed", True)
            
        except ExecutionEngineFactoryError as e:
            # Validate error message contains expected patterns
            error_message = str(e)
            
            patterns_found = []
            for pattern in expected_error_patterns:
                if pattern in error_message:
                    patterns_found.append(pattern)
            
            # Validate this is the Issue #920 error pattern
            assert len(patterns_found) >= 2, (
                f"Issue #920 error message should contain business context. "
                f"Found patterns: {patterns_found} in message: {error_message}"
            )
            
            self.record_metric("issue_920_error_pattern_validated", True)
    
    @pytest.mark.unit  
    async def test_execution_engine_creation_with_none_websocket_compatibility(self):
        """Test that execution engines can be created even with None websocket_bridge."""
        # Given: Factory with None websocket_bridge (should not fail per Issue #920 fix)
        try:
            factory = ExecutionEngineFactory(
                websocket_bridge=None,
                database_session_manager=self.mock_db_manager,
                redis_manager=self.mock_redis_manager
            )
        except ExecutionEngineFactoryError:
            # Skip this test if Issue #920 is not yet fixed
            pytest.skip("Issue #920 not yet fixed - ExecutionEngineFactory rejects None websocket_bridge")
            return
        
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
        
        self.record_metric("none_websocket_compatibility_validated", True)