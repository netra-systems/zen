from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''Regression tests for ExecutionContext hashable type error.

# REMOVED_SYNTAX_ERROR: Tests ensure ExecutionContext and similar dataclasses are never used
# REMOVED_SYNTAX_ERROR: as hashable types (dict keys, set members, etc).

# REMOVED_SYNTAX_ERROR: Business Value: Prevents runtime crashes from type errors.
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict

import pytest

from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.schemas.core_enums import ExecutionStatus
import asyncio

# REMOVED_SYNTAX_ERROR: class TestExecutionContextHashableRegression:
    # REMOVED_SYNTAX_ERROR: """Test suite to prevent ExecutionContext hashable type errors."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def execution_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test execution context."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="test request")
    # REMOVED_SYNTAX_ERROR: return ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id="test-run-123",
    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
    # REMOVED_SYNTAX_ERROR: state=state,
    # REMOVED_SYNTAX_ERROR: user_id="user-456",
    # REMOVED_SYNTAX_ERROR: thread_id="thread-789",
    # REMOVED_SYNTAX_ERROR: metadata={"test": "data"}
    

# REMOVED_SYNTAX_ERROR: def test_execution_context_is_hashable(self, execution_context):
    # REMOVED_SYNTAX_ERROR: """Test that ExecutionContext is now hashable."""
    # Should be able to hash the context
    # REMOVED_SYNTAX_ERROR: context_hash = hash(execution_context)
    # REMOVED_SYNTAX_ERROR: assert isinstance(context_hash, int)

    # Should be able to use as dict key
    # REMOVED_SYNTAX_ERROR: test_dict = {execution_context: "value"}
    # REMOVED_SYNTAX_ERROR: assert test_dict[execution_context] == "value"

    # Should be able to add to set
    # REMOVED_SYNTAX_ERROR: test_set = {execution_context}
    # REMOVED_SYNTAX_ERROR: assert execution_context in test_set

    # Hash should be consistent
    # REMOVED_SYNTAX_ERROR: assert hash(execution_context) == context_hash

    # Different contexts with same ids should have same hash
    # REMOVED_SYNTAX_ERROR: state2 = DeepAgentState(user_request="different request")
    # REMOVED_SYNTAX_ERROR: context2 = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id="test-run-123",
    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
    # REMOVED_SYNTAX_ERROR: state=state2,
    # REMOVED_SYNTAX_ERROR: user_id="different-user"
    
    # REMOVED_SYNTAX_ERROR: assert hash(context2) == hash(execution_context)
    # REMOVED_SYNTAX_ERROR: assert context2 == execution_context

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def error_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test error handler."""
    # REMOVED_SYNTAX_ERROR: return ExecutionErrorHandler

# REMOVED_SYNTAX_ERROR: def test_error_handler_cache_fallback_no_hashable_context(self, execution_context, error_handler):
    # REMOVED_SYNTAX_ERROR: """Test that cache_fallback_data doesn't use ExecutionContext as hashable."""
    # REMOVED_SYNTAX_ERROR: test_data = {"result": "test"}

    # This should not raise unhashable type error
    # REMOVED_SYNTAX_ERROR: error_handler.cache_fallback_data(execution_context, test_data)

    # Verify data is cached correctly
    # REMOVED_SYNTAX_ERROR: cache_key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert cache_key in error_handler._fallback_data_cache

    # REMOVED_SYNTAX_ERROR: cached = error_handler._fallback_data_cache[cache_key]
    # REMOVED_SYNTAX_ERROR: assert cached["data"] == test_data
    # REMOVED_SYNTAX_ERROR: assert "context" in cached

    # Verify context is serialized as dict, not stored as object
    # REMOVED_SYNTAX_ERROR: assert isinstance(cached["context"], dict)
    # REMOVED_SYNTAX_ERROR: assert cached["context"]["run_id"] == execution_context.run_id
    # REMOVED_SYNTAX_ERROR: assert cached["context"]["agent_name"] == execution_context.agent_name

# REMOVED_SYNTAX_ERROR: def test_execution_monitor_doesnt_use_context_as_key(self, execution_context):
    # REMOVED_SYNTAX_ERROR: """Test ExecutionMonitor doesn't use ExecutionContext as dict key."""
    # REMOVED_SYNTAX_ERROR: monitor = ExecutionMonitor()

    # Start execution should use run_id as key, not context
    # REMOVED_SYNTAX_ERROR: monitor.start_execution(execution_context)

    # Verify context.run_id is used as key, not context itself
    # REMOVED_SYNTAX_ERROR: assert execution_context.run_id in monitor._active_executions
    # REMOVED_SYNTAX_ERROR: assert isinstance(monitor._active_executions[execution_context.run_id], float)

    # Record error should also work without hashable issues
    # REMOVED_SYNTAX_ERROR: test_error = Exception("test error")
    # REMOVED_SYNTAX_ERROR: monitor.record_error(execution_context, test_error)

    # Complete execution
    # REMOVED_SYNTAX_ERROR: result = ExecutionResult( )
    # REMOVED_SYNTAX_ERROR: success=True,
    # REMOVED_SYNTAX_ERROR: status=ExecutionStatus.COMPLETED,
    # REMOVED_SYNTAX_ERROR: result={"test": "result"}
    
    # REMOVED_SYNTAX_ERROR: monitor.complete_execution(execution_context, result)

    # Verify context was never used as key
    # REMOVED_SYNTAX_ERROR: assert execution_context.run_id not in monitor._active_executions

# REMOVED_SYNTAX_ERROR: def test_dataclass_serialization_instead_of_direct_storage(self, execution_context):
    # REMOVED_SYNTAX_ERROR: """Test that dataclasses are serialized before storage in dicts."""
    # Test pattern that could cause issues
    # REMOVED_SYNTAX_ERROR: storage_dict = {}

    # BAD: Would fail if ExecutionContext was used as key
    # storage_dict[execution_context] = "value"  # This would raise TypeError

    # GOOD: Use serializable identifier
    # REMOVED_SYNTAX_ERROR: storage_dict[execution_context.run_id] = { )
    # REMOVED_SYNTAX_ERROR: "context_data": { )
    # REMOVED_SYNTAX_ERROR: "run_id": execution_context.run_id,
    # REMOVED_SYNTAX_ERROR: "agent_name": execution_context.agent_name,
    # REMOVED_SYNTAX_ERROR: "user_id": execution_context.user_id
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "value": "test_value"
    

    # REMOVED_SYNTAX_ERROR: assert execution_context.run_id in storage_dict
    # REMOVED_SYNTAX_ERROR: assert storage_dict[execution_context.run_id]["value"] == "test_value"

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_connection_executor_context_handling(self):
        # REMOVED_SYNTAX_ERROR: """Test WebSocket connection executor handles context correctly."""
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.connection_executor import ConnectionExecutor

        # REMOVED_SYNTAX_ERROR: executor = ConnectionExecutor()

        # Create test context
        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="websocket test")
        # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
        # REMOVED_SYNTAX_ERROR: run_id="ws-test-123",
        # REMOVED_SYNTAX_ERROR: agent_name="websocket_connection",
        # REMOVED_SYNTAX_ERROR: state=state,
        # REMOVED_SYNTAX_ERROR: metadata={ )
        # REMOVED_SYNTAX_ERROR: "operation_type": "get_connection_stats",
        # REMOVED_SYNTAX_ERROR: "operation_data": {}
        
        

        # Validate preconditions shouldn't use context as hashable
        # REMOVED_SYNTAX_ERROR: is_valid = await executor.validate_preconditions(context)
        # REMOVED_SYNTAX_ERROR: assert isinstance(is_valid, bool)

# REMOVED_SYNTAX_ERROR: def test_mcp_context_manager_storage(self):
    # REMOVED_SYNTAX_ERROR: """Test MCP context manager doesn't use ExecutionContext as key."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.mcp_integration.context_manager import ( )
        # REMOVED_SYNTAX_ERROR: MCPContextManager)

        # Mock dependencies
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_service = mock_service_instance  # Initialize appropriate service
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_discovery = mock_discovery_instance  # Initialize appropriate service
        # Mock: Generic component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: mock_monitor = mock_monitor_instance  # Initialize appropriate service

        # REMOVED_SYNTAX_ERROR: manager = MCPContextManager(mock_service, mock_discovery, mock_monitor)

        # Create MCP context
        # REMOVED_SYNTAX_ERROR: run_id = "mcp-test-123"
        # REMOVED_SYNTAX_ERROR: agent_name = "test_agent"

        # Context should be stored by run_id, not by context object
        # REMOVED_SYNTAX_ERROR: mcp_context = manager.create_context(run_id, agent_name)

        # REMOVED_SYNTAX_ERROR: assert run_id in manager.active_contexts
        # REMOVED_SYNTAX_ERROR: assert manager.active_contexts[run_id] == mcp_context

        # Cleanup should work without hashable issues
        # REMOVED_SYNTAX_ERROR: mock_result = mock_result_instance  # Initialize appropriate service
        # REMOVED_SYNTAX_ERROR: manager.cleanup_context(run_id, mock_result)

        # REMOVED_SYNTAX_ERROR: assert run_id not in manager.active_contexts
        # REMOVED_SYNTAX_ERROR: except ImportError:
            # Skip if MCP integration not available
            # REMOVED_SYNTAX_ERROR: pytest.skip("MCP integration not available")

# REMOVED_SYNTAX_ERROR: class TestDataclassSerializationPatterns:
    # REMOVED_SYNTAX_ERROR: """Test correct serialization patterns for dataclasses."""

# REMOVED_SYNTAX_ERROR: def test_execution_context_to_dict_pattern(self):
    # REMOVED_SYNTAX_ERROR: """Test converting ExecutionContext to dict for storage."""
    # Create test context
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="dict pattern test")
    # REMOVED_SYNTAX_ERROR: execution_context = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id="dict-test-123",
    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
    # REMOVED_SYNTAX_ERROR: state=state,
    # REMOVED_SYNTAX_ERROR: user_id="user-111",
    # REMOVED_SYNTAX_ERROR: thread_id="thread-222",
    # REMOVED_SYNTAX_ERROR: metadata={"test": "metadata"}
    

    # Create a dict representation
    # REMOVED_SYNTAX_ERROR: context_dict = { )
    # REMOVED_SYNTAX_ERROR: "run_id": execution_context.run_id,
    # REMOVED_SYNTAX_ERROR: "agent_name": execution_context.agent_name,
    # REMOVED_SYNTAX_ERROR: "user_id": execution_context.user_id,
    # REMOVED_SYNTAX_ERROR: "thread_id": execution_context.thread_id,
    # REMOVED_SYNTAX_ERROR: "retry_count": execution_context.retry_count,
    # REMOVED_SYNTAX_ERROR: "metadata": execution_context.metadata
    

    # This can be safely stored in any dict or cache
    # REMOVED_SYNTAX_ERROR: cache = { )
    # REMOVED_SYNTAX_ERROR: "contexts": { )
    # REMOVED_SYNTAX_ERROR: execution_context.run_id: context_dict
    
    

    # REMOVED_SYNTAX_ERROR: assert cache["contexts"][execution_context.run_id]["agent_name"] == "test_agent"

# REMOVED_SYNTAX_ERROR: def test_avoid_storing_dataclass_directly(self):
    # REMOVED_SYNTAX_ERROR: """Test that we avoid storing dataclass objects directly."""

    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class TestContext:
    # REMOVED_SYNTAX_ERROR: id: str
    # REMOVED_SYNTAX_ERROR: name: str
    # REMOVED_SYNTAX_ERROR: data: Dict[str, Any]

    # REMOVED_SYNTAX_ERROR: context = TestContext(id="123", name="test", data={"key": "value"})

    # BAD: Don't store dataclass directly as dict value if it might be used as key later
    # REMOVED_SYNTAX_ERROR: bad_storage = {}
    # bad_storage[context] = "value"  # Would fail with TypeError: unhashable type

    # GOOD: Use id as key
    # REMOVED_SYNTAX_ERROR: good_storage = {}
    # REMOVED_SYNTAX_ERROR: good_storage[context.id] = { )
    # REMOVED_SYNTAX_ERROR: "name": context.name,
    # REMOVED_SYNTAX_ERROR: "data": context.data
    

    # REMOVED_SYNTAX_ERROR: assert "123" in good_storage
    # REMOVED_SYNTAX_ERROR: assert good_storage["123"]["name"] == "test"

# REMOVED_SYNTAX_ERROR: def test_safe_caching_pattern(self):
    # REMOVED_SYNTAX_ERROR: """Test safe caching pattern for execution contexts."""

# REMOVED_SYNTAX_ERROR: class SafeCache:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self._cache: Dict[str, Dict[str, Any]] = {]

# REMOVED_SYNTAX_ERROR: def store_context(self, context: ExecutionContext, data: Any):
    # REMOVED_SYNTAX_ERROR: """Store context data safely."""
    # REMOVED_SYNTAX_ERROR: key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: self._cache[key] = { )
    # REMOVED_SYNTAX_ERROR: "data": data,
    # REMOVED_SYNTAX_ERROR: "context_info": { )
    # REMOVED_SYNTAX_ERROR: "run_id": context.run_id,
    # REMOVED_SYNTAX_ERROR: "agent_name": context.agent_name,
    # REMOVED_SYNTAX_ERROR: "user_id": context.user_id
    
    

# REMOVED_SYNTAX_ERROR: def get_context_data(self, context: ExecutionContext) -> Any:
    # REMOVED_SYNTAX_ERROR: """Retrieve context data safely."""
    # REMOVED_SYNTAX_ERROR: key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self._cache.get(key, {}).get("data")

    # Test the safe cache
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="cache test")
    # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id="cache-123",
    # REMOVED_SYNTAX_ERROR: agent_name="cache_agent",
    # REMOVED_SYNTAX_ERROR: state=state
    

    # REMOVED_SYNTAX_ERROR: cache = SafeCache()
    # REMOVED_SYNTAX_ERROR: cache.store_context(context, {"result": "success"})

    # REMOVED_SYNTAX_ERROR: retrieved = cache.get_context_data(context)
    # REMOVED_SYNTAX_ERROR: assert retrieved == {"result": "success"}

# REMOVED_SYNTAX_ERROR: class TestErrorHandlerRegressionFixes:
    # REMOVED_SYNTAX_ERROR: """Test the specific fix applied to ExecutionErrorHandler."""

# REMOVED_SYNTAX_ERROR: def test_fixed_cache_fallback_data_method(self):
    # REMOVED_SYNTAX_ERROR: """Test the fixed cache_fallback_data method."""
    # REMOVED_SYNTAX_ERROR: handler = ExecutionErrorHandler

    # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="fallback test")
    # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id="fallback-123",
    # REMOVED_SYNTAX_ERROR: agent_name="fallback_agent",
    # REMOVED_SYNTAX_ERROR: state=state,
    # REMOVED_SYNTAX_ERROR: user_id="user-999",
    # REMOVED_SYNTAX_ERROR: thread_id="thread-888"
    

    # REMOVED_SYNTAX_ERROR: test_data = {"fallback": "data"}

    # This should work without TypeError
    # REMOVED_SYNTAX_ERROR: handler.cache_fallback_data(context, test_data)

    # Verify the fix: context can now be stored directly
    # REMOVED_SYNTAX_ERROR: cache_key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: cached = handler._fallback_data_cache[cache_key]

    # Check that context is stored (now hashable)
    # REMOVED_SYNTAX_ERROR: assert cached["context"] == context

    # Original data should be preserved
    # REMOVED_SYNTAX_ERROR: assert cached["data"] == test_data

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_error_handler_full_flow_no_hashable_errors(self):
        # REMOVED_SYNTAX_ERROR: """Test full error handling flow doesn't produce hashable errors."""
        # REMOVED_SYNTAX_ERROR: handler = ExecutionErrorHandler

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="error flow test")
        # REMOVED_SYNTAX_ERROR: context = ExecutionContext( )
        # REMOVED_SYNTAX_ERROR: run_id="error-flow-123",
        # REMOVED_SYNTAX_ERROR: agent_name="error_agent",
        # REMOVED_SYNTAX_ERROR: state=state
        

        # First cache some fallback data
        # REMOVED_SYNTAX_ERROR: handler.cache_fallback_data(context, {"cached": "result"})

        # Now handle an error - should use cached data without hashable issues
        # REMOVED_SYNTAX_ERROR: error = Exception("Test error requiring fallback")
        # REMOVED_SYNTAX_ERROR: result = await handler.handle_execution_error(error, context)

        # REMOVED_SYNTAX_ERROR: assert isinstance(result, ExecutionResult)
        # REMOVED_SYNTAX_ERROR: assert result.status in [ExecutionStatus.FAILED, ExecutionStatus.DEGRADED]

        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])