"""Regression tests for ExecutionContext hashable type error.

Tests ensure ExecutionContext and similar dataclasses are never used 
as hashable types (dict keys, set members, etc).

Business Value: Prevents runtime crashes from type errors.
"""

import pytest
from dataclasses import dataclass, asdict
from typing import Dict, Any
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.agents.base.interface import ExecutionContext, ExecutionResult, ExecutionStatus
from app.agents.base.error_handler import ExecutionErrorHandler
from app.agents.base.monitoring import ExecutionMonitor
from app.schemas.agent_models import DeepAgentState


class TestExecutionContextHashableRegression:
    """Test suite to prevent ExecutionContext hashable type errors."""
    
    @pytest.fixture
    def execution_context(self):
        """Create test execution context."""
        state = DeepAgentState(user_request="test request")
        return ExecutionContext(
            run_id="test-run-123",
            agent_name="test_agent",
            state=state,
            user_id="user-456",
            thread_id="thread-789",
            metadata={"test": "data"}
        )
    
    @pytest.fixture
    def error_handler(self):
        """Create test error handler."""
        return ExecutionErrorHandler()
    
    def test_error_handler_cache_fallback_no_hashable_context(self, execution_context, error_handler):
        """Test that cache_fallback_data doesn't use ExecutionContext as hashable."""
        test_data = {"result": "test"}
        
        # This should not raise unhashable type error
        error_handler.cache_fallback_data(execution_context, test_data)
        
        # Verify data is cached correctly
        cache_key = f"{execution_context.agent_name}_{execution_context.run_id}"
        assert cache_key in error_handler._fallback_data_cache
        
        cached = error_handler._fallback_data_cache[cache_key]
        assert cached["data"] == test_data
        assert "context" in cached
        
        # Verify context is serialized as dict, not stored as object
        assert isinstance(cached["context"], dict)
        assert cached["context"]["run_id"] == execution_context.run_id
        assert cached["context"]["agent_name"] == execution_context.agent_name
    
    def test_execution_monitor_doesnt_use_context_as_key(self, execution_context):
        """Test ExecutionMonitor doesn't use ExecutionContext as dict key."""
        monitor = ExecutionMonitor()
        
        # Start execution should use run_id as key, not context
        monitor.start_execution(execution_context)
        
        # Verify context.run_id is used as key, not context itself
        assert execution_context.run_id in monitor._active_executions
        assert isinstance(monitor._active_executions[execution_context.run_id], float)
        
        # Record error should also work without hashable issues
        test_error = Exception("test error")
        monitor.record_error(execution_context, test_error)
        
        # Complete execution
        result = ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result={"test": "result"}
        )
        monitor.complete_execution(execution_context, result)
        
        # Verify context was never used as key
        assert execution_context.run_id not in monitor._active_executions
    
    def test_dataclass_serialization_instead_of_direct_storage(self, execution_context):
        """Test that dataclasses are serialized before storage in dicts."""
        # Test pattern that could cause issues
        storage_dict = {}
        
        # BAD: Would fail if ExecutionContext was used as key
        # storage_dict[execution_context] = "value"  # This would raise TypeError
        
        # GOOD: Use serializable identifier
        storage_dict[execution_context.run_id] = {
            "context_data": {
                "run_id": execution_context.run_id,
                "agent_name": execution_context.agent_name,
                "user_id": execution_context.user_id
            },
            "value": "test_value"
        }
        
        assert execution_context.run_id in storage_dict
        assert storage_dict[execution_context.run_id]["value"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_executor_context_handling(self):
        """Test WebSocket connection executor handles context correctly."""
        from app.websocket.connection_executor import ConnectionExecutor
        
        executor = ConnectionExecutor()
        
        # Create test context
        state = DeepAgentState(user_request="websocket test")
        context = ExecutionContext(
            run_id="ws-test-123",
            agent_name="websocket_connection",
            state=state,
            metadata={
                "operation_type": "get_connection_stats",
                "operation_data": {}
            }
        )
        
        # Validate preconditions shouldn't use context as hashable
        is_valid = await executor.validate_preconditions(context)
        assert isinstance(is_valid, bool)
    
    def test_mcp_context_manager_storage(self):
        """Test MCP context manager doesn't use ExecutionContext as key."""
        from app.agents.mcp_integration.context_manager import MCPContextManager
        
        # Mock dependencies
        mock_service = Mock()
        mock_discovery = Mock()
        mock_monitor = Mock()
        
        manager = MCPContextManager(mock_service, mock_discovery, mock_monitor)
        
        # Create MCP context
        run_id = "mcp-test-123"
        agent_name = "test_agent"
        
        # Context should be stored by run_id, not by context object
        mcp_context = manager.create_context(run_id, agent_name)
        
        assert run_id in manager.active_contexts
        assert manager.active_contexts[run_id] == mcp_context
        
        # Cleanup should work without hashable issues
        mock_result = Mock()
        manager.cleanup_context(run_id, mock_result)
        
        assert run_id not in manager.active_contexts


class TestDataclassSerializationPatterns:
    """Test correct serialization patterns for dataclasses."""
    
    def test_execution_context_to_dict_pattern(self):
        """Test converting ExecutionContext to dict for storage."""
        # Create test context
        state = DeepAgentState(user_request="dict pattern test")
        execution_context = ExecutionContext(
            run_id="dict-test-123",
            agent_name="test_agent",
            state=state,
            user_id="user-111",
            thread_id="thread-222",
            metadata={"test": "metadata"}
        )
        
        # Create a dict representation
        context_dict = {
            "run_id": execution_context.run_id,
            "agent_name": execution_context.agent_name,
            "user_id": execution_context.user_id,
            "thread_id": execution_context.thread_id,
            "retry_count": execution_context.retry_count,
            "metadata": execution_context.metadata
        }
        
        # This can be safely stored in any dict or cache
        cache = {
            "contexts": {
                execution_context.run_id: context_dict
            }
        }
        
        assert cache["contexts"][execution_context.run_id]["agent_name"] == "test_agent"
    
    def test_avoid_storing_dataclass_directly(self):
        """Test that we avoid storing dataclass objects directly."""
        
        @dataclass
        class TestContext:
            id: str
            name: str
            data: Dict[str, Any]
        
        context = TestContext(id="123", name="test", data={"key": "value"})
        
        # BAD: Don't store dataclass directly as dict value if it might be used as key later
        bad_storage = {}
        # bad_storage[context] = "value"  # Would fail with TypeError: unhashable type
        
        # GOOD: Use id as key
        good_storage = {}
        good_storage[context.id] = {
            "name": context.name,
            "data": context.data
        }
        
        assert "123" in good_storage
        assert good_storage["123"]["name"] == "test"
    
    def test_safe_caching_pattern(self):
        """Test safe caching pattern for execution contexts."""
        
        class SafeCache:
            def __init__(self):
                self._cache: Dict[str, Dict[str, Any]] = {}
            
            def store_context(self, context: ExecutionContext, data: Any):
                """Store context data safely."""
                key = f"{context.agent_name}:{context.run_id}"
                self._cache[key] = {
                    "data": data,
                    "context_info": {
                        "run_id": context.run_id,
                        "agent_name": context.agent_name,
                        "user_id": context.user_id
                    }
                }
            
            def get_context_data(self, context: ExecutionContext) -> Any:
                """Retrieve context data safely."""
                key = f"{context.agent_name}:{context.run_id}"
                return self._cache.get(key, {}).get("data")
        
        # Test the safe cache
        state = DeepAgentState(user_request="cache test")
        context = ExecutionContext(
            run_id="cache-123",
            agent_name="cache_agent",
            state=state
        )
        
        cache = SafeCache()
        cache.store_context(context, {"result": "success"})
        
        retrieved = cache.get_context_data(context)
        assert retrieved == {"result": "success"}


class TestErrorHandlerRegressionFixes:
    """Test the specific fix applied to ExecutionErrorHandler."""
    
    def test_fixed_cache_fallback_data_method(self):
        """Test the fixed cache_fallback_data method."""
        handler = ExecutionErrorHandler()
        
        state = DeepAgentState(user_request="fallback test")
        context = ExecutionContext(
            run_id="fallback-123",
            agent_name="fallback_agent",
            state=state,
            user_id="user-999",
            thread_id="thread-888"
        )
        
        test_data = {"fallback": "data"}
        
        # This should work without TypeError
        handler.cache_fallback_data(context, test_data)
        
        # Verify the fix: context is stored as dict, not as object
        cache_key = f"{context.agent_name}_{context.run_id}"
        cached = handler._fallback_data_cache[cache_key]
        
        # Check that context is stored as dict with specific fields
        assert isinstance(cached["context"], dict)
        assert cached["context"]["run_id"] == "fallback-123"
        assert cached["context"]["agent_name"] == "fallback_agent"
        assert cached["context"]["user_id"] == "user-999"
        assert cached["context"]["thread_id"] == "thread-888"
        
        # Original data should be preserved
        assert cached["data"] == test_data
    
    @pytest.mark.asyncio
    async def test_error_handler_full_flow_no_hashable_errors(self):
        """Test full error handling flow doesn't produce hashable errors."""
        handler = ExecutionErrorHandler()
        
        state = DeepAgentState(user_request="error flow test")
        context = ExecutionContext(
            run_id="error-flow-123",
            agent_name="error_agent",
            state=state
        )
        
        # First cache some fallback data
        handler.cache_fallback_data(context, {"cached": "result"})
        
        # Now handle an error - should use cached data without hashable issues
        error = Exception("Test error requiring fallback")
        result = await handler.handle_execution_error(error, context)
        
        assert isinstance(result, ExecutionResult)
        assert result.status in [ExecutionStatus.FAILED, ExecutionStatus.DEGRADED]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])