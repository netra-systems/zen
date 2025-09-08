"""
Unit Tests for Tool Dispatcher Execution Engine - Batch 2 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure execution engine reliably runs tools with proper error handling
- Value Impact: Prevents tool execution failures that break agent task completion
- Strategic Impact: Execution layer that powers all AI agent tool interactions

Focus Areas:
1. Delegation to unified execution engine
2. Response transformation and error handling
3. WebSocket manager integration
4. Interface compliance and method signatures
5. State management during execution
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.schemas.tool import (
    ToolInput, 
    ToolResult, 
    ToolStatus,
    ToolExecuteResponse,
    ToolExecutionEngineInterface
)
from netra_backend.app.agents.state import DeepAgentState


class TestToolExecutionEngineUnit(SSotBaseTestCase):
    """Unit tests for the tool execution engine wrapper."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_websocket_manager = Mock()
        self.mock_state = Mock(spec=DeepAgentState)
        self.mock_state.user_request = "test request"
    
    # ===================== INITIALIZATION TESTS =====================
    
    def test_initialization_creates_unified_engine(self):
        """Test ToolExecutionEngine initializes with unified engine.
        
        BVJ: Ensures proper delegation to consolidated implementation.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Verify unified engine was created with correct parameters
            mock_unified.assert_called_once_with(self.mock_websocket_manager)
            assert engine._core_engine == mock_core_engine
        
        self.record_metric("initialization_creates_unified_engine", True)
    
    def test_initialization_without_websocket_manager(self):
        """Test ToolExecutionEngine initializes without WebSocket manager.
        
        BVJ: Ensures flexibility in execution contexts.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            # Verify unified engine was created with None
            mock_unified.assert_called_once_with(None)
            assert engine._core_engine == mock_core_engine
        
        self.record_metric("initialization_without_websocket", True)
    
    # ===================== INTERFACE COMPLIANCE TESTS =====================
    
    def test_implements_tool_execution_engine_interface(self):
        """Test ToolExecutionEngine implements required interface.
        
        BVJ: Ensures consistent API across execution engines.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine'):
            engine = ToolExecutionEngine()
            
            # Should be instance of the interface
            assert isinstance(engine, ToolExecutionEngineInterface)
            
            # Should have required interface methods
            assert hasattr(engine, 'execute_tool_with_input')
            assert hasattr(engine, 'execute_with_state')
            assert hasattr(engine, 'execute_tool')
            
            # Methods should be callable
            assert callable(engine.execute_tool_with_input)
            assert callable(engine.execute_with_state)
            assert callable(engine.execute_tool)
        
        self.record_metric("interface_compliance_verified", True)
    
    # ===================== DELEGATION TESTS =====================
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_input_delegates_to_core(self):
        """Test execute_tool_with_input delegates to unified engine.
        
        BVJ: Ensures consistent tool execution behavior.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_result = Mock(spec=ToolResult)
            mock_core_engine.execute_tool_with_input = AsyncMock(return_value=mock_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            tool_input = ToolInput(tool_name="test_tool", kwargs={"param": "value"})
            mock_tool = Mock()
            kwargs = {"param": "value"}
            
            result = await engine.execute_tool_with_input(tool_input, mock_tool, kwargs)
            
            # Verify delegation to core engine
            mock_core_engine.execute_tool_with_input.assert_called_once_with(
                tool_input, mock_tool, kwargs
            )
            assert result == mock_result
        
        self.record_metric("execute_tool_with_input_delegation_tested", True)
    
    @pytest.mark.asyncio
    async def test_execute_with_state_delegates_and_transforms_response(self):
        """Test execute_with_state delegates and transforms response properly.
        
        BVJ: Ensures stateful execution works with proper response format.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_core_result = {
                "success": True,
                "result": {"output": "success"},
                "metadata": {"execution_time": 100}
            }
            mock_core_engine.execute_with_state = AsyncMock(return_value=mock_core_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            mock_tool = Mock()
            parameters = {"param": "value"}
            run_id = "test_run_123"
            
            result = await engine.execute_with_state(
                mock_tool, "test_tool", parameters, self.mock_state, run_id
            )
            
            # Verify delegation to core engine
            mock_core_engine.execute_with_state.assert_called_once_with(
                mock_tool, "test_tool", parameters, self.mock_state, run_id
            )
            
            # Verify response transformation to ToolDispatchResponse
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            assert isinstance(result, ToolDispatchResponse)
            assert result.success is True
            assert result.result == {"output": "success"}
            assert result.metadata == {"execution_time": 100}
            assert result.error is None
        
        self.record_metric("execute_with_state_delegation_tested", True)
    
    @pytest.mark.asyncio
    async def test_execute_with_state_handles_error_response(self):
        """Test execute_with_state properly transforms error responses.
        
        BVJ: Ensures consistent error handling across execution paths.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_core_result = {
                "success": False,
                "error": "Tool execution failed",
                "metadata": {"error_code": 500}
            }
            mock_core_engine.execute_with_state = AsyncMock(return_value=mock_core_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            result = await engine.execute_with_state(
                Mock(), "failing_tool", {}, self.mock_state, "test_run"
            )
            
            # Verify error response transformation
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            assert isinstance(result, ToolDispatchResponse)
            assert result.success is False
            assert result.error == "Tool execution failed"
            assert result.result is None
            assert result.metadata == {"error_code": 500}
        
        self.record_metric("error_response_transformation_tested", True)
    
    @pytest.mark.asyncio
    async def test_execute_tool_delegates_to_core(self):
        """Test execute_tool interface method delegates to core.
        
        BVJ: Ensures interface compliance for direct tool execution.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_response = Mock(spec=ToolExecuteResponse)
            mock_core_engine.execute_tool = AsyncMock(return_value=mock_response)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            result = await engine.execute_tool("test_tool", {"param": "value"})
            
            # Verify delegation to core engine
            mock_core_engine.execute_tool.assert_called_once_with(
                "test_tool", {"param": "value"}
            )
            assert result == mock_response
        
        self.record_metric("execute_tool_interface_delegation_tested", True)
    
    # ===================== ERROR HANDLING TESTS =====================
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_input_propagates_exceptions(self):
        """Test execute_tool_with_input propagates exceptions from core engine.
        
        BVJ: Ensures errors are properly surfaced for debugging.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_core_engine.execute_tool_with_input = AsyncMock(
                side_effect=ValueError("Core engine error")
            )
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            tool_input = ToolInput(tool_name="failing_tool")
            
            with pytest.raises(ValueError, match="Core engine error"):
                await engine.execute_tool_with_input(tool_input, Mock(), {})
        
        self.record_metric("exception_propagation_tested", True)
    
    @pytest.mark.asyncio
    async def test_execute_with_state_handles_malformed_core_response(self):
        """Test execute_with_state handles malformed responses from core.
        
        BVJ: Ensures robustness against internal API changes.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            # Return response missing expected fields
            mock_core_engine.execute_with_state = AsyncMock(return_value={})
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            result = await engine.execute_with_state(
                Mock(), "test_tool", {}, self.mock_state, "test_run"
            )
            
            # Should handle gracefully with defaults
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            assert isinstance(result, ToolDispatchResponse)
            # Should default to failure if success field missing
            assert result.success is False
        
        self.record_metric("malformed_response_handling_tested", True)


class TestToolExecutionEngineWebSocketIntegrationUnit(SSotBaseTestCase):
    """Unit tests for WebSocket integration in execution engine."""
    
    def setup_method(self, method):
        """Set up test environment.""" 
        super().setup_method(method)
        self.mock_websocket_manager = Mock()
    
    def test_websocket_manager_passed_to_unified_engine(self):
        """Test WebSocket manager is properly passed to unified engine.
        
        BVJ: Ensures tool execution events are properly emitted.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Verify unified engine was initialized with WebSocket manager
            mock_unified.assert_called_once_with(self.mock_websocket_manager)
        
        self.record_metric("websocket_manager_integration_tested", True)
    
    @pytest.mark.asyncio
    async def test_execution_inherits_websocket_behavior_from_core(self):
        """Test execution inherits WebSocket behavior from unified engine.
        
        BVJ: Ensures WebSocket events are emitted during tool execution.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_result = Mock(spec=ToolResult)
            mock_core_engine.execute_tool_with_input = AsyncMock(return_value=mock_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine(websocket_manager=self.mock_websocket_manager)
            
            # Execute a tool - WebSocket behavior should be handled by core engine
            tool_input = ToolInput(tool_name="test_tool")
            await engine.execute_tool_with_input(tool_input, Mock(), {})
            
            # Verify core engine was called (it handles WebSocket events internally)
            mock_core_engine.execute_tool_with_input.assert_called_once()
        
        self.record_metric("websocket_behavior_inheritance_tested", True)


class TestToolExecutionEngineCompatibilityUnit(SSotBaseTestCase):
    """Unit tests for compatibility with existing tool execution patterns."""
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.mock_production_tool = Mock()
        self.mock_production_tool.name = "production_tool"
    
    @pytest.mark.asyncio
    async def test_production_tool_compatibility(self):
        """Test execution engine works with ProductionTool instances.
        
        BVJ: Ensures compatibility with existing production tool implementations.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_result = Mock(spec=ToolResult)
            mock_core_engine.execute_tool_with_input = AsyncMock(return_value=mock_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            # Should work with ProductionTool
            tool_input = ToolInput(tool_name="production_tool")
            result = await engine.execute_tool_with_input(
                tool_input, self.mock_production_tool, {}
            )
            
            # Verify execution completed
            assert result == mock_result
            mock_core_engine.execute_tool_with_input.assert_called_once_with(
                tool_input, self.mock_production_tool, {}
            )
        
        self.record_metric("production_tool_compatibility_tested", True)
    
    @pytest.mark.asyncio
    async def test_state_based_execution_compatibility(self):
        """Test execution engine maintains compatibility with state-based execution.
        
        BVJ: Ensures existing agent workflows continue to work.
        """
        mock_state = Mock(spec=DeepAgentState)
        mock_state.user_request = "test request"
        
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_core_result = {"success": True, "result": "state execution"}
            mock_core_engine.execute_with_state = AsyncMock(return_value=mock_core_result)
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            result = await engine.execute_with_state(
                Mock(), "stateful_tool", {"param": "value"}, mock_state, "run_123"
            )
            
            # Verify compatibility with state-based pattern
            from netra_backend.app.agents.tool_dispatcher_core import ToolDispatchResponse
            assert isinstance(result, ToolDispatchResponse)
            assert result.success is True
            assert result.result == "state execution"
        
        self.record_metric("state_execution_compatibility_tested", True)


class TestToolExecutionEngineArchitectureUnit(SSotBaseTestCase):
    """Unit tests for architectural patterns in execution engine."""
    
    def test_follows_delegation_pattern(self):
        """Test execution engine follows proper delegation pattern.
        
        BVJ: Ensures clean architecture with single responsibility.
        """
        with patch('netra_backend.app.agents.tool_dispatcher_execution.UnifiedToolExecutionEngine') as mock_unified:
            mock_core_engine = Mock()
            mock_unified.return_value = mock_core_engine
            
            engine = ToolExecutionEngine()
            
            # Engine should store reference to core engine
            assert hasattr(engine, '_core_engine')
            assert engine._core_engine == mock_core_engine
            
            # Engine should not duplicate functionality
            assert not hasattr(engine, 'execute_tool_logic')  # No direct execution logic
            assert not hasattr(engine, 'websocket_events')    # No direct event handling
        
        self.record_metric("delegation_pattern_verified", True)
    
    def test_minimal_wrapper_implementation(self):
        """Test execution engine is minimal wrapper around unified engine.
        
        BVJ: Ensures maintainability and prevents code duplication.
        """
        import inspect
        
        # Get the source code of the class
        source_lines = inspect.getsourcelines(ToolExecutionEngine)[0]
        source_text = ''.join(source_lines)
        
        # Should be primarily delegation with minimal logic
        delegation_patterns = [
            "self._core_engine",
            "return await self._core_engine",
            "UnifiedToolExecutionEngine"
        ]
        
        for pattern in delegation_patterns:
            assert pattern in source_text, f"Delegation pattern '{pattern}' not found"
        
        # Should not have complex logic
        complex_patterns = [
            "if.*else.*if",  # Complex conditionals
            "for.*in.*:",    # Loops (simple delegation shouldn't need loops)
            "try:.*except:.*except:"  # Complex error handling
        ]
        
        import re
        for pattern in complex_patterns:
            matches = re.search(pattern, source_text, re.MULTILINE | re.DOTALL)
            assert matches is None, f"Complex pattern found: {pattern}"
        
        self.record_metric("minimal_wrapper_verified", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])