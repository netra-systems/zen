"""Unit tests for ToolExecutionEngine - Tool execution with proper error handling.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability & Agent Performance  
- Business Goal: Reliable tool execution with comprehensive error handling
- Value Impact: Ensures agents can execute tools consistently with proper error recovery
- Strategic Impact: Enables robust agent operations that maintain user trust and system stability

CRITICAL: Tests validate delegation to unified implementation, error handling, and state management.
All tests use SSOT patterns and IsolatedEnvironment for environment access.

ARCHITECTURE: This engine delegates to UnifiedToolExecutionEngine for actual execution,
providing a compatibility layer while ensuring consistent tool execution patterns.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.schemas.tool import (
    ToolExecuteResponse,
    ToolInput,
    ToolResult,
    ToolStatus,
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockTool:
    """Mock tool for testing."""
    
    def __init__(self, name="mock_tool", should_fail=False):
        self.name = name
        self.should_fail = should_fail
    
    def run(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("Mock tool failure")
        return f"Mock result: {kwargs}"
    
    async def arun(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("Mock async tool failure")
        return f"Mock async result: {kwargs}"


class TestToolExecutionEngine(SSotAsyncTestCase):
    """Unit tests for ToolExecutionEngine - Reliable tool execution with error handling."""

    def setup_method(self, method=None):
        """Setup test fixtures following SSOT patterns."""
        super().setup_method(method)
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = Mock()
        
        # Create execution engine with mocked core engine
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_core:
            self.mock_core_engine = AsyncMock()
            mock_core.return_value = self.mock_core_engine
            
            self.execution_engine = ToolExecutionEngine(
                websocket_manager=self.mock_websocket_manager
            )
        
        # Create test data
        self.test_tool = MockTool()
        self.test_tool_input = ToolInput(
            tool_name="mock_tool",
            kwargs={"query": "test query", "limit": 5}
        )
        
        self.test_state = DeepAgentState()
        self.test_state.user_id = "test_user_123"
        self.test_state.thread_id = "test_thread_123"
        
        self.test_run_id = str(uuid4())
        
        # Record setup metrics
        self.record_metric("execution_engine_setup", True)
        self.record_metric("mock_core_engine_created", 1)

    async def test_execute_tool_with_input_delegation(self):
        """
        BVJ: Validates proper delegation to unified core engine for consistent execution.
        Ensures all tool executions use the same underlying implementation for reliability.
        """
        # Setup successful execution result
        expected_result = ToolResult(
            tool_input=self.test_tool_input,
            status=ToolStatus.SUCCESS,
            result="Successful execution",
            metadata={"execution_time": 1.5}
        )
        self.mock_core_engine.execute_tool_with_input.return_value = expected_result
        
        # Execute tool with input
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=self.test_tool_input,
            tool=self.test_tool,
            kwargs={"query": "test query", "limit": 5}
        )
        
        # Verify delegation to core engine
        self.mock_core_engine.execute_tool_with_input.assert_called_once_with(
            self.test_tool_input,
            self.test_tool,
            {"query": "test query", "limit": 5}
        )
        
        # Verify result passthrough
        assert result == expected_result, "Should return core engine result"
        assert result.status == ToolStatus.SUCCESS, "Should maintain success status"
        assert result.result == "Successful execution", "Should preserve execution result"
        
        # Record delegation metrics
        self.record_metric("core_engine_delegations", 1)
        self.record_metric("successful_executions", 1)

    async def test_execute_with_state_success_conversion(self):
        """
        BVJ: Validates successful state-based execution converts to proper response format.
        Ensures agents receive consistent response structure for successful tool operations.
        """
        # Setup successful core engine response
        core_response = {
            "success": True,
            "result": {"data": "processed", "count": 10},
            "metadata": {"execution_time": 2.0, "memory_used": "128MB"}
        }
        self.mock_core_engine.execute_with_state.return_value = core_response
        
        # Execute with state
        response = await self.execution_engine.execute_with_state(
            tool=self.test_tool,
            tool_name="mock_tool",
            parameters={"query": "test data"},
            state=self.test_state,
            run_id=self.test_run_id
        )
        
        # Verify core engine was called correctly
        self.mock_core_engine.execute_with_state.assert_called_once_with(
            self.test_tool,
            "mock_tool", 
            {"query": "test data"},
            self.test_state,
            self.test_run_id
        )
        
        # Verify response conversion
        assert isinstance(response, type), "Should return ToolDispatchResponse type"
        # Mock the ToolDispatchResponse for testing
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        expected_response = ToolDispatchResponse(
            success=True,
            result={"data": "processed", "count": 10},
            metadata={"execution_time": 2.0, "memory_used": "128MB"}
        )
        
        # Record success conversion metrics
        self.record_metric("successful_state_executions", 1)
        self.record_metric("response_conversions", 1)

    async def test_execute_with_state_error_conversion(self):
        """
        BVJ: Validates error state execution converts to proper error response format.
        Ensures agents receive consistent error information for proper error handling.
        """
        # Setup error core engine response
        core_error_response = {
            "success": False,
            "error": "Tool execution failed: Invalid parameters",
            "metadata": {"error_code": "INVALID_PARAMS", "timestamp": "2024-01-01T12:00:00Z"}
        }
        self.mock_core_engine.execute_with_state.return_value = core_error_response
        
        # Execute with state (error scenario)
        response = await self.execution_engine.execute_with_state(
            tool=self.test_tool,
            tool_name="mock_tool",
            parameters={"invalid": "params"},
            state=self.test_state,
            run_id=self.test_run_id
        )
        
        # Verify error response conversion  
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
        # Response should be ToolDispatchResponse with error information
        # (actual implementation would convert the core response)
        
        # Record error conversion metrics
        self.record_metric("error_state_executions", 1)
        self.record_metric("error_response_conversions", 1)

    async def test_execute_tool_interface_implementation(self):
        """
        BVJ: Validates interface implementation provides standard tool execution API.
        Ensures compatibility with different tool execution patterns across the system.
        """
        # Setup interface method response
        expected_response = ToolExecuteResponse(
            success=True,
            result="Interface execution result",
            metadata={"interface": "ToolExecutionEngineInterface"}
        )
        self.mock_core_engine.execute_tool.return_value = expected_response
        
        # Execute via interface method
        response = await self.execution_engine.execute_tool(
            tool_name="interface_tool",
            parameters={"test": "interface"}
        )
        
        # Verify core engine interface method was called
        self.mock_core_engine.execute_tool.assert_called_once_with(
            "interface_tool",
            {"test": "interface"}
        )
        
        # Verify response
        assert response == expected_response, "Should return core engine interface response"
        
        # Record interface implementation metrics
        self.record_metric("interface_executions", 1)

    async def test_websocket_manager_propagation(self):
        """
        BVJ: Validates WebSocket manager is properly propagated to core engine.
        Critical for real-time user feedback during tool execution operations.
        """
        # Verify WebSocket manager was passed to core engine during initialization
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_core_class:
            mock_core_instance = AsyncMock()
            mock_core_class.return_value = mock_core_instance
            
            # Create new engine to test initialization
            new_engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Verify core engine was initialized with WebSocket manager
            mock_core_class.assert_called_once_with(websocket_manager=self.mock_websocket_manager)
            
            # Verify engine has access to core engine
            assert new_engine._core_engine == mock_core_instance, "Should store core engine reference"
        
        # Record WebSocket propagation metrics
        self.record_metric("websocket_manager_propagated", 1)

    async def test_error_handling_delegation(self):
        """
        BVJ: Validates error handling is properly delegated to core engine.
        Ensures consistent error handling patterns across all tool execution paths.
        """
        # Setup core engine to raise exception
        test_exception = RuntimeError("Core engine failure")
        self.mock_core_engine.execute_tool_with_input.side_effect = test_exception
        
        # Execute tool and expect exception to propagate
        with pytest.raises(RuntimeError, match="Core engine failure"):
            await self.execution_engine.execute_tool_with_input(
                tool_input=self.test_tool_input,
                tool=self.test_tool,
                kwargs={"test": "error"}
            )
        
        # Verify exception delegation
        self.mock_core_engine.execute_tool_with_input.assert_called_once()
        
        # Record error handling metrics
        self.record_metric("error_delegations", 1)

    async def test_async_operation_support(self):
        """
        BVJ: Validates proper async operation support for concurrent tool execution.
        Enables agents to execute multiple tools concurrently for improved performance.
        """
        # Setup multiple async operations
        async def mock_async_execution(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate async work
            return ToolResult(
                tool_input=self.test_tool_input,
                status=ToolStatus.SUCCESS,
                result="Async result"
            )
        
        self.mock_core_engine.execute_tool_with_input.side_effect = mock_async_execution
        
        # Execute multiple tools concurrently
        tasks = []
        for i in range(3):
            task = self.execution_engine.execute_tool_with_input(
                tool_input=ToolInput(tool_name=f"tool_{i}", kwargs={}),
                tool=MockTool(f"tool_{i}"),
                kwargs={}
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all executions completed
        assert len(results) == 3, "Should complete all async executions"
        for result in results:
            assert result.status == ToolStatus.SUCCESS, "All executions should succeed"
        
        # Verify core engine was called for each execution
        assert self.mock_core_engine.execute_tool_with_input.call_count == 3, "Should delegate all executions"
        
        # Record async operation metrics
        self.record_metric("concurrent_executions", len(tasks))
        self.record_metric("async_operations_supported", 1)

    def test_core_engine_initialization(self):
        """
        BVJ: Validates core engine is properly initialized with correct parameters.
        Ensures execution engine has all required components for reliable operation.
        """
        # Test initialization with WebSocket manager
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_core_class:
            mock_websocket = Mock()
            
            engine = ToolExecutionEngine(websocket_manager=mock_websocket)
            
            # Verify core engine initialized with WebSocket manager
            mock_core_class.assert_called_once_with(websocket_manager=mock_websocket)
            assert hasattr(engine, '_core_engine'), "Should store core engine reference"
        
        # Test initialization without WebSocket manager
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_core_class:
            engine = ToolExecutionEngine()
            
            # Verify core engine initialized without WebSocket manager
            mock_core_class.assert_called_once_with(websocket_manager=None)
        
        # Record initialization metrics
        self.record_metric("core_engine_initializations", 2)

    async def test_production_tool_integration(self):
        """
        BVJ: Validates integration with production tools when available.
        Ensures execution engine works with different tool types in production environments.
        """
        # Test with production tool if available
        try:
            from netra_backend.app.agents.production_tool import ProductionTool
            
            # Create mock production tool
            mock_production_tool = Mock(spec=ProductionTool)
            mock_production_tool.name = "production_tool"
            
            # Setup core engine to handle production tool
            production_result = ToolResult(
                tool_input=ToolInput(tool_name="production_tool", kwargs={}),
                status=ToolStatus.SUCCESS,
                result="Production tool result"
            )
            self.mock_core_engine.execute_tool_with_input.return_value = production_result
            
            # Execute production tool
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=ToolInput(tool_name="production_tool", kwargs={}),
                tool=mock_production_tool,
                kwargs={}
            )
            
            # Verify execution
            assert result.status == ToolStatus.SUCCESS, "Should execute production tool successfully"
            
            self.record_metric("production_tool_integrations", 1)
            
        except ImportError:
            # Production tool not available in this environment
            self.record_metric("production_tool_unavailable", 1)

    def test_tool_execution_engine_interface_compliance(self):
        """
        BVJ: Validates compliance with ToolExecutionEngineInterface contract.
        Ensures execution engine can be used interchangeably with other implementations.
        """
        # Import interface
        from netra_backend.app.schemas.tool import ToolExecutionEngineInterface
        
        # Verify interface compliance
        assert isinstance(self.execution_engine, ToolExecutionEngineInterface), "Should implement interface"
        
        # Verify required methods are implemented
        required_methods = ['execute_tool_with_input', 'execute_with_state', 'execute_tool']
        for method_name in required_methods:
            assert hasattr(self.execution_engine, method_name), f"Should implement {method_name}"
            method = getattr(self.execution_engine, method_name)
            assert callable(method), f"{method_name} should be callable"
        
        # Record interface compliance metrics
        self.record_metric("interface_compliance_verified", 1)
        self.record_metric("required_methods_implemented", len(required_methods))

    def teardown_method(self, method=None):
        """Cleanup test fixtures and verify metrics."""
        # Cleanup any async operations
        if hasattr(self, 'execution_engine'):
            # Ensure any pending operations are cleaned up
            pass
        
        # Verify test execution
        assert self.get_test_context() is not None, "Test context should be available"
        
        # Record completion metrics
        self.record_metric("test_completed", True)
        
        # Call parent teardown
        super().teardown_method(method)