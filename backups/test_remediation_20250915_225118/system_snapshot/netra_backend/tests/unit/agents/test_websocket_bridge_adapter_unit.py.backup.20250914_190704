"""
WebSocketBridgeAdapter Unit Tests - Issue #1081 Phase 1

Comprehensive unit tests for WebSocketBridgeAdapter functionality.
Targets adapter pattern, event delegation, and agent-websocket coordination.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Risk Reduction
- Value Impact: Protects $500K+ ARR WebSocket event adapter functionality
- Strategic Impact: Comprehensive coverage for agent WebSocket event emission

Coverage Focus:
- WebSocket bridge adapter initialization and configuration
- Event emission delegation to AgentWebSocketBridge
- Test mode handling for development and testing
- Error handling for missing bridge scenarios
- Event validation and format consistency
- Agent lifecycle event emission patterns

Test Strategy: Unit tests with adapter pattern validation, minimal external dependencies
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.websocket_core.event_validator import get_websocket_validator


class MockAgentWebSocketBridge:
    """Mock AgentWebSocketBridge for adapter testing."""
    
    def __init__(self):
        self.events_received = []
        self.is_healthy = True
        self.connection_active = True
    
    async def emit_agent_event(self, event_type: str, data: Dict[str, Any], 
                              run_id: str, user_context=None, agent_name: str = None):
        """Mock event emission."""
        event = {
            "event_type": event_type,
            "data": data,
            "run_id": run_id,
            "agent_name": agent_name,
            "user_context": user_context,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.events_received.append(event)
        return True
    
    def health_check(self) -> bool:
        """Mock health check."""
        return self.is_healthy
    
    def is_connected(self) -> bool:
        """Mock connection check."""
        return self.connection_active
    
    def get_events_for_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get events for specific agent."""
        return [e for e in self.events_received if e.get("agent_name") == agent_name]


class TestWebSocketBridgeAdapter(SSotAsyncTestCase):
    """Comprehensive unit tests for WebSocketBridgeAdapter functionality."""
    
    def setup_method(self, method):
        """Set up test fixtures for each test method."""
        super().setup_method(method)
        
        # Create test adapter
        self.adapter = WebSocketBridgeAdapter()
        
        # Create mock bridge
        self.mock_bridge = MockAgentWebSocketBridge()
        
        # Test identifiers
        self.test_run_id = "adapter_test_run_123"
        self.test_agent_name = "TestAdapterAgent"
        
        # Track adapter operations
        self.adapter_operations = []
        self.event_emissions = []
    
    def teardown_method(self, method):
        """Clean up after each test."""
        super().teardown_method(method)
        self.adapter_operations.clear()
        self.event_emissions.clear()
    
    # === Adapter Initialization Tests ===
    
    def test_adapter_initialization(self):
        """Test WebSocketBridgeAdapter initializes correctly."""
        # Verify basic initialization
        assert self.adapter._bridge is None
        assert self.adapter._run_id is None
        assert self.adapter._agent_name is None
        assert self.adapter._test_mode is False
        
        # Verify adapter starts without bridge configured
        assert not self.adapter.has_websocket_bridge()
    
    def test_adapter_bridge_configuration(self):
        """Test adapter bridge configuration process."""
        # Configure bridge
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Verify configuration
        assert self.adapter._bridge == self.mock_bridge
        assert self.adapter._run_id == self.test_run_id
        assert self.adapter._agent_name == self.test_agent_name
        assert self.adapter.has_websocket_bridge() is True
    
    def test_adapter_configuration_validation(self):
        """Test adapter validates bridge configuration parameters."""
        # Test with None bridge (should log error but not crash)
        self.adapter.set_websocket_bridge(
            bridge=None,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Should handle None bridge gracefully
        assert self.adapter._bridge is None
        assert not self.adapter.has_websocket_bridge()
        
        # Test with None run_id (should log error)
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=None,
            agent_name=self.test_agent_name
        )
        
        # Should handle None run_id gracefully
        assert self.adapter._run_id is None
        assert not self.adapter.has_websocket_bridge()
    
    def test_adapter_test_mode_configuration(self):
        """Test adapter test mode configuration."""
        # Initially not in test mode
        assert self.adapter._test_mode is False
        
        # Enable test mode
        self.adapter.enable_test_mode()
        
        # Verify test mode enabled
        assert self.adapter._test_mode is True
    
    # === Event Emission Core Tests ===
    
    async def test_agent_started_event_emission(self):
        """Test agent_started event emission through adapter."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit agent started event
        await self.adapter.emit_agent_started("Agent starting message processing")
        
        # Verify event was sent to bridge
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        assert len(events) >= 1
        
        # Verify event content
        started_events = [e for e in events if e["event_type"] == "agent_started"]
        assert len(started_events) >= 1
        
        event = started_events[0]
        assert event["run_id"] == self.test_run_id
        assert event["agent_name"] == self.test_agent_name
    
    async def test_agent_thinking_event_emission(self):
        """Test agent_thinking event emission through adapter."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit thinking event
        thinking_message = "Analyzing user query for optimal response"
        await self.adapter.emit_agent_thinking(thinking_message)
        
        # Verify event was sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        thinking_events = [e for e in events if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 1
        
        event = thinking_events[0]
        assert event["data"]["message"] == thinking_message
    
    async def test_tool_execution_events(self):
        """Test tool execution event emission sequence."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit tool executing event
        tool_name = "calculator"
        tool_input = {"expression": "2 + 2"}
        await self.adapter.emit_tool_executing(tool_name, tool_input)
        
        # Emit tool completed event
        tool_output = {"result": 4}
        await self.adapter.emit_tool_completed(tool_name, tool_output)
        
        # Verify both events were sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        
        executing_events = [e for e in events if e["event_type"] == "tool_executing"]
        completed_events = [e for e in events if e["event_type"] == "tool_completed"]
        
        assert len(executing_events) >= 1
        assert len(completed_events) >= 1
        
        # Verify event data
        exec_event = executing_events[0]
        comp_event = completed_events[0]
        
        assert exec_event["data"]["tool_name"] == tool_name
        assert exec_event["data"]["input"] == tool_input
        assert comp_event["data"]["tool_name"] == tool_name
        assert comp_event["data"]["output"] == tool_output
    
    async def test_agent_completed_event_emission(self):
        """Test agent_completed event emission."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit completed event
        completion_result = {"status": "success", "message": "Task completed successfully"}
        await self.adapter.emit_agent_completed(completion_result)
        
        # Verify event was sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        completed_events = [e for e in events if e["event_type"] == "agent_completed"]
        assert len(completed_events) >= 1
        
        event = completed_events[0]
        assert event["data"] == completion_result
    
    async def test_progress_event_emission(self):
        """Test progress event emission for incremental updates."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit progress event
        progress_data = {
            "step": "data_processing",
            "progress": 50,
            "total": 100,
            "message": "Processing data files"
        }
        await self.adapter.emit_progress(progress_data)
        
        # Verify event was sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        progress_events = [e for e in events if e["event_type"] == "agent_progress"]
        assert len(progress_events) >= 1
        
        event = progress_events[0]
        assert event["data"]["step"] == "data_processing"
        assert event["data"]["progress"] == 50
    
    async def test_error_event_emission(self):
        """Test error event emission for error handling."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit error event
        error_data = {
            "error_type": "ValidationError",
            "message": "Invalid input format",
            "details": {"field": "user_query", "expected": "string"}
        }
        await self.adapter.emit_error(error_data)
        
        # Verify event was sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        error_events = [e for e in events if e["event_type"] == "agent_error"]
        assert len(error_events) >= 1
        
        event = error_events[0]
        assert event["data"]["error_type"] == "ValidationError"
        assert event["data"]["message"] == "Invalid input format"
    
    # === Sub-agent Lifecycle Events Tests ===
    
    async def test_subagent_lifecycle_events(self):
        """Test sub-agent lifecycle event emission."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit subagent started
        subagent_info = {
            "subagent_name": "DataAnalysisAgent",
            "task": "analyze_dataset",
            "parent_agent": self.test_agent_name
        }
        await self.adapter.emit_subagent_started(subagent_info)
        
        # Emit subagent completed
        subagent_result = {
            "subagent_name": "DataAnalysisAgent",
            "status": "completed",
            "result": {"insights": ["trend_up", "correlation_found"]},
            "parent_agent": self.test_agent_name
        }
        await self.adapter.emit_subagent_completed(subagent_result)
        
        # Verify both events were sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        
        started_events = [e for e in events if e["event_type"] == "subagent_started"]
        completed_events = [e for e in events if e["event_type"] == "subagent_completed"]
        
        assert len(started_events) >= 1
        assert len(completed_events) >= 1
        
        # Verify event data
        start_event = started_events[0]
        comp_event = completed_events[0]
        
        assert start_event["data"]["subagent_name"] == "DataAnalysisAgent"
        assert comp_event["data"]["subagent_name"] == "DataAnalysisAgent"
        assert comp_event["data"]["status"] == "completed"
    
    # === Complete Event Sequence Tests ===
    
    async def test_complete_agent_workflow_event_sequence(self):
        """Test complete agent workflow event sequence."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit complete workflow sequence
        await self.adapter.emit_agent_started("Starting user query processing")
        await self.adapter.emit_agent_thinking("Analyzing query requirements")
        await self.adapter.emit_tool_executing("search", {"query": "test search"})
        await self.adapter.emit_tool_completed("search", {"results": ["result1", "result2"]})
        await self.adapter.emit_progress({"step": "synthesis", "progress": 80})
        await self.adapter.emit_agent_completed({"status": "success", "result": "Query processed"})
        
        # Verify all events were sent in sequence
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        assert len(events) == 6
        
        # Verify event sequence
        event_types = [e["event_type"] for e in events]
        expected_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_progress",
            "agent_completed"
        ]
        assert event_types == expected_sequence
    
    async def test_concurrent_event_emission(self):
        """Test concurrent event emission maintains order and isolation."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Create concurrent event emission tasks
        tasks = [
            asyncio.create_task(self.adapter.emit_agent_thinking(f"Thought {i}"))
            for i in range(5)
        ]
        
        # Wait for all emissions
        await asyncio.gather(*tasks)
        
        # Verify all events were sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        thinking_events = [e for e in events if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) == 5
    
    # === Error Handling Tests ===
    
    async def test_missing_bridge_error_handling(self):
        """Test error handling when WebSocket bridge is not configured."""
        # Don't configure bridge - adapter should handle gracefully
        
        # Attempt to emit event without bridge
        with pytest.raises(RuntimeError, match="Missing WebSocket bridge"):
            await self.adapter.emit_agent_started("Test message")
    
    async def test_missing_bridge_with_test_mode(self):
        """Test missing bridge handling in test mode."""
        # Enable test mode
        self.adapter.enable_test_mode()
        
        # Attempt to emit event without bridge (should not raise in test mode)
        await self.adapter.emit_agent_started("Test message in test mode")
        
        # Should complete without error
        assert True  # If we reach here, test passed
    
    async def test_bridge_failure_during_emission(self):
        """Test handling of bridge failures during event emission."""
        # Create failing bridge
        failing_bridge = Mock()
        failing_bridge.emit_agent_event = AsyncMock(side_effect=Exception("Bridge connection lost"))
        
        # Configure adapter with failing bridge
        self.adapter.set_websocket_bridge(
            bridge=failing_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Attempt event emission (should handle failure gracefully)
        with pytest.raises(Exception):
            await self.adapter.emit_agent_started("Test message")
    
    async def test_partial_configuration_error_handling(self):
        """Test handling of partial adapter configuration."""
        # Configure with missing run_id
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=None,
            agent_name=self.test_agent_name
        )
        
        # Should not have valid bridge
        assert not self.adapter.has_websocket_bridge()
        
        # Event emission should fail appropriately
        with pytest.raises(RuntimeError):
            await self.adapter.emit_agent_started("Test message")
    
    # === Event Validation Tests ===
    
    async def test_event_data_validation(self):
        """Test event data validation and formatting."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit event with complex data
        complex_data = {
            "nested": {"key": "value"},
            "array": [1, 2, 3],
            "boolean": True,
            "number": 42.5
        }
        
        await self.adapter.emit_progress(complex_data)
        
        # Verify data was preserved correctly
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        progress_events = [e for e in events if e["event_type"] == "agent_progress"]
        assert len(progress_events) >= 1
        
        event = progress_events[0]
        assert event["data"] == complex_data
    
    async def test_event_metadata_consistency(self):
        """Test event metadata consistency across emissions."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit multiple events
        await self.adapter.emit_agent_started("Start")
        await self.adapter.emit_agent_thinking("Think")
        await self.adapter.emit_agent_completed({"status": "done"})
        
        # Verify all events have consistent metadata
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        assert len(events) == 3
        
        for event in events:
            assert event["run_id"] == self.test_run_id
            assert event["agent_name"] == self.test_agent_name
            assert "timestamp" in event
    
    # === Integration Readiness Tests ===
    
    def test_adapter_websocket_validator_integration(self):
        """Test adapter integration with WebSocket validator."""
        # Verify validator is available
        try:
            validator = get_websocket_validator()
            assert validator is not None
        except ImportError:
            # Validator might not be available in test environment
            pytest.skip("WebSocket validator not available")
    
    async def test_adapter_bridge_interface_compatibility(self):
        """Test adapter compatibility with bridge interface."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Test all required bridge methods are called correctly
        await self.adapter.emit_agent_started("Interface test")
        
        # Verify bridge received call with correct parameters
        events = self.mock_bridge.events_received
        assert len(events) >= 1
        
        event = events[0]
        assert event["event_type"] == "agent_started"
        assert event["run_id"] == self.test_run_id
        assert event["agent_name"] == self.test_agent_name
    
    def test_adapter_configuration_state_management(self):
        """Test adapter manages configuration state correctly."""
        # Initial state
        assert not self.adapter.has_websocket_bridge()
        
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # State should be updated
        assert self.adapter.has_websocket_bridge()
        
        # Reconfigure with different parameters
        new_run_id = "new_run_456"
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=new_run_id,
            agent_name=self.test_agent_name
        )
        
        # State should reflect new configuration
        assert self.adapter._run_id == new_run_id
        assert self.adapter.has_websocket_bridge()
    
    # === Performance Tests ===
    
    async def test_event_emission_performance(self):
        """Test adapter event emission performance."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Measure emission time
        start_time = time.time()
        
        # Emit multiple events
        for i in range(100):
            await self.adapter.emit_agent_thinking(f"Thought {i}")
        
        execution_time = time.time() - start_time
        
        # Should be fast (< 1 second for 100 events)
        assert execution_time < 1.0
        
        # Verify all events were sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        thinking_events = [e for e in events if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) == 100
    
    def test_adapter_memory_usage(self):
        """Test adapter memory usage remains reasonable."""
        import sys
        
        # Measure initial memory
        initial_size = sys.getsizeof(self.adapter)
        
        # Configure adapter multiple times
        for i in range(100):
            self.adapter.set_websocket_bridge(
                bridge=self.mock_bridge,
                run_id=f"run_{i}",
                agent_name=f"agent_{i}"
            )
        
        # Memory growth should be minimal
        final_size = sys.getsizeof(self.adapter)
        growth = final_size - initial_size
        
        # Should not grow significantly
        assert growth < 1000  # Less than 1KB growth
    
    # === Business Value Protection Tests ===
    
    def test_golden_path_event_emission_coverage(self):
        """Test adapter covers all golden path event types."""
        # Verify adapter has all critical event emission methods
        critical_methods = [
            "emit_agent_started",
            "emit_agent_thinking", 
            "emit_tool_executing",
            "emit_tool_completed",
            "emit_agent_completed"
        ]
        
        for method_name in critical_methods:
            assert hasattr(self.adapter, method_name), f"Missing critical method: {method_name}"
            method = getattr(self.adapter, method_name)
            assert callable(method), f"Method {method_name} is not callable"
    
    async def test_user_visibility_event_sequence(self):
        """Test event sequence provides proper user visibility."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit user visibility sequence
        await self.adapter.emit_agent_started("Starting AI processing")
        await self.adapter.emit_agent_thinking("Analyzing your request")
        await self.adapter.emit_tool_executing("search_tool", {"query": "user question"})
        await self.adapter.emit_tool_completed("search_tool", {"results": "found answers"})
        await self.adapter.emit_agent_completed({"status": "success", "answer": "Complete response"})
        
        # Verify complete user visibility chain
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        assert len(events) == 5
        
        # Verify user can see complete AI workflow
        event_types = [e["event_type"] for e in events]
        user_visibility_chain = [
            "agent_started",    # User sees AI started
            "agent_thinking",   # User sees AI thinking  
            "tool_executing",   # User sees tool usage
            "tool_completed",   # User sees tool results
            "agent_completed"   # User sees completion
        ]
        assert event_types == user_visibility_chain
    
    async def test_real_time_feedback_capability(self):
        """Test adapter provides real-time feedback capability."""
        # Configure adapter
        self.adapter.set_websocket_bridge(
            bridge=self.mock_bridge,
            run_id=self.test_run_id,
            agent_name=self.test_agent_name
        )
        
        # Emit real-time updates
        updates = [
            ("agent_thinking", "Step 1: Understanding your question"),
            ("agent_thinking", "Step 2: Searching relevant information"),
            ("agent_thinking", "Step 3: Analyzing search results"),
            ("agent_thinking", "Step 4: Formulating response")
        ]
        
        for event_type, message in updates:
            await self.adapter.emit_agent_thinking(message)
        
        # Verify all real-time updates were sent
        events = self.mock_bridge.get_events_for_agent(self.test_agent_name)
        thinking_events = [e for e in events if e["event_type"] == "agent_thinking"]
        assert len(thinking_events) == 4
        
        # Verify progressive messaging
        messages = [e["data"]["message"] for e in thinking_events]
        for i, (_, expected_msg) in enumerate(updates):
            assert messages[i] == expected_msg
    
    def test_adapter_ssot_compliance(self):
        """Test adapter follows SSOT patterns correctly."""
        # Verify adapter uses centralized WebSocket bridge (not direct WebSocket manager)
        assert hasattr(self.adapter, '_bridge')
        assert not hasattr(self.adapter, '_websocket_manager')  # Should not bypass bridge
        
        # Verify adapter doesn't duplicate event emission logic
        assert hasattr(self.adapter, 'set_websocket_bridge')
        assert hasattr(self.adapter, 'has_websocket_bridge')
        
        # Verify test mode support for development
        assert hasattr(self.adapter, 'enable_test_mode')
        assert hasattr(self.adapter, '_test_mode')


if __name__ == "__main__":
    # Run tests with pytest for better async support
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])