#!/usr/bin/env python3
"""
Test Suite for Progress Streaming Agent
========================================

Comprehensive tests for the ProgressStreamingManager functionality including:
- Real-time progress streaming across multiple output modes
- Event aggregation and progress calculations 
- WebSocket integration for web interfaces
- Console formatting and display
- JSON output for programmatic consumption
- Integration with existing progress tracking infrastructure

Business Value: Ensures reliable progress reporting during test execution,
preventing user confusion and abandonment during long-running operations.
"""

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from loguru import logger

# Import the agent under test
from test_framework.orchestration.progress_streaming_manager import (
    ProgressStreamingManager, ProgressOutputMode, ProgressEventType,
    LayerProgressState, StreamingConfig, create_console_streaming_agent,
    create_json_streaming_agent, create_websocket_streaming_agent
)
from test_framework.progress_tracker import ProgressStatus, CategoryProgress


class MockWebSocketManager:
    """Mock WebSocket manager for testing"""
    
    def __init__(self):
        self.messages = []
        self.connected_threads = set()
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Mock send to thread"""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'timestamp': time.time()
        })
        return True
    
    async def broadcast(self, message: Dict[str, Any]) -> bool:
        """Mock broadcast"""
        self.messages.append({
            'thread_id': 'broadcast',
            'message': message,
            'timestamp': time.time()
        })
        return True
    
    def get_messages_for_thread(self, thread_id: str) -> List[Dict]:
        """Get messages for specific thread"""
        return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def clear_messages(self):
        """Clear all messages"""
        self.messages.clear()


class EventCapture:
    """Utility class to capture streaming events for testing"""
    
    def __init__(self):
        self.events = []
        self.event_counts = {}
        self.last_status_update = None
    
    async def capture_event(self, event_type: ProgressEventType, data: Dict[str, Any]):
        """Capture streaming event"""
        event_data = {
            'type': event_type.value,
            'data': data,
            'timestamp': time.time()
        }
        self.events.append(event_data)
        self.event_counts[event_type.value] = self.event_counts.get(event_type.value, 0) + 1
    
    def capture_status_sync(self, event_type: ProgressEventType, data: Dict[str, Any]):
        """Synchronous event capture"""
        asyncio.create_task(self.capture_event(event_type, data))
    
    def get_events_of_type(self, event_type: str) -> List[Dict]:
        """Get events of specific type"""
        return [event for event in self.events if event['type'] == event_type]
    
    def clear(self):
        """Clear captured events"""
        self.events.clear()
        self.event_counts.clear()
        self.last_status_update = None


@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project root for testing"""
    test_reports_dir = tmp_path / "test_reports" / "progress"
    test_reports_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    return MockWebSocketManager()


@pytest.fixture
def event_capture():
    """Create event capture utility"""
    return EventCapture()


@pytest.fixture
def streaming_config():
    """Create test streaming configuration"""
    return StreamingConfig(
        output_mode=ProgressOutputMode.CONSOLE,
        update_interval=0.1,  # Fast updates for testing
        websocket_enabled=True,
        console_colors=False,  # Disable colors for test output
        show_detailed_progress=True
    )


@pytest.fixture
async def progress_agent(temp_project_root, streaming_config):
    """Create progress streaming agent for testing"""
    agent = ProgressStreamingManager(temp_project_root, streaming_config)
    yield agent
    
    # Cleanup
    if agent.active:
        await agent.stop_streaming(success=True)


class TestProgressStreamingManager:
    """Test suite for ProgressStreamingManager core functionality"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, temp_project_root, streaming_config):
        """Test agent initialization and configuration"""
        agent = ProgressStreamingManager(temp_project_root, streaming_config)
        
        assert agent.project_root == temp_project_root
        assert agent.config.output_mode == ProgressOutputMode.CONSOLE
        assert agent.config.update_interval == 0.1
        assert not agent.active
        assert len(agent.layers) == 0
        assert len(agent.background_tasks) == 0
        assert agent.agent_id.startswith("progress_streamer_")
    
    @pytest.mark.asyncio
    async def test_start_stop_streaming(self, progress_agent):
        """Test starting and stopping streaming"""
        layers = ["layer1", "layer2", "layer3"]
        
        # Start streaming
        success = await progress_agent.start_streaming(layers, "test_run")
        assert success
        assert progress_agent.active
        assert progress_agent.start_time is not None
        assert len(progress_agent.layers) == 3
        assert all(layer in progress_agent.layers for layer in layers)
        
        # Try starting again (should fail)
        success = await progress_agent.start_streaming(layers, "test_run2")
        assert not success  # Should fail because already active
        
        # Stop streaming
        await progress_agent.stop_streaming(success=True)
        assert not progress_agent.active
        assert progress_agent.end_time is not None
    
    @pytest.mark.asyncio
    async def test_layer_progress_updates(self, progress_agent):
        """Test layer progress updates"""
        layers = ["test_layer"]
        await progress_agent.start_streaming(layers, "test_run")
        
        layer_name = "test_layer"
        
        # Start layer
        await progress_agent.update_layer_progress(
            layer_name, status=ProgressStatus.RUNNING
        )
        
        layer = progress_agent.layers[layer_name]
        assert layer.status == ProgressStatus.RUNNING
        assert layer.start_time is not None
        
        # Update with category
        await progress_agent.update_layer_progress(
            layer_name, "category1", status=ProgressStatus.RUNNING, progress=50.0
        )
        
        assert "category1" in layer.categories
        category = layer.categories["category1"]
        assert category.status == ProgressStatus.RUNNING
        assert category.progress_percentage == 50.0
        
        # Complete category
        await progress_agent.update_layer_progress(
            layer_name, "category1", status=ProgressStatus.COMPLETED,
            test_counts={"total": 10, "passed": 8, "failed": 2}
        )
        
        category = layer.categories["category1"]
        assert category.status == ProgressStatus.COMPLETED
        assert category.total_tests == 10
        assert category.passed_tests == 8
        assert category.failed_tests == 2
        
        # Layer should update aggregated metrics
        layer.update_from_categories()
        assert layer.total_tests == 10
        assert layer.passed_tests == 8
        assert layer.failed_tests == 2
    
    @pytest.mark.asyncio
    async def test_background_task_updates(self, progress_agent):
        """Test background task progress updates"""
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        task_id = "background_task_1"
        
        # Start background task
        await progress_agent.update_background_task(task_id, "started", progress=0.0)
        
        assert task_id in progress_agent.background_tasks
        task = progress_agent.background_tasks[task_id]
        assert task["status"] == "started"
        assert task["progress"] == 0.0
        assert task["start_time"] is not None
        
        # Update progress
        await progress_agent.update_background_task(task_id, "running", progress=50.0)
        
        task = progress_agent.background_tasks[task_id]
        assert task["status"] == "running"
        assert task["progress"] == 50.0
        
        # Complete task
        await progress_agent.update_background_task(task_id, "completed", progress=100.0)
        
        task = progress_agent.background_tasks[task_id]
        assert task["status"] == "completed"
        assert task["progress"] == 100.0
        assert "end_time" in task
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, progress_agent, event_capture):
        """Test event subscription mechanism"""
        # Add event subscriber
        progress_agent.add_event_subscriber(event_capture.capture_status_sync)
        
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        # Generate some events
        await progress_agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await progress_agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.RUNNING)
        await progress_agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.COMPLETED)
        
        # Wait for events to propagate
        await asyncio.sleep(0.2)
        
        # Check events were captured
        assert len(event_capture.events) > 0
        assert event_capture.event_counts.get('layer_started', 0) > 0
    
    @pytest.mark.asyncio
    async def test_status_generation(self, progress_agent):
        """Test comprehensive status generation"""
        layers = ["layer1", "layer2"]
        await progress_agent.start_streaming(layers, "test_run")
        
        # Set up some progress
        await progress_agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await progress_agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.COMPLETED,
                                                  test_counts={"total": 5, "passed": 5, "failed": 0})
        await progress_agent.update_layer_progress("layer1", "cat2", status=ProgressStatus.RUNNING,
                                                  progress=75.0)
        
        await progress_agent.update_background_task("task1", "running", progress=60.0)
        
        # Generate status
        status = progress_agent.get_current_status()
        
        assert status["agent_id"] == progress_agent.agent_id
        assert status["overall"]["active"] == True
        assert status["overall"]["layers_count"] == 2
        assert status["overall"]["background_tasks_count"] == 1
        
        # Check layer details
        layer1_status = next(layer for layer in status["layers"] if layer["name"] == "layer1")
        assert layer1_status["status"] == "running"
        assert layer1_status["categories_total"] == 2
        assert layer1_status["categories_completed"] == 1
        assert layer1_status["test_counts"]["total"] == 5
        assert layer1_status["test_counts"]["passed"] == 5
        
        # Check background tasks
        assert len(status["background_tasks"]) == 1
        task_status = status["background_tasks"][0]
        assert task_status["task_id"] == "task1"
        assert task_status["status"] == "running"
        assert task_status["progress"] == 60.0
    
    @pytest.mark.asyncio
    async def test_final_summary_generation(self, progress_agent):
        """Test final summary generation"""
        layers = ["layer1", "layer2"]
        await progress_agent.start_streaming(layers, "test_run")
        
        # Set up completed progress
        for layer_name in layers:
            await progress_agent.update_layer_progress(layer_name, status=ProgressStatus.RUNNING)
            await progress_agent.update_layer_progress(layer_name, "cat1", status=ProgressStatus.COMPLETED,
                                                      test_counts={"total": 10, "passed": 8, "failed": 2})
            await progress_agent.update_layer_progress(layer_name, status=ProgressStatus.COMPLETED)
        
        await progress_agent.update_background_task("task1", "completed", progress=100.0)
        
        # Stop and get summary
        await progress_agent.stop_streaming(success=True)
        
        # Generate summary manually to test
        summary = progress_agent._generate_final_summary(True)
        
        assert summary["success"] == True
        assert summary["layers_count"] == 2
        assert summary["background_tasks_count"] == 1
        assert summary["overall_test_counts"]["total"] == 20
        assert summary["overall_test_counts"]["passed"] == 16
        assert summary["overall_test_counts"]["failed"] == 4
        assert summary["overall_success_rate"] == 0.8  # 16/20
        
        # Check layer summaries
        assert len(summary["layers"]) == 2
        for layer_summary in summary["layers"]:
            assert layer_summary["status"] == "completed"
            assert layer_summary["categories_completed"] == 1
            assert layer_summary["test_counts"]["total"] == 10
    
    @pytest.mark.asyncio
    async def test_layer_progress_state_updates(self, temp_project_root):
        """Test LayerProgressState functionality"""
        layer = LayerProgressState(layer_name="test_layer")
        
        # Add categories
        cat1 = CategoryProgress(name="category1")
        cat1.start()
        cat1.update_test_counts(total=10, passed=8, failed=2)
        cat1.complete(success=True)
        
        cat2 = CategoryProgress(name="category2")
        cat2.start()
        cat2.update_test_counts(total=15, passed=15, failed=0)
        cat2.complete(success=True)
        
        layer.categories["category1"] = cat1
        layer.categories["category2"] = cat2
        
        # Update layer from categories
        layer.update_from_categories()
        
        assert layer.categories_total == 2
        assert layer.categories_completed == 2
        assert layer.total_tests == 25
        assert layer.passed_tests == 23
        assert layer.failed_tests == 2
        assert layer.success_rate == 0.92  # 23/25


class TestOutputModes:
    """Test different output modes of the streaming agent"""
    
    @pytest.mark.asyncio
    async def test_console_output_mode(self, temp_project_root):
        """Test console output mode"""
        config = StreamingConfig(
            output_mode=ProgressOutputMode.CONSOLE,
            console_colors=False  # Easier to test without colors
        )
        agent = ProgressStreamingManager(temp_project_root, config)
        
        # Test console formatting methods
        assert agent._format_duration(timedelta(seconds=65)) == "1m 5s"
        assert agent._format_duration(timedelta(seconds=3661)) == "1h 1m 1s"
        
        progress_bar = agent._create_progress_bar(50.0, 20)
        assert len(progress_bar) == 22  # [20 chars]
        assert '█' in progress_bar
        assert '░' in progress_bar
    
    @pytest.mark.asyncio
    async def test_json_output_mode(self, temp_project_root, capsys):
        """Test JSON output mode"""
        config = StreamingConfig(output_mode=ProgressOutputMode.JSON)
        agent = ProgressStreamingManager(temp_project_root, config)
        
        await agent.start_streaming(["layer1"], "test_run")
        
        # Generate an event that should output JSON
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Clean up
        await agent.stop_streaming(success=True)
    
    @pytest.mark.asyncio
    async def test_websocket_output_mode(self, temp_project_root, mock_websocket_manager):
        """Test WebSocket output mode"""
        config = StreamingConfig(
            output_mode=ProgressOutputMode.WEBSOCKET,
            websocket_enabled=True,
            websocket_thread_id="test_thread"
        )
        agent = ProgressStreamingManager(temp_project_root, config)
        agent.set_websocket_manager(mock_websocket_manager, "test_thread")
        
        await agent.start_streaming(["layer1"], "test_run")
        
        # Generate events
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.RUNNING)
        await agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.COMPLETED)
        
        # Wait for processing
        await asyncio.sleep(0.3)
        
        # Check WebSocket messages were sent
        messages = mock_websocket_manager.get_messages_for_thread("test_thread")
        assert len(messages) > 0
        
        # Verify message structure
        for msg in messages:
            assert "message" in msg
            assert "timestamp" in msg
            assert msg["thread_id"] == "test_thread"
        
        await agent.stop_streaming(success=True)


class TestWebSocketIntegration:
    """Test WebSocket integration functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self, temp_project_root, mock_websocket_manager):
        """Test WebSocket manager integration"""
        agent = ProgressStreamingManager(temp_project_root)
        agent.set_websocket_manager(mock_websocket_manager, "test_thread")
        
        assert agent.websocket_manager is mock_websocket_manager
        assert agent.config.websocket_thread_id == "test_thread"
        assert agent.websocket_notifier is not None
    
    @pytest.mark.asyncio
    async def test_websocket_event_mapping(self, temp_project_root, mock_websocket_manager):
        """Test mapping of streaming events to WebSocket events"""
        agent = ProgressStreamingManager(temp_project_root)
        agent.set_websocket_manager(mock_websocket_manager, "test_thread")
        
        await agent.start_streaming(["layer1"], "test_run")
        
        # Test different event types
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)  # Should trigger agent_started
        await agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.RUNNING, progress=25.0)  # Should trigger agent_thinking
        await agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.COMPLETED)  # Should trigger tool_completed
        
        # Wait for WebSocket processing
        await asyncio.sleep(0.5)
        
        messages = mock_websocket_manager.get_messages_for_thread("test_thread")
        
        # Should have various WebSocket messages
        assert len(messages) > 0
        
        await agent.stop_streaming(success=True)
    
    @pytest.mark.asyncio 
    async def test_websocket_periodic_updates(self, temp_project_root, mock_websocket_manager):
        """Test periodic WebSocket status updates"""
        config = StreamingConfig(
            websocket_enabled=True,
            websocket_thread_id="test_thread",
            update_interval=0.1  # Fast updates
        )
        agent = ProgressStreamingManager(temp_project_root, config)
        agent.set_websocket_manager(mock_websocket_manager, "test_thread")
        
        await agent.start_streaming(["layer1"], "test_run")
        
        # Set up some active progress
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await agent.update_layer_progress("layer1", "cat1", status=ProgressStatus.RUNNING, progress=30.0)
        
        # Wait for periodic updates
        await asyncio.sleep(0.5)
        
        messages = mock_websocket_manager.get_messages_for_thread("test_thread")
        
        # Should have received periodic updates
        assert len(messages) > 0
        
        # Look for agent_thinking messages (periodic updates)
        thinking_messages = [msg for msg in messages if 'agent_thinking' in str(msg.get('message', {}))]
        assert len(thinking_messages) > 0
        
        await agent.stop_streaming(success=True)


class TestUtilityFunctions:
    """Test utility functions and factory methods"""
    
    def test_create_console_streaming_agent(self, temp_project_root):
        """Test console streaming agent factory"""
        agent = create_console_streaming_agent(temp_project_root)
        
        assert agent.project_root == temp_project_root
        assert agent.config.output_mode == ProgressOutputMode.CONSOLE
        assert agent.config.console_colors == True
        assert agent.config.show_detailed_progress == True
        assert agent.config.show_eta == True
        assert agent.config.update_interval == 1.0
    
    def test_create_json_streaming_agent(self, temp_project_root):
        """Test JSON streaming agent factory"""
        agent = create_json_streaming_agent(temp_project_root)
        
        assert agent.project_root == temp_project_root
        assert agent.config.output_mode == ProgressOutputMode.JSON
        assert agent.config.websocket_enabled == False
        assert agent.config.show_detailed_progress == True
        assert agent.config.update_interval == 0.5
    
    def test_create_websocket_streaming_agent(self, temp_project_root, mock_websocket_manager):
        """Test WebSocket streaming agent factory"""
        agent = create_websocket_streaming_agent(
            mock_websocket_manager, "test_thread", temp_project_root
        )
        
        assert agent.project_root == temp_project_root
        assert agent.config.output_mode == ProgressOutputMode.WEBSOCKET
        assert agent.config.websocket_enabled == True
        assert agent.config.websocket_thread_id == "test_thread"
        assert agent.websocket_manager is mock_websocket_manager


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_update_without_active_streaming(self, temp_project_root):
        """Test updates when streaming is not active"""
        agent = ProgressStreamingManager(temp_project_root)
        
        # Should not raise exception, should handle gracefully
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await agent.update_background_task("task1", "started")
        
        # No layers should be created since streaming not active
        assert len(agent.layers) == 0
        assert len(agent.background_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_invalid_layer_updates(self, progress_agent):
        """Test updates to non-existent layers"""
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        # Update non-existent layer should be handled gracefully
        await progress_agent.update_layer_progress("non_existent_layer", status=ProgressStatus.RUNNING)
        
        # Should not create the layer
        assert "non_existent_layer" not in progress_agent.layers
        assert "layer1" in progress_agent.layers
    
    @pytest.mark.asyncio
    async def test_multiple_stop_calls(self, progress_agent):
        """Test multiple stop streaming calls"""
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        # First stop should work
        await progress_agent.stop_streaming(success=True)
        assert not progress_agent.active
        
        # Second stop should be handled gracefully
        await progress_agent.stop_streaming(success=False)
        # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_websocket_integration_without_websocket_available(self, temp_project_root):
        """Test behavior when WebSocket integration is not available"""
        # This tests the graceful fallback when WebSocket modules aren't available
        config = StreamingConfig(websocket_enabled=True)
        agent = ProgressStreamingManager(temp_project_root, config)
        
        # Should work even without WebSocket manager
        await agent.start_streaming(["layer1"], "test_run")
        await agent.update_layer_progress("layer1", status=ProgressStatus.RUNNING)
        await agent.stop_streaming(success=True)
        
        # Should complete without errors


class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_high_frequency_updates(self, progress_agent):
        """Test handling of high frequency progress updates"""
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        start_time = time.time()
        
        # Send many rapid updates
        for i in range(100):
            await progress_agent.update_layer_progress(
                "layer1", "category1", progress=i, 
                test_counts={"total": 100, "passed": i, "failed": 0}
            )
        
        end_time = time.time()
        update_time = end_time - start_time
        
        # Should handle 100 updates reasonably quickly (under 2 seconds)
        assert update_time < 2.0
        
        # Final state should be correct
        layer = progress_agent.layers["layer1"]
        category = layer.categories["category1"]
        assert category.progress_percentage == 99.0  # Last update
        assert category.passed_tests == 99
    
    @pytest.mark.asyncio
    async def test_many_background_tasks(self, progress_agent):
        """Test handling many background tasks"""
        await progress_agent.start_streaming(["layer1"], "test_run")
        
        # Create many background tasks
        num_tasks = 50
        for i in range(num_tasks):
            task_id = f"task_{i}"
            await progress_agent.update_background_task(task_id, "running", progress=i * 2)
        
        assert len(progress_agent.background_tasks) == num_tasks
        
        # Generate status (should handle large number of tasks)
        status = progress_agent.get_current_status()
        assert len(status["background_tasks"]) == num_tasks
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_long_running_stream(self, progress_agent):
        """Test memory usage doesn't grow excessively with long-running streams"""
        await progress_agent.start_streaming(["layer1", "layer2"], "test_run")
        
        # Simulate long-running execution with many events
        for cycle in range(10):
            for layer in ["layer1", "layer2"]:
                for cat in ["cat1", "cat2", "cat3"]:
                    await progress_agent.update_layer_progress(layer, cat, progress=cycle * 10)
                    await progress_agent.update_background_task(f"task_{cycle}", "running", progress=cycle * 10)
        
        # Event queue should not grow indefinitely
        # (This is a basic check - in real scenarios you'd want more sophisticated memory monitoring)
        with progress_agent._queue_lock:
            queue_size = len(progress_agent._event_queue)
        
        # Queue should be reasonable size (events should be processed)
        assert queue_size < 100


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])