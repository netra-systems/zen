"""
Unit Tests for Issue #1048: WebSocket Event Structure Field Missing Production Events

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Chat Value Delivery & User Trust
- Value Impact: Ensures tool_name and results fields are present in WebSocket events
- Strategic Impact: Fixes missing fields that cause 3/8 mission critical tests to fail

This test validates that WebSocket events contain the required fields:
- tool_executing events must have tool_name field
- tool_completed events must have results field
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


class TestWebSocketEventStructureIssue1048:
    """Test WebSocket event structure for Issue #1048."""
    
    @pytest.fixture(autouse=True)
    def setup_emitter(self):
        """Set up test environment."""
        # Create mock WebSocket manager
        self.mock_manager = MagicMock()
        self.mock_manager.emit_critical_event = AsyncMock()
        self.mock_manager.is_connection_active = MagicMock(return_value=True)
        
        # Create emitter instance
        self.emitter = UnifiedWebSocketEmitter(
            manager=self.mock_manager,
            user_id="test_user_1048",
            context=None
        )

    @pytest.mark.asyncio
    async def test_tool_executing_event_has_tool_name_field(self):
        """Test that tool_executing events include tool_name field at top level."""
        # Arrange
        test_data = {
            "tool_name": "cost_optimizer",
            "parameters": {"budget": 50000},
            "timestamp": "2025-09-17T21:00:00Z"
        }
        
        # Act
        result = await self.emitter.emit_tool_executing(test_data)
        
        # Assert
        assert result, "tool_executing event should emit successfully"
        
        # Verify the manager was called with correct event structure
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        assert call_args[1]["event_type"] == "tool_executing"
        event_data = call_args[1]["data"]
        
        # CRITICAL: tool_name must be at top level for Issue #1048
        assert "tool_name" in event_data, "tool_executing event must have tool_name field"
        assert event_data["tool_name"] == "cost_optimizer"
        
        # Verify other required fields are preserved
        assert "parameters" in event_data
        assert event_data["parameters"]["budget"] == 50000

    @pytest.mark.asyncio
    async def test_tool_completed_event_has_results_field(self):
        """Test that tool_completed events include results field at top level."""
        # Arrange - simulate tool completion with nested result
        test_data = {
            "tool_name": "cost_optimizer",
            "metadata": {
                "result": {
                    "optimizations": ["right-sizing", "reserved instances"],
                    "projected_savings": 15000,
                    "implementation_timeline": "30 days"
                },
                "duration": 2.5
            },
            "status": "success"
        }
        
        # Act
        result = await self.emitter.emit_tool_completed(test_data)
        
        # Assert
        self.assertTrue(result, "tool_completed event should emit successfully")
        
        # Verify the manager was called with correct event structure
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        
        self.assertEqual(call_args[1]["event_type"], "tool_completed")
        event_data = call_args[1]["data"]
        
        # CRITICAL: results must be at top level for Issue #1048
        self.assertIn("results", event_data, "tool_completed event must have results field")
        
        # Verify results content is promoted correctly
        results = event_data["results"]
        self.assertIn("optimizations", results)
        self.assertEqual(results["projected_savings"], 15000)
        
        # Verify backward compatibility - metadata.result should still exist
        self.assertIn("metadata", event_data)
        self.assertIn("result", event_data["metadata"])

    @pytest.mark.asyncio
    async def test_tool_executing_without_tool_name_fails_gracefully(self):
        """Test tool_executing event behavior when tool_name is missing."""
        # Arrange - data without tool_name
        test_data = {
            "parameters": {"query": "test"},
            "timestamp": "2025-09-17T21:00:00Z"
        }
        
        # Act
        result = await self.emitter.emit_tool_executing(test_data)
        
        # Assert - should still emit but without top-level tool_name promotion
        self.assertTrue(result, "Event should still emit even without tool_name")
        
        # Verify event was sent but without tool_name promotion
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        event_data = call_args[1]["data"]
        
        # Should not have tool_name at top level since it wasn't provided
        self.assertNotIn("tool_name", event_data)

    @pytest.mark.asyncio
    async def test_tool_completed_without_results_fails_gracefully(self):
        """Test tool_completed event behavior when results are missing."""
        # Arrange - data without metadata.result
        test_data = {
            "tool_name": "test_tool",
            "status": "success",
            "metadata": {
                "duration": 1.0
            }
        }
        
        # Act
        result = await self.emitter.emit_tool_completed(test_data)
        
        # Assert - should still emit but without results promotion
        self.assertTrue(result, "Event should still emit even without results")
        
        # Verify event was sent but without results promotion
        self.mock_manager.emit_critical_event.assert_called_once()
        call_args = self.mock_manager.emit_critical_event.call_args
        event_data = call_args[1]["data"]
        
        # Should not have results at top level since metadata.result wasn't provided
        self.assertNotIn("results", event_data)

    @pytest.mark.asyncio
    async def test_event_structure_preserves_all_original_fields(self):
        """Test that event structure enhancement preserves all original fields."""
        # Arrange
        tool_executing_data = {
            "tool_name": "data_analyzer",
            "parameters": {"dataset": "costs.csv"},
            "execution_id": "exec_123",
            "priority": "high",
            "metadata": {
                "user_tier": "enterprise",
                "estimated_duration": 5.0
            }
        }
        
        # Act
        await self.emitter.emit_tool_executing(tool_executing_data)
        
        # Assert - all original fields preserved
        call_args = self.mock_manager.emit_critical_event.call_args
        event_data = call_args[1]["data"]
        
        # Verify all original fields are preserved
        self.assertEqual(event_data["tool_name"], "data_analyzer")
        self.assertEqual(event_data["parameters"]["dataset"], "costs.csv")
        self.assertEqual(event_data["execution_id"], "exec_123")
        self.assertEqual(event_data["priority"], "high")
        self.assertIn("metadata", event_data)
        self.assertEqual(event_data["metadata"]["user_tier"], "enterprise")

    @pytest.mark.asyncio
    async def test_multiple_events_maintain_field_structure(self):
        """Test that multiple events maintain consistent field structure."""
        # Reset mock for clean test
        self.mock_manager.reset_mock()
        
        # Test tool_executing event
        executing_data = {"tool_name": "optimizer", "parameters": {"type": "cost"}}
        await self.emitter.emit_tool_executing(executing_data)
        
        # Test tool_completed event
        completed_data = {
            "tool_name": "optimizer",
            "metadata": {"result": {"savings": 10000}},
            "status": "success"
        }
        await self.emitter.emit_tool_completed(completed_data)
        
        # Verify both events were emitted
        self.assertEqual(self.mock_manager.emit_critical_event.call_count, 2)
        
        # Verify first event (tool_executing) has tool_name
        first_call = self.mock_manager.emit_critical_event.call_args_list[0]
        self.assertEqual(first_call[1]["event_type"], "tool_executing")
        self.assertIn("tool_name", first_call[1]["data"])
        
        # Verify second event (tool_completed) has results
        second_call = self.mock_manager.emit_critical_event.call_args_list[1]
        self.assertEqual(second_call[1]["event_type"], "tool_completed")
        self.assertIn("results", second_call[1]["data"])
        self.assertEqual(second_call[1]["data"]["results"]["savings"], 10000)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])