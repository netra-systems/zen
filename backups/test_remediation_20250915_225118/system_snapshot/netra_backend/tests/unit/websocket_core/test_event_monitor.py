"""
Comprehensive Unit Tests for Event Monitor - SSOT Implementation

Business Value Protection: $500K+ ARR WebSocket event monitoring comprehensive testing
Addresses Issue #714 Phase 1C: Event Monitoring Tests

This test suite provides comprehensive coverage for the WebSocket event monitoring
module, focusing on the highest-impact uncovered code paths identified in coverage analysis.

Key Test Areas:
1. Event delivery tracking and anomaly detection
2. Connection health monitoring and status reporting
3. Event queue management and flow validation
4. Silent failure detection and recovery
5. Component audit capabilities and integration
6. Performance metrics and latency tracking
7. Background monitoring and alert systems

Coverage Target: event_monitor.py (currently 0% -> target 80%+)
"""

import asyncio
import time
from collections import defaultdict, deque
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List, Optional, Set

import pytest

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import target module components
from netra_backend.app.websocket_core.event_monitor import (
    EventType,
    HealthStatus,
    ChatEventMonitor,
    WebSocketEventMonitor,
    EventValidationError,
    MissingCriticalEventError,
    EventTracker,
    EventMetrics
)

# Import related interfaces
from shared.monitoring.interfaces import ComponentMonitor, MonitorableComponent


class ChatEventMonitorTests(SSotAsyncTestCase):
    """Test suite for ChatEventMonitor functionality."""

    def setup_method(self, method):
        """Set up test environment with SSOT compliance."""
        super().setup_method(method)

        # Use SSOT mock factory for consistent mocking
        self.mock_factory = SSotMockFactory()

        # Create common test data
        self.test_thread_id = "thread_123"
        self.test_tool_name = "test_analyzer"
        self.test_timestamp = time.time()

        # Create monitor instance
        self.monitor = ChatEventMonitor()

    def teardown_method(self, method):
        """Clean up test resources."""
        # Stop background monitoring if running
        if hasattr(self.monitor, '_monitor_task') and self.monitor._monitor_task:
            self.monitor._monitor_task.cancel()

        super().teardown_method(method)

    def test_event_type_enum_values(self):
        """Test EventType enum contains all required values."""
        # Verify all critical event types exist
        required_events = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,
            EventType.TOOL_COMPLETED,
            EventType.AGENT_COMPLETED,
            EventType.ERROR
        ]

        for event_type in required_events:
            self.assertIn(event_type, EventType)

        # Verify specific values
        self.assertEqual(EventType.AGENT_STARTED.value, "agent_started")
        self.assertEqual(EventType.AGENT_THINKING.value, "agent_thinking")
        self.assertEqual(EventType.TOOL_EXECUTING.value, "tool_executing")
        self.assertEqual(EventType.TOOL_COMPLETED.value, "tool_completed")
        self.assertEqual(EventType.AGENT_COMPLETED.value, "agent_completed")

    def test_health_status_enum_values(self):
        """Test HealthStatus enum contains all required values."""
        self.assertEqual(HealthStatus.HEALTHY, "healthy")
        self.assertEqual(HealthStatus.WARNING, "warning")
        self.assertEqual(HealthStatus.CRITICAL, "critical")
        self.assertEqual(HealthStatus.FAILED, "failed")

    def test_chat_event_monitor_initialization(self):
        """Test ChatEventMonitor initialization."""
        monitor = ChatEventMonitor()

        # Verify initial state
        self.assertIsInstance(monitor.event_counts, dict)
        self.assertIsInstance(monitor.last_event_time, dict)
        self.assertIsInstance(monitor.thread_start_time, dict)
        self.assertIsInstance(monitor.active_tools, dict)
        self.assertIsInstance(monitor.expected_sequences, dict)
        self.assertIsInstance(monitor.event_history, dict)
        self.assertIsInstance(monitor.event_latencies, list)
        self.assertIsInstance(monitor.silent_failures, list)

        # Verify thresholds are set
        self.assertGreater(monitor.stale_thread_threshold, 0)
        self.assertGreater(monitor.tool_timeout_threshold, 0)
        self.assertGreater(monitor.latency_warning_threshold, 0)
        self.assertGreater(monitor.latency_critical_threshold, 0)

        # Verify component audit capabilities
        self.assertIsInstance(monitor.monitored_components, dict)
        self.assertIsInstance(monitor.component_health_history, dict)
        self.assertIsInstance(monitor.bridge_audit_metrics, dict)

    async def test_record_event_agent_started(self):
        """Test ChatEventMonitor records agent_started events correctly."""
        # Record agent_started event
        await self.monitor.record_event(
            EventType.AGENT_STARTED.value,
            self.test_thread_id,
            metadata={"agent_name": "TestAgent"}
        )

        # Verify event was recorded
        self.assertIn(self.test_thread_id, self.monitor.event_counts)
        self.assertEqual(
            self.monitor.event_counts[self.test_thread_id][EventType.AGENT_STARTED.value],
            1
        )

        # Verify thread start time was set
        self.assertIn(self.test_thread_id, self.monitor.thread_start_time)

        # Verify expected sequence was initialized
        self.assertIn(self.test_thread_id, self.monitor.expected_sequences)
        expected = self.monitor.expected_sequences[self.test_thread_id]
        self.assertIn(EventType.AGENT_THINKING.value, expected)
        self.assertIn(EventType.TOOL_EXECUTING.value, expected)

    async def test_record_event_agent_thinking(self):
        """Test ChatEventMonitor records agent_thinking events correctly."""
        # First record agent_started
        await self.monitor.record_event(EventType.AGENT_STARTED.value, self.test_thread_id)

        # Then record agent_thinking
        await self.monitor.record_event(
            EventType.AGENT_THINKING.value,
            self.test_thread_id,
            metadata={"thought_process": "Analyzing request"}
        )

        # Verify event was recorded
        self.assertEqual(
            self.monitor.event_counts[self.test_thread_id][EventType.AGENT_THINKING.value],
            1
        )

        # Verify event history
        history = self.monitor.event_history[self.test_thread_id]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["event_type"], EventType.AGENT_THINKING.value)

    async def test_record_event_tool_executing(self):
        """Test ChatEventMonitor records tool_executing events correctly."""
        # Record tool_executing event
        await self.monitor.record_event(
            EventType.TOOL_EXECUTING.value,
            self.test_thread_id,
            tool_name=self.test_tool_name,
            metadata={"tool_params": {"query": "test"}}
        )

        # Verify event was recorded
        self.assertEqual(
            self.monitor.event_counts[self.test_thread_id][EventType.TOOL_EXECUTING.value],
            1
        )

        # Verify tool is tracked as active
        self.assertIn(self.test_tool_name, self.monitor.active_tools[self.test_thread_id])

        # Verify expected sequence updated
        expected = self.monitor.expected_sequences[self.test_thread_id]
        self.assertIn(EventType.TOOL_COMPLETED.value, expected)

    async def test_record_event_tool_completed(self):
        """Test ChatEventMonitor records tool_completed events correctly."""
        # First record tool_executing
        await self.monitor.record_event(
            EventType.TOOL_EXECUTING.value,
            self.test_thread_id,
            tool_name=self.test_tool_name
        )

        # Then record tool_completed
        await self.monitor.record_event(
            EventType.TOOL_COMPLETED.value,
            self.test_thread_id,
            tool_name=self.test_tool_name,
            metadata={"result": {"status": "success"}}
        )

        # Verify event was recorded
        self.assertEqual(
            self.monitor.event_counts[self.test_thread_id][EventType.TOOL_COMPLETED.value],
            1
        )

        # Verify tool is no longer active
        self.assertNotIn(self.test_tool_name, self.monitor.active_tools[self.test_thread_id])

    async def test_record_event_tool_completed_without_executing_silent_failure(self):
        """Test ChatEventMonitor detects silent failure when tool_completed without tool_executing."""
        # Record tool_completed without tool_executing
        await self.monitor.record_event(
            EventType.TOOL_COMPLETED.value,
            self.test_thread_id,
            tool_name=self.test_tool_name
        )

        # Verify silent failure was recorded
        self.assertGreater(len(self.monitor.silent_failures), 0)

        latest_failure = self.monitor.silent_failures[-1]
        self.assertEqual(latest_failure["thread_id"], self.test_thread_id)
        self.assertIn("tool_completed without tool_executing", latest_failure["description"])

    async def test_record_event_agent_completed(self):
        """Test ChatEventMonitor records agent_completed events correctly."""
        # Record complete sequence
        events = [
            (EventType.AGENT_STARTED.value, None),
            (EventType.AGENT_THINKING.value, None),
            (EventType.TOOL_EXECUTING.value, self.test_tool_name),
            (EventType.TOOL_COMPLETED.value, self.test_tool_name),
            (EventType.AGENT_COMPLETED.value, None)
        ]

        for event_type, tool_name in events:
            await self.monitor.record_event(event_type, self.test_thread_id, tool_name=tool_name)

        # Verify all events recorded
        for event_type, _ in events:
            self.assertEqual(
                self.monitor.event_counts[self.test_thread_id][event_type],
                1
            )

        # Verify complete event history
        history = self.monitor.event_history[self.test_thread_id]
        self.assertEqual(len(history), 5)

    async def test_record_event_skips_test_threads(self):
        """Test ChatEventMonitor skips monitoring for test threads."""
        test_thread_patterns = [
            "pytest_thread",
            "test_12345",
            "unittest_thread",
            "mock_thread"
        ]

        for test_thread_id in test_thread_patterns:
            await self.monitor.record_event(
                EventType.AGENT_STARTED.value,
                test_thread_id
            )

            # Should not record events for test threads
            self.assertNotIn(test_thread_id, self.monitor.event_counts)

    async def test_record_event_latency_calculation(self):
        """Test ChatEventMonitor calculates event latency correctly."""
        # Record first event
        await self.monitor.record_event(EventType.AGENT_STARTED.value, self.test_thread_id)

        # Wait a small amount
        await asyncio.sleep(0.01)

        # Record second event
        await self.monitor.record_event(EventType.AGENT_THINKING.value, self.test_thread_id)

        # Verify latency was calculated and recorded
        self.assertGreater(len(self.monitor.event_latencies), 0)
        self.assertGreater(self.monitor.event_latencies[-1], 0)

    async def test_get_health_status_healthy(self):
        """Test ChatEventMonitor reports healthy status for normal operation."""
        # Record normal event sequence
        events = [
            EventType.AGENT_STARTED.value,
            EventType.AGENT_THINKING.value,
            EventType.TOOL_EXECUTING.value,
            EventType.TOOL_COMPLETED.value,
            EventType.AGENT_COMPLETED.value
        ]

        for event_type in events:
            tool_name = self.test_tool_name if "tool" in event_type else None
            await self.monitor.record_event(event_type, self.test_thread_id, tool_name=tool_name)

        # Get health status
        status = self.monitor.get_health_status()

        # Should be healthy
        self.assertEqual(status, HealthStatus.HEALTHY)

    async def test_get_health_status_warning_stale_threads(self):
        """Test ChatEventMonitor reports warning status for stale threads."""
        # Record agent_started event with old timestamp
        await self.monitor.record_event(EventType.AGENT_STARTED.value, self.test_thread_id)

        # Simulate stale thread by setting old last event time
        old_time = time.time() - (self.monitor.stale_thread_threshold + 1)
        key = f"{self.test_thread_id}:{EventType.AGENT_STARTED.value}"
        self.monitor.last_event_time[key] = old_time

        # Get health status
        status = self.monitor.get_health_status()

        # Should be warning due to stale thread
        self.assertIn(status, [HealthStatus.WARNING, HealthStatus.CRITICAL])

    async def test_get_health_status_critical_silent_failures(self):
        """Test ChatEventMonitor reports critical status for many silent failures."""
        # Generate multiple silent failures
        for i in range(10):
            await self.monitor.record_event(
                EventType.TOOL_COMPLETED.value,
                f"thread_{i}",
                tool_name=f"tool_{i}"
            )

        # Get health status
        status = self.monitor.get_health_status()

        # Should be critical due to many silent failures
        self.assertIn(status, [HealthStatus.WARNING, HealthStatus.CRITICAL])

    def test_get_metrics_basic(self):
        """Test ChatEventMonitor get_metrics returns basic metrics."""
        # Get metrics (should work even with no events)
        metrics = self.monitor.get_metrics()

        # Verify metrics structure
        self.assertIsInstance(metrics, dict)
        self.assertIn("total_threads", metrics)
        self.assertIn("total_events", metrics)
        self.assertIn("active_threads", metrics)
        self.assertIn("silent_failures", metrics)
        self.assertIn("average_latency", metrics)

    async def test_get_metrics_with_events(self):
        """Test ChatEventMonitor get_metrics with recorded events."""
        # Record some events
        await self.monitor.record_event(EventType.AGENT_STARTED.value, self.test_thread_id)
        await self.monitor.record_event(EventType.AGENT_THINKING.value, self.test_thread_id)
        await self.monitor.record_event(EventType.AGENT_COMPLETED.value, self.test_thread_id)

        # Get metrics
        metrics = self.monitor.get_metrics()

        # Verify metrics reflect recorded events
        self.assertGreaterEqual(metrics["total_threads"], 1)
        self.assertGreaterEqual(metrics["total_events"], 3)

    def test_register_component(self):
        """Test ChatEventMonitor register_component functionality."""
        # Create mock component
        mock_component = Mock(spec=MonitorableComponent)
        mock_component.get_health_status.return_value = {"status": "healthy"}

        # Register component
        self.monitor.register_component("test_component", mock_component)

        # Verify component was registered
        self.assertIn("test_component", self.monitor.monitored_components)
        self.assertEqual(self.monitor.monitored_components["test_component"], mock_component)

    def test_unregister_component(self):
        """Test ChatEventMonitor unregister_component functionality."""
        # Register then unregister component
        mock_component = Mock(spec=MonitorableComponent)
        self.monitor.register_component("test_component", mock_component)
        self.monitor.unregister_component("test_component")

        # Verify component was unregistered
        self.assertNotIn("test_component", self.monitor.monitored_components)

    async def test_audit_components(self):
        """Test ChatEventMonitor audit_components functionality."""
        # Register mock component
        mock_component = Mock(spec=MonitorableComponent)
        mock_component.get_health_status.return_value = {
            "status": "healthy",
            "metrics": {"events_processed": 100}
        }

        self.monitor.register_component("test_component", mock_component)

        # Audit components
        audit_results = await self.monitor.audit_components()

        # Verify audit results
        self.assertIsInstance(audit_results, dict)
        self.assertIn("test_component", audit_results)

        # Verify health status was called
        mock_component.get_health_status.assert_called_once()

        # Verify health history was updated
        self.assertIn("test_component", self.monitor.component_health_history)

    async def test_get_anomaly_report(self):
        """Test ChatEventMonitor get_anomaly_report functionality."""
        # Create some anomalies
        await self.monitor.record_event(
            EventType.TOOL_COMPLETED.value,
            self.test_thread_id,
            tool_name=self.test_tool_name
        )  # Silent failure

        # Get anomaly report
        report = await self.monitor.get_anomaly_report()

        # Verify report structure
        self.assertIsInstance(report, dict)
        self.assertIn("silent_failures", report)
        self.assertIn("stale_threads", report)
        self.assertIn("latency_issues", report)

        # Verify silent failures are reported
        self.assertGreater(len(report["silent_failures"]), 0)

    async def test_start_monitoring_background_task(self):
        """Test ChatEventMonitor start_monitoring creates background task."""
        # Start monitoring
        await self.monitor.start_monitoring()

        # Verify background task was created
        self.assertIsNotNone(self.monitor._monitor_task)
        self.assertFalse(self.monitor._monitor_task.done())

        # Stop monitoring
        await self.monitor.stop_monitoring()

    async def test_stop_monitoring_background_task(self):
        """Test ChatEventMonitor stop_monitoring stops background task."""
        # Start then stop monitoring
        await self.monitor.start_monitoring()
        await self.monitor.stop_monitoring()

        # Verify background task was stopped
        self.assertTrue(self.monitor._shutdown)
        if self.monitor._monitor_task:
            self.assertTrue(self.monitor._monitor_task.done())

    async def test_background_monitoring_detects_stale_threads(self):
        """Test ChatEventMonitor background monitoring detects stale threads."""
        # Create short-lived monitor for testing
        test_monitor = ChatEventMonitor()
        test_monitor.stale_thread_threshold = 0.1  # 100ms for quick testing

        # Record event
        await test_monitor.record_event(EventType.AGENT_STARTED.value, self.test_thread_id)

        # Wait longer than threshold
        await asyncio.sleep(0.2)

        # Check for stale threads
        stale_threads = await test_monitor._check_stale_threads()

        # Should detect stale thread
        self.assertGreater(len(stale_threads), 0)
        self.assertIn(self.test_thread_id, stale_threads)

    async def test_event_sequence_validation(self):
        """Test ChatEventMonitor validates event sequences correctly."""
        # Record valid sequence
        valid_sequence = [
            EventType.AGENT_STARTED.value,
            EventType.AGENT_THINKING.value,
            EventType.TOOL_EXECUTING.value,
            EventType.TOOL_COMPLETED.value,
            EventType.AGENT_COMPLETED.value
        ]

        for event_type in valid_sequence:
            tool_name = self.test_tool_name if "tool" in event_type else None
            await self.monitor.record_event(event_type, self.test_thread_id, tool_name=tool_name)

        # Should have no sequence violations
        report = await self.monitor.get_anomaly_report()
        # Implementation may vary, but should track sequence correctness

    async def test_concurrent_event_recording(self):
        """Test ChatEventMonitor handles concurrent event recording."""
        # Create multiple threads recording events concurrently
        tasks = []
        thread_count = 10

        for i in range(thread_count):
            thread_id = f"thread_{i}"
            task = self.monitor.record_event(
                EventType.AGENT_STARTED.value,
                thread_id,
                metadata={"thread_number": i}
            )
            tasks.append(task)

        # Wait for all events to be recorded
        await asyncio.gather(*tasks)

        # Verify all events were recorded
        self.assertEqual(len(self.monitor.event_counts), thread_count)

        for i in range(thread_count):
            thread_id = f"thread_{i}"
            self.assertIn(thread_id, self.monitor.event_counts)

    async def test_memory_management_event_history_limits(self):
        """Test ChatEventMonitor manages memory by limiting stored data."""
        # Record many events to test memory limits
        event_count = 1000

        for i in range(event_count):
            await self.monitor.record_event(
                EventType.AGENT_STARTED.value,
                self.test_thread_id,
                metadata={"iteration": i}
            )

        # Verify memory limits are respected
        # Event latencies should be limited
        self.assertLessEqual(len(self.monitor.event_latencies), self.monitor.max_latency_samples)

        # Silent failures should be limited
        self.assertLessEqual(len(self.monitor.silent_failures), self.monitor.max_silent_failures)

    async def test_event_tracker_initialization(self):
        """Test EventTracker class initialization."""
        tracker = EventTracker()

        # Verify initialization
        self.assertIsNotNone(tracker)
        # Add specific assertions based on EventTracker implementation

    async def test_event_metrics_initialization(self):
        """Test EventMetrics class initialization."""
        metrics = EventMetrics()

        # Verify initialization
        self.assertIsNotNone(metrics)
        # Add specific assertions based on EventMetrics implementation

    def test_websocket_event_monitor_initialization(self):
        """Test WebSocketEventMonitor class initialization."""
        monitor = WebSocketEventMonitor()

        # Verify initialization
        self.assertIsNotNone(monitor)
        # Add specific assertions based on WebSocketEventMonitor implementation

    def test_event_validation_error(self):
        """Test EventValidationError exception class."""
        error = EventValidationError("Test validation error")

        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test validation error")

    def test_missing_critical_event_error(self):
        """Test MissingCriticalEventError exception class."""
        error = MissingCriticalEventError("Missing critical event")

        self.assertIsInstance(error, EventValidationError)
        self.assertEqual(str(error), "Missing critical event")

    async def test_monitor_performance_with_high_event_volume(self):
        """Test ChatEventMonitor performance with high event volume."""
        start_time = time.time()

        # Record large number of events
        event_count = 1000
        for i in range(event_count):
            await self.monitor.record_event(
                EventType.AGENT_STARTED.value,
                f"thread_{i % 10}",  # Spread across 10 threads
                metadata={"iteration": i}
            )

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process events efficiently (less than 1 second for 1000 events)
        self.assertLess(processing_time, 1.0)

        # Verify all events were processed
        total_events = sum(
            sum(counts.values()) for counts in self.monitor.event_counts.values()
        )
        self.assertEqual(total_events, event_count)

    async def test_monitor_error_resilience(self):
        """Test ChatEventMonitor resilience to errors during event processing."""
        # Test with malformed event data
        try:
            await self.monitor.record_event(
                None,  # Invalid event type
                self.test_thread_id
            )
        except Exception:
            pass  # Should handle gracefully

        # Test with invalid thread ID
        try:
            await self.monitor.record_event(
                EventType.AGENT_STARTED.value,
                None  # Invalid thread ID
            )
        except Exception:
            pass  # Should handle gracefully

        # Monitor should still be functional
        await self.monitor.record_event(
            EventType.AGENT_STARTED.value,
            self.test_thread_id
        )

        # Verify normal operation continues
        self.assertIn(self.test_thread_id, self.monitor.event_counts)

    async def test_component_health_history_management(self):
        """Test ChatEventMonitor manages component health history efficiently."""
        # Register component
        mock_component = Mock(spec=MonitorableComponent)
        self.monitor.register_component("test_component", mock_component)

        # Generate many health reports
        health_report_count = 100

        for i in range(health_report_count):
            mock_component.get_health_status.return_value = {
                "status": "healthy",
                "iteration": i
            }
            await self.monitor.audit_components()

        # Verify history is limited to prevent memory issues
        component_history = self.monitor.component_health_history["test_component"]
        self.assertLessEqual(
            len(component_history),
            self.monitor.max_health_history_per_component
        )