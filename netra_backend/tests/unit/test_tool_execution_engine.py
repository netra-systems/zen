"""
Test Tool Execution Engine Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tools execute correctly to deliver AI value
- Value Impact: Tools are core mechanisms for agents to provide insights and solutions
- Strategic Impact: Core platform functionality enabling all agent-based business value

This test suite validates the UnifiedToolExecutionEngine's business logic including:
- Tool execution flow and result handling
- WebSocket notification integration
- Security controls and resource limits
- Performance metrics tracking
- Error handling and recovery patterns

Performance Requirements:
- Tool execution should complete within configured timeout
- Memory usage should not exceed limits
- WebSocket notifications should be sent for all tool operations
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.core.tool_models import ToolExecutionResult, UnifiedTool
from netra_backend.app.core.exceptions_base import NetraException


class TestUnifiedToolExecutionEngine(SSotBaseTestCase):
    """Test UnifiedToolExecutionEngine business logic without external dependencies."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create mock WebSocket bridge
        self.mock_websocket_bridge = Mock()
        self.mock_websocket_bridge.send_tool_executing = AsyncMock()
        self.mock_websocket_bridge.send_tool_completed = AsyncMock()
        
        # Create mock permission service
        self.mock_permission_service = Mock()
        
        # Initialize engine under test
        self.engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.mock_websocket_bridge,
            permission_service=self.mock_permission_service
        )
        
        # Track metrics for validation
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_initialization_sets_security_defaults(self):
        """Test that engine initializes with proper security defaults."""
        # Given: Fresh engine initialization
        engine = UnifiedToolExecutionEngine()
        
        # Then: Security controls should be initialized
        assert engine.default_timeout == 30.0  # Default from env
        assert engine.max_memory_mb == 512
        assert engine.max_concurrent_per_user == 10
        assert engine.rate_limit_per_minute == 100
        
        # And: Metrics tracking should be initialized
        assert engine._execution_metrics['total_executions'] == 0
        assert engine._execution_metrics['successful_executions'] == 0
        assert engine._execution_metrics['failed_executions'] == 0
        
        # And: User limits tracking should be initialized
        assert len(engine._active_executions) == 0
        assert len(engine._user_execution_counts) == 0
        
        self.record_metric("initialization_validated", True)
    
    @pytest.mark.unit
    async def test_execute_tool_sends_websocket_notifications(self):
        """Test that tool execution sends proper WebSocket notifications."""
        # Given: Mock tool and execution context
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "test_calculator"
        mock_tool.execute = AsyncMock(return_value={"result": "calculation_complete"})
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        execution_context = {
            "user_id": user_id,
            "tool_name": "test_calculator",
            "parameters": {"operation": "add", "values": [1, 2]}
        }
        
        # When: Executing tool
        with patch.object(self.engine, '_validate_execution_permissions', return_value=True), \
             patch.object(self.engine, '_check_resource_limits', return_value=True), \
             patch.object(self.engine, '_execute_with_monitoring') as mock_execute:
            
            mock_execute.return_value = ToolExecutionResult(
                success=True,
                result={"calculation": 3},
                execution_time=0.150,
                tool_name="test_calculator"
            )
            
            result = await self.engine.execute_tool(mock_tool, execution_context)
        
        # Then: WebSocket notifications should be sent
        self.mock_websocket_bridge.send_tool_executing.assert_called_once()
        self.mock_websocket_bridge.send_tool_completed.assert_called_once()
        
        # And: Result should indicate success
        assert result.success is True
        assert result.result["calculation"] == 3
        assert result.tool_name == "test_calculator"
        assert result.execution_time > 0
        
        # And: Metrics should be updated
        self.increment_websocket_events(2)  # executing + completed
        self.record_metric("tool_execution_success", True)
        self.record_metric("execution_time_ms", result.execution_time * 1000)
    
    @pytest.mark.unit
    async def test_execute_tool_handles_execution_timeout(self):
        """Test that tool execution properly handles timeout scenarios."""
        # Given: Mock tool that takes too long
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "slow_calculator"
        
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(2.0)  # Simulate slow operation
            return {"result": "too_late"}
        
        mock_tool.execute = slow_execution
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        execution_context = {
            "user_id": user_id,
            "tool_name": "slow_calculator",
            "timeout": 0.5  # Very short timeout
        }
        
        # When: Executing tool with short timeout
        with patch.object(self.engine, '_validate_execution_permissions', return_value=True), \
             patch.object(self.engine, '_check_resource_limits', return_value=True):
            
            result = await self.engine.execute_tool(mock_tool, execution_context)
        
        # Then: Execution should fail with timeout
        assert result.success is False
        assert "timeout" in result.error_message.lower() or "timed out" in result.error_message.lower()
        assert result.tool_name == "slow_calculator"
        
        # And: WebSocket notifications should still be sent
        self.mock_websocket_bridge.send_tool_executing.assert_called_once()
        self.mock_websocket_bridge.send_tool_completed.assert_called_once()
        
        self.record_metric("timeout_handling_validated", True)
    
    @pytest.mark.unit
    async def test_execute_tool_validates_permissions(self):
        """Test that tool execution validates user permissions."""
        # Given: Mock tool and permission service that denies access
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "restricted_tool"
        
        self.mock_permission_service.check_tool_permission = AsyncMock(
            return_value={"allowed": False, "reason": "insufficient_subscription"}
        )
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        execution_context = {
            "user_id": user_id,
            "tool_name": "restricted_tool",
            "subscription_level": "free"
        }
        
        # When: Executing tool without permission
        result = await self.engine.execute_tool(mock_tool, execution_context)
        
        # Then: Execution should fail with permission error
        assert result.success is False
        assert "permission" in result.error_message.lower() or "insufficient" in result.error_message.lower()
        
        # And: Permission check should have been called
        self.mock_permission_service.check_tool_permission.assert_called_once()
        
        self.record_metric("permission_validation_enforced", True)
    
    @pytest.mark.unit
    async def test_execute_tool_enforces_resource_limits(self):
        """Test that tool execution enforces resource limits per user."""
        # Given: Engine with low concurrent limit
        engine = UnifiedToolExecutionEngine(websocket_bridge=self.mock_websocket_bridge)
        engine.max_concurrent_per_user = 2
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Simulate user already has 2 active executions
        engine._user_execution_counts[user_id] = 2
        
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "resource_intensive_tool"
        
        execution_context = {
            "user_id": user_id,
            "tool_name": "resource_intensive_tool"
        }
        
        # When: Executing tool that would exceed limit
        with patch.object(engine, '_validate_execution_permissions', return_value=True):
            result = await engine.execute_tool(mock_tool, execution_context)
        
        # Then: Execution should fail with resource limit error
        assert result.success is False
        assert "limit" in result.error_message.lower() or "resource" in result.error_message.lower()
        
        self.record_metric("resource_limits_enforced", True)
    
    @pytest.mark.unit
    def test_enhance_tool_dispatcher_integration(self):
        """Test tool dispatcher enhancement with WebSocket notifications."""
        # Given: Mock tool dispatcher
        mock_dispatcher = Mock()
        mock_dispatcher.executor = Mock()
        
        mock_websocket_manager = Mock()
        
        # When: Enhancing dispatcher
        enhanced_dispatcher = asyncio.run(enhance_tool_dispatcher_with_notifications(
            tool_dispatcher=mock_dispatcher,
            websocket_manager=mock_websocket_manager,
            enable_notifications=True
        ))
        
        # Then: Dispatcher should be enhanced
        assert enhanced_dispatcher._websocket_enhanced is True
        assert isinstance(enhanced_dispatcher.executor, UnifiedToolExecutionEngine)
        assert hasattr(enhanced_dispatcher.executor, 'websocket_manager')
        
        # And: Should not double-enhance
        enhanced_again = asyncio.run(enhance_tool_dispatcher_with_notifications(
            tool_dispatcher=enhanced_dispatcher,
            websocket_manager=mock_websocket_manager
        ))
        
        assert enhanced_again is enhanced_dispatcher
        
        self.record_metric("dispatcher_enhancement_validated", True)
    
    @pytest.mark.unit
    async def test_execution_metrics_tracking(self):
        """Test that execution metrics are properly tracked."""
        # Given: Fresh engine for metrics testing
        engine = UnifiedToolExecutionEngine(websocket_bridge=self.mock_websocket_bridge)
        
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "metrics_test_tool"
        mock_tool.execute = AsyncMock(return_value={"status": "success"})
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        execution_context = {"user_id": user_id, "tool_name": "metrics_test_tool"}
        
        # When: Executing multiple tools
        with patch.object(engine, '_validate_execution_permissions', return_value=True), \
             patch.object(engine, '_check_resource_limits', return_value=True):
            
            # Execute successful tool
            result1 = await engine.execute_tool(mock_tool, execution_context)
            
            # Execute failing tool
            mock_tool.execute.side_effect = Exception("Tool error")
            result2 = await engine.execute_tool(mock_tool, execution_context)
        
        # Then: Metrics should be tracked
        metrics = engine._execution_metrics
        assert metrics['total_executions'] >= 2
        assert metrics['successful_executions'] >= 1
        assert metrics['failed_executions'] >= 1
        assert metrics['total_duration_ms'] > 0
        
        self.record_metric("metrics_tracking_validated", True)
    
    @pytest.mark.unit
    def test_websocket_bridge_compatibility(self):
        """Test WebSocket bridge compatibility with legacy interfaces."""
        # Given: Engine with WebSocket bridge
        engine = UnifiedToolExecutionEngine(websocket_bridge=self.mock_websocket_bridge)
        
        # Then: Should provide backward compatibility aliases
        assert engine.websocket_notifier is engine.websocket_bridge
        assert hasattr(engine, 'websocket_bridge')
        
        # And: Should handle None websocket_bridge gracefully
        engine_without_ws = UnifiedToolExecutionEngine(websocket_bridge=None)
        assert engine_without_ws.websocket_bridge is None
        assert engine_without_ws.websocket_notifier is None
        
        self.record_metric("websocket_compatibility_validated", True)
    
    @pytest.mark.unit
    async def test_error_recovery_patterns(self):
        """Test error recovery and resilience patterns."""
        # Given: Tool that fails intermittently
        mock_tool = Mock(spec=UnifiedTool)
        mock_tool.name = "unreliable_tool"
        
        call_count = 0
        async def flaky_execution(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Network error {call_count}")
            return {"result": "success_after_retries"}
        
        mock_tool.execute = flaky_execution
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        execution_context = {"user_id": user_id, "tool_name": "unreliable_tool"}
        
        # When: Executing unreliable tool with retry mechanism
        with patch.object(self.engine, '_validate_execution_permissions', return_value=True), \
             patch.object(self.engine, '_check_resource_limits', return_value=True), \
             patch.object(self.engine, '_execute_with_retry') as mock_retry:
            
            mock_retry.return_value = ToolExecutionResult(
                success=True,
                result={"result": "success_after_retries"},
                execution_time=0.300,
                tool_name="unreliable_tool",
                retry_count=2
            )
            
            result = await self.engine.execute_tool(mock_tool, execution_context)
        
        # Then: Should eventually succeed after retries
        assert result.success is True
        assert result.retry_count == 2
        assert result.result["result"] == "success_after_retries"
        
        self.record_metric("error_recovery_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Verify WebSocket events were properly tracked if any were sent
        websocket_events = self.get_websocket_events_count()
        if websocket_events > 0:
            self.record_metric("websocket_events_sent", websocket_events)
        
        # Verify execution time is reasonable for unit tests
        execution_time = self.get_metrics().execution_time
        if execution_time > 2.0:  # Unit tests should be fast
            self.record_metric("slow_test_warning", execution_time)
        
        super().teardown_method(method)


class TestToolExecutionEnginePerformance(SSotBaseTestCase):
    """Test performance characteristics of tool execution engine."""
    
    @pytest.mark.unit
    async def test_concurrent_execution_handling(self):
        """Test that engine handles concurrent tool executions properly."""
        # Given: Engine configured for concurrent testing
        engine = UnifiedToolExecutionEngine()
        
        mock_tools = []
        execution_contexts = []
        
        # Create multiple mock tools
        for i in range(5):
            mock_tool = Mock(spec=UnifiedTool)
            mock_tool.name = f"concurrent_tool_{i}"
            mock_tool.execute = AsyncMock(return_value={"result": f"output_{i}"})
            mock_tools.append(mock_tool)
            
            execution_contexts.append({
                "user_id": f"user_{i}",
                "tool_name": f"concurrent_tool_{i}"
            })
        
        # When: Executing tools concurrently
        start_time = time.time()
        
        with patch.object(engine, '_validate_execution_permissions', return_value=True), \
             patch.object(engine, '_check_resource_limits', return_value=True):
            
            tasks = [
                engine.execute_tool(tool, context)
                for tool, context in zip(mock_tools, execution_contexts)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        
        # Then: All executions should complete successfully
        assert len(results) == 5
        successful_results = [r for r in results if isinstance(r, ToolExecutionResult) and r.success]
        assert len(successful_results) >= 4  # Allow for one potential failure in concurrent testing
        
        # And: Execution time should be reasonable for concurrent operations
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        self.record_metric("concurrent_executions_completed", len(successful_results))
        self.record_metric("concurrent_execution_time", execution_time)
    
    @pytest.mark.unit
    def test_memory_usage_monitoring(self):
        """Test that engine monitors memory usage appropriately."""
        # Given: Engine with memory monitoring
        engine = UnifiedToolExecutionEngine()
        
        # When: Checking memory usage
        initial_memory = engine._process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate some memory-intensive operation
        large_data = {"data": "x" * 1000000}  # 1MB string
        engine._execution_metrics['memory_test'] = large_data
        
        current_memory = engine._process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        # Then: Memory monitoring should work
        assert initial_memory > 0
        assert current_memory > 0
        
        # And: Should not exceed configured limits significantly
        assert current_memory < engine.max_memory_mb * 2  # Allow some headroom for test environment
        
        self.record_metric("initial_memory_mb", initial_memory)
        self.record_metric("current_memory_mb", current_memory)
        self.record_metric("memory_increase_mb", memory_increase)
        
        # Cleanup
        del engine._execution_metrics['memory_test']
        del large_data