"""
Tool Dispatcher Execution Unit Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool execution engine delivers reliable results for AI interactions
- Value Impact: Proper tool execution enables agents to provide actionable business insights
- Strategic Impact: Core execution reliability drives user trust and platform adoption

CRITICAL: These tests validate the execution engine that powers AI tool interactions,
directly impacting the quality and reliability of business insights delivered to users.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.schemas.tool import (
    ToolInput,
    ToolResult,
    ToolStatus,
    ToolExecuteResponse,
    SimpleToolPayload
)
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockWebSocketManager:
    """Mock WebSocket manager for testing tool execution events."""
    
    def __init__(self):
        self.events_sent = []
        self.connection_active = True
        
    async def notify_tool_executing(self, tool_name: str, **kwargs):
        """Mock tool executing notification."""
        if self.connection_active:
            event = {
                "type": "tool_executing",
                "tool_name": tool_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kwargs": kwargs
            }
            self.events_sent.append(event)
        
    async def notify_tool_completed(self, tool_name: str, result: Any, **kwargs):
        """Mock tool completed notification."""
        if self.connection_active:
            event = {
                "type": "tool_completed",
                "tool_name": tool_name,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kwargs": kwargs
            }
            self.events_sent.append(event)
            
    def disconnect(self):
        """Simulate WebSocket disconnection."""
        self.connection_active = False


class MockBusinessTool(BaseTool):
    """Mock business tool that simulates real business logic."""
    
    def __init__(
        self, 
        name: str, 
        should_fail: bool = False, 
        execution_time: float = 0.1,
        business_result: Dict[str, Any] = None
    ):
        self.name = name
        self.description = f"Business tool {name} for real value delivery"
        self.should_fail = should_fail
        self.execution_time = execution_time
        self.business_result = business_result or {
            "success": True,
            "business_value": f"Tool {name} delivered actionable insights",
            "cost_savings": 1000.0,
            "recommendations": ["Optimize infrastructure", "Reduce redundant services"]
        }
        
    def _run(self, *args, **kwargs):
        """Sync version - not used in async system."""
        return self._execute(*args, **kwargs)
        
    async def _arun(self, *args, **kwargs):
        """Async version - primary execution path."""
        await asyncio.sleep(self.execution_time)
        return self._execute(*args, **kwargs)
        
    def _execute(self, *args, **kwargs):
        """Core business logic simulation."""
        if self.should_fail:
            raise Exception(f"Business tool {self.name} failed: Server timeout")
            
        # Simulate business processing
        result = self.business_result.copy()
        result.update({
            "tool_name": self.name,
            "parameters_received": kwargs,
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_duration": self.execution_time
        })
        
        return result


class TestToolExecutionEngineBasicValidation(SSotBaseTestCase):
    """Test basic tool execution engine validation and setup."""
    
    @pytest.mark.unit
    async def test_execution_engine_initialization_with_websocket(self):
        """Test tool execution engine initializes with WebSocket manager."""
        websocket_manager = MockWebSocketManager()
        
        # Create execution engine with WebSocket support
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Verify initialization
        assert engine is not None
        assert hasattr(engine, '_core_engine')
        assert isinstance(engine._core_engine, UnifiedToolExecutionEngine)
        
        # Verify WebSocket integration
        assert hasattr(engine._core_engine, 'websocket_bridge')
        # The core engine should have the WebSocket manager integrated
    
    @pytest.mark.unit
    async def test_execution_engine_initialization_without_websocket(self):
        """Test tool execution engine initializes without WebSocket manager."""
        # Create execution engine without WebSocket support
        engine = ToolExecutionEngine(websocket_manager=None)
        
        # Verify initialization still works
        assert engine is not None
        assert hasattr(engine, '_core_engine')
        assert isinstance(engine._core_engine, UnifiedToolExecutionEngine)
        
        # Engine should still work, just without WebSocket events
        assert engine._core_engine is not None
    
    @pytest.mark.unit
    async def test_tool_input_processing_validation(self):
        """Test tool input processing and validation in execution engine."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create test tool and input
        business_tool = MockBusinessTool("cost_analyzer")
        tool_input = ToolInput(
            tool_name="cost_analyzer",
            kwargs={"aws_account": "123456789", "time_period": "last_30_days"}
        )
        
        # Execute tool with input
        result = await engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=business_tool,
            kwargs=tool_input.kwargs
        )
        
        # Verify result structure
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input == tool_input
        
        # Verify business value in result
        assert "business_value" in str(result.result)
        assert "cost_savings" in str(result.result)
        
        # Verify WebSocket events were sent
        assert len(websocket_manager.events_sent) >= 2
        event_types = [event["type"] for event in websocket_manager.events_sent]
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types


class TestToolExecutionEngineResultProcessing(SSotBaseTestCase):
    """Test result processing and response formatting."""
    
    @pytest.mark.unit
    async def test_successful_execution_result_processing(self):
        """Test processing of successful tool execution results."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create business tool with rich results
        business_result = {
            "success": True,
            "insights": "Your AWS costs can be reduced by 30%",
            "actionable_items": [
                "Terminate idle EC2 instances",
                "Optimize RDS storage",
                "Review S3 storage classes"
            ],
            "potential_savings": {"monthly": 2500.0, "annually": 30000.0},
            "confidence_score": 0.89
        }
        business_tool = MockBusinessTool("cost_optimizer", business_result=business_result)
        
        # Execute with agent state and run ID
        test_state = DeepAgentState(user_request="Help me reduce AWS costs")
        run_id = "business-optimization-run-123"
        
        response = await engine.execute_with_state(
            tool=business_tool,
            tool_name="cost_optimizer",
            parameters={"account_id": "123456789"},
            state=test_state,
            run_id=run_id
        )
        
        # Verify response structure
        assert hasattr(response, 'success')
        assert response.success is True
        assert hasattr(response, 'result')
        assert response.result is not None
        assert hasattr(response, 'error')
        assert response.error is None
        
        # Verify business value is preserved
        result_str = str(response.result)
        assert "potential_savings" in result_str
        assert "actionable_items" in result_str
        assert "confidence_score" in result_str
        
        # Verify metadata contains execution context
        assert hasattr(response, 'metadata')
        metadata_str = str(response.metadata)
        assert run_id in metadata_str or "business-optimization-run" in metadata_str
    
    @pytest.mark.unit
    async def test_execution_error_result_processing(self):
        """Test processing of failed tool execution results."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create failing business tool
        failing_tool = MockBusinessTool("failing_analyzer", should_fail=True)
        test_state = DeepAgentState(user_request="Analyze my costs")
        run_id = "failed-analysis-run-456"
        
        # Execute failing tool
        response = await engine.execute_with_state(
            tool=failing_tool,
            tool_name="failing_analyzer",
            parameters={"account": "invalid"},
            state=test_state,
            run_id=run_id
        )
        
        # Verify error response structure
        assert hasattr(response, 'success')
        assert response.success is False
        assert hasattr(response, 'result')
        assert response.result is None
        assert hasattr(response, 'error')
        assert response.error is not None
        
        # Verify error message is informative
        assert "failed" in response.error.lower()
        assert "timeout" in response.error.lower() or "server" in response.error.lower()
        
        # Verify metadata contains error context
        assert hasattr(response, 'metadata')
        # Error context should be preserved in metadata
    
    @pytest.mark.unit  
    async def test_interface_compliance_execute_tool_method(self):
        """Test ToolExecutionEngineInterface compliance for execute_tool method."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Test the interface method directly
        response = await engine.execute_tool(
            tool_name="interface_test_tool",
            parameters={"param1": "value1", "param2": 42}
        )
        
        # Verify response follows ToolExecuteResponse interface
        assert isinstance(response, ToolExecuteResponse)
        assert hasattr(response, 'success')
        assert hasattr(response, 'result') or hasattr(response, 'error')
        
        # Note: This may return an error since the tool doesn't exist in core engine,
        # but the interface should still be followed
        if not response.success:
            assert hasattr(response, 'error')
            assert response.error is not None


class TestToolExecutionEngineTimeoutAndConcurrency(SSotBaseTestCase):
    """Test timeout handling and concurrent execution scenarios."""
    
    @pytest.mark.unit
    async def test_concurrent_tool_execution_isolation(self):
        """Test concurrent tool executions don't interfere with each other."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create multiple business tools with different execution times
        tools = [
            MockBusinessTool("fast_analyzer", execution_time=0.05, business_result={
                "success": True, "analysis": "Fast analysis complete", "processing_time": "50ms"
            }),
            MockBusinessTool("medium_analyzer", execution_time=0.1, business_result={
                "success": True, "analysis": "Medium analysis complete", "processing_time": "100ms"  
            }),
            MockBusinessTool("slow_analyzer", execution_time=0.15, business_result={
                "success": True, "analysis": "Slow analysis complete", "processing_time": "150ms"
            })
        ]
        
        # Execute tools concurrently
        tasks = []
        for i, tool in enumerate(tools):
            tool_input = ToolInput(tool_name=tool.name, kwargs={"task_id": i})
            task = engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=tool,
                kwargs=tool_input.kwargs
            )
            tasks.append(task)
        
        # Wait for all executions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded and maintained isolation
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            
            # Verify each tool got its own parameters
            result_str = str(result.result)
            assert f"task_id" in result_str or str(i) in result_str
        
        # Verify proper number of WebSocket events (6 total: 3 executing + 3 completed)
        assert len(websocket_manager.events_sent) >= 6
        executing_events = [e for e in websocket_manager.events_sent if e["type"] == "tool_executing"]
        completed_events = [e for e in websocket_manager.events_sent if e["type"] == "tool_completed"]
        assert len(executing_events) == 3
        assert len(completed_events) == 3
    
    @pytest.mark.unit
    async def test_websocket_disconnection_during_execution(self):
        """Test tool execution continues even if WebSocket disconnects."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create business tool
        business_tool = MockBusinessTool("resilient_tool", execution_time=0.1)
        tool_input = ToolInput(tool_name="resilient_tool", kwargs={"param": "value"})
        
        # Start tool execution
        execution_task = asyncio.create_task(
            engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=business_tool,
                kwargs=tool_input.kwargs
            )
        )
        
        # Simulate WebSocket disconnection during execution
        await asyncio.sleep(0.05)  # Let execution start
        websocket_manager.disconnect()
        
        # Wait for execution to complete
        result = await execution_task
        
        # Verify execution completed successfully despite WebSocket disconnection
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        
        # Verify some events were sent before disconnection
        assert len(websocket_manager.events_sent) >= 1  # At least tool_executing
        
        # Verify business value was still delivered
        assert "business_value" in str(result.result)
    
    @pytest.mark.unit
    async def test_execution_with_complex_business_parameters(self):
        """Test execution with complex business parameters and nested data."""
        websocket_manager = MockWebSocketManager()
        engine = ToolExecutionEngine(websocket_manager=websocket_manager)
        
        # Create tool that handles complex business data
        complex_result = {
            "success": True,
            "cost_analysis": {
                "current_spend": {"monthly": 45000.0, "trend": "increasing"},
                "optimization_opportunities": [
                    {"service": "EC2", "potential_savings": 12000.0, "confidence": 0.95},
                    {"service": "RDS", "potential_savings": 3500.0, "confidence": 0.87},
                    {"service": "S3", "potential_savings": 800.0, "confidence": 0.72}
                ],
                "recommendations": {
                    "immediate": ["Terminate idle instances", "Resize over-provisioned RDS"],
                    "short_term": ["Implement auto-scaling", "Optimize storage classes"],
                    "long_term": ["Migrate to serverless", "Implement FinOps practices"]
                }
            },
            "risk_assessment": {"overall_risk": "LOW", "impact_score": 8.5}
        }
        
        business_tool = MockBusinessTool("enterprise_analyzer", business_result=complex_result)
        
        # Create complex parameters that enterprise customers would use
        complex_params = {
            "aws_accounts": ["123456789", "987654321"],
            "services_to_analyze": ["EC2", "RDS", "S3", "Lambda"],
            "time_range": {"start": "2024-01-01", "end": "2024-02-01"},
            "analysis_depth": "comprehensive",
            "include_forecasting": True,
            "compliance_requirements": ["SOC2", "GDPR"],
            "cost_allocation_tags": {"Environment": ["prod", "staging"], "Team": ["backend", "frontend"]}
        }
        
        tool_input = ToolInput(tool_name="enterprise_analyzer", kwargs=complex_params)
        
        # Execute with complex parameters
        result = await engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=business_tool,
            kwargs=complex_params
        )
        
        # Verify successful processing of complex data
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        
        # Verify complex business data is preserved
        result_str = str(result.result)
        assert "cost_analysis" in result_str
        assert "optimization_opportunities" in result_str
        assert "recommendations" in result_str
        assert "risk_assessment" in result_str
        
        # Verify parameters were processed correctly
        assert "aws_accounts" in result_str or "123456789" in result_str
        assert "compliance_requirements" in result_str or "SOC2" in result_str
        
        # Verify WebSocket events contain relevant business information
        assert len(websocket_manager.events_sent) >= 2
        completed_event = next(e for e in websocket_manager.events_sent if e["type"] == "tool_completed")
        assert "enterprise_analyzer" in str(completed_event)