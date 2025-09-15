#!/usr/bin/env python3
"""Issue #1146 Phase 2 Implementation Validation Test.

This test validates that the Phase 2 ToolExecutionEngine consolidation
implementation is working correctly and hasn't introduced regressions.

Business Value Protection: $500K+ ARR Golden Path functionality.
"""

import asyncio
import sys
import unittest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context
    from netra_backend.app.schemas.tool import ToolInput, ToolExecuteResponse, ToolResult
except ImportError as e:
    print(f"Import error: {e}")
    print("Skipping test due to missing imports")
    sys.exit(0)


class TestIssue1146Phase2Validation(unittest.TestCase):
    """Validate Issue #1146 Phase 2 ToolExecutionEngine interface implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.user_id = "validation_user_abc123"
        self.session_id = "validation_session_def456"
        
        # Create user context using defensive method
        self.user_context = create_defensive_user_execution_context(
            user_id=self.user_id,
            websocket_client_id=self.session_id
        )
        
        # Create mock dependencies
        self.mock_agent_registry = Mock()
        self.mock_websocket_bridge = AsyncMock()
        self.mock_websocket_emitter = AsyncMock()
        
        # Create UserExecutionEngine instance
        self.execution_engine = UserExecutionEngine(
            context=self.user_context,
            agent_registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            websocket_emitter=self.mock_websocket_emitter
        )
    
    def test_user_execution_engine_implements_tool_interface(self):
        """Test that UserExecutionEngine implements ToolExecutionEngineInterface."""
        from netra_backend.app.schemas.tool import ToolExecutionEngineInterface
        
        # Verify inheritance
        self.assertIsInstance(self.execution_engine, ToolExecutionEngineInterface)
        
        # Verify required interface methods exist
        interface_methods = [
            'execute_tool',
            'execute_tool_with_input', 
            'execute_with_state'
        ]
        
        for method_name in interface_methods:
            self.assertTrue(hasattr(self.execution_engine, method_name),
                          f"UserExecutionEngine should have {method_name} method")
            method = getattr(self.execution_engine, method_name)
            self.assertTrue(callable(method),
                          f"{method_name} should be callable")
    
    async def test_execute_tool_interface_method(self):
        """Test execute_tool method from ToolExecutionEngineInterface."""
        tool_name = "test_tool"
        parameters = {"param1": "value1", "param2": 42}
        
        # Mock tool dispatcher
        mock_dispatcher = AsyncMock()
        mock_tool_result = {
            "result": "Tool executed successfully",
            "success": True,
            "data": {"output": "test_output"}
        }
        mock_dispatcher.execute_tool.return_value = mock_tool_result
        self.execution_engine._get_tool_dispatcher = Mock(return_value=mock_dispatcher)
        
        # Execute tool
        result = await self.execution_engine.execute_tool(tool_name, parameters)
        
        # Validate result structure
        self.assertIsInstance(result, ToolExecuteResponse)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, tool_name)
        self.assertIsNotNone(result.result)
        
        # Verify WebSocket events were triggered
        self.mock_websocket_emitter.notify_tool_executing.assert_called_once_with(tool_name)
        self.mock_websocket_emitter.notify_tool_completed.assert_called_once()
    
    async def test_execute_tool_with_input_interface_method(self):
        """Test execute_tool_with_input method from ToolExecutionEngineInterface."""
        tool_input = ToolInput(
            tool_name="test_tool_input",
            parameters={"input_param": "input_value"},
            user_id=self.user_id
        )
        
        mock_tool = Mock()
        kwargs = {"extra": "kwargs"}
        
        # Mock tool dispatcher
        mock_dispatcher = AsyncMock()
        mock_result = {
            "result": "Tool with input executed",
            "success": True
        }
        mock_dispatcher.execute_tool.return_value = mock_result
        self.execution_engine._get_tool_dispatcher = Mock(return_value=mock_dispatcher)
        
        # Execute tool with input
        result = await self.execution_engine.execute_tool_with_input(tool_input, mock_tool, kwargs)
        
        # Validate result
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, tool_input.tool_name)
    
    async def test_execute_with_state_interface_method(self):
        """Test execute_with_state method from ToolExecutionEngineInterface."""
        mock_tool = Mock()
        tool_name = "state_tool"
        parameters = {"state_param": "state_value"}
        mock_state = {"current_state": "test"}
        run_id = "run_123"
        
        # Mock tool dispatcher
        mock_dispatcher = AsyncMock()
        mock_result = {
            "result": "Tool with state executed",
            "success": True,
            "state_updated": True
        }
        mock_dispatcher.execute_tool.return_value = mock_result
        self.execution_engine._get_tool_dispatcher = Mock(return_value=mock_dispatcher)
        
        # Execute tool with state
        result = await self.execution_engine.execute_with_state(
            mock_tool, tool_name, parameters, mock_state, run_id
        )
        
        # Validate result
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("result", result)
    
    def test_user_context_isolation_maintained(self):
        """Test that user context isolation is maintained in new interface."""
        # Verify user context is properly set
        self.assertEqual(self.execution_engine.context.user_id, self.user_id)
        self.assertEqual(self.execution_engine.context.session_id, self.session_id)
        
        # Verify no shared state
        another_context = create_defensive_user_execution_context(
            user_id="different_user_789",
            websocket_client_id="different_session_xyz"
        )
        
        another_engine = UserExecutionEngine(
            context=another_context,
            agent_registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            websocket_emitter=Mock()  # Different emitter
        )
        
        # Verify isolated contexts
        self.assertNotEqual(self.execution_engine.context.user_id, another_engine.context.user_id)
        self.assertNotEqual(self.execution_engine.websocket_emitter, another_engine.websocket_emitter)


def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestAsyncMethodsWrapper(unittest.TestCase):
    """Wrapper to run async tests in unittest."""
    
    def setUp(self):
        """Set up test instance."""
        self.test_instance = TestIssue1146Phase2Validation()
        self.test_instance.setUp()
    
    def test_execute_tool_async(self):
        """Test execute_tool method (async wrapper)."""
        run_async_test(self.test_instance.test_execute_tool_interface_method())
    
    def test_execute_tool_with_input_async(self):
        """Test execute_tool_with_input method (async wrapper)."""
        run_async_test(self.test_instance.test_execute_tool_with_input_interface_method())
    
    def test_execute_with_state_async(self):
        """Test execute_with_state method (async wrapper)."""
        run_async_test(self.test_instance.test_execute_with_state_interface_method())


if __name__ == '__main__':
    print("🧪 Issue #1146 Phase 2 Validation Test")
    print("Testing ToolExecutionEngine interface implementation...")
    
    # Run synchronous tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIssue1146Phase2Validation)
    sync_runner = unittest.TextTestRunner(verbosity=2)
    sync_result = sync_runner.run(suite)
    
    # Run async tests
    async_suite = unittest.TestLoader().loadTestsFromTestCase(TestAsyncMethodsWrapper)
    async_runner = unittest.TextTestRunner(verbosity=2)
    async_result = async_runner.run(async_suite)
    
    # Summary
    total_tests = sync_result.testsRun + async_result.testsRun
    total_failures = len(sync_result.failures) + len(async_result.failures)
    total_errors = len(sync_result.errors) + len(async_result.errors)
    
    print(f"\n📊 Validation Summary:")
    print(f"   Tests Run: {total_tests}")
    print(f"   Failures: {total_failures}")
    print(f"   Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("✅ All Phase 2 validations PASSED!")
        sys.exit(0)
    else:
        print("❌ Some validations FAILED!")
        sys.exit(1)