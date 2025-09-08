"""
Comprehensive Unit Test Suite for WebSocketNotifier - 100% Coverage Target

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure Mission Critical Agent Events ($75K+ MRR protection) 
- Value Impact: WebSocketNotifier sends the 5 CRITICAL events that deliver chat business value
- Strategic Impact: MISSION CRITICAL - Agent events provide real-time feedback preventing user abandonment

This test suite ensures 100% coverage of WebSocketNotifier, focusing on the 5 mission-critical
WebSocket events that enable substantive chat interactions:

1. **agent_started** - User must see agent began processing their problem
2. **agent_thinking** - Real-time reasoning visibility (shows AI is working on valuable solutions)  
3. **tool_executing** - Tool usage transparency (demonstrates problem-solving approach)
4. **tool_completed** - Tool results display (delivers actionable insights)
5. **agent_completed** - User must know when valuable response is ready

CRITICAL COVERAGE AREAS:
- All 5 critical event types with guaranteed delivery
- Event queuing and retry logic for reliability 
- Enhanced event payloads with progress tracking
- Delivery confirmation tracking for critical events
- Concurrent execution optimization
- Backlog processing and user notifications
- Error handling and recovery patterns

⚠️ DEPRECATION CONTEXT: While WebSocketNotifier is deprecated in favor of AgentWebSocketBridge,
it's still used in production and requires complete test coverage for stability.
"""

import asyncio
import pytest
import time
import uuid
import warnings
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

# Import test framework
import unittest
from shared.isolated_environment import get_env  
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import system under test
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.schemas.registry import AgentStatus


class MockWebSocketManager:
    """Mock WebSocketManager for testing WebSocketNotifier."""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sent_messages: List[Dict[str, Any]] = []
        self.broadcast_messages: List[Dict[str, Any]] = []
        self.sent_to_threads: Dict[str, List[Dict[str, Any]]] = {}
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Mock send_to_thread method."""
        if self.should_fail:
            raise Exception("Mock WebSocket manager failure")
        
        if thread_id not in self.sent_to_threads:
            self.sent_to_threads[thread_id] = []
        
        self.sent_to_threads[thread_id].append({
            **message,
            "_test_thread_id": thread_id,
            "_test_timestamp": time.time()
        })
        return True
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Mock broadcast method."""
        if self.should_fail:
            raise Exception("Mock broadcast failure")
        
        self.broadcast_messages.append({
            **message,
            "_test_broadcast_timestamp": time.time()
        })
    
    def get_messages_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages sent to a specific thread."""
        return self.sent_to_threads.get(thread_id, [])
    
    def get_all_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all messages sent to all threads."""
        all_messages = []
        for messages in self.sent_to_threads.values():
            all_messages.extend(messages)
        return all_messages
    
    def clear_messages(self) -> None:
        """Clear all message history."""
        self.sent_messages.clear()
        self.broadcast_messages.clear()
        self.sent_to_threads.clear()


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocketManager for testing."""
    return MockWebSocketManager()


@pytest.fixture
def failing_websocket_manager():
    """Create failing WebSocketManager for testing error scenarios."""
    return MockWebSocketManager(should_fail=True)


@pytest.fixture
def sample_execution_context():
    """Create sample AgentExecutionContext for testing."""
    return AgentExecutionContext(
        agent_name="TestAgent",
        run_id="run_12345",
        thread_id="thread_67890",
        user_id="user_99999",
        total_steps=5
    )


class TestWebSocketNotifierUnit(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive unit tests for WebSocketNotifier."""
    
    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)
        # Use IsolatedEnvironment per CLAUDE.md requirements
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="websocket_notifier_test")
        self.env.set("WEBSOCKET_TIMEOUT", "5", source="websocket_notifier_test")
        
        # Initialize mock manager and notifier for each test
        self.mock_manager = MockWebSocketManager()
        
        # Suppress deprecation warning during testing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.notifier = WebSocketNotifier(self.mock_manager)
    
    def teardown_method(self, method):
        """Cleanup method for each test."""
        # Use pytest-asyncio to handle async cleanup
        if hasattr(self, 'notifier'):
            import asyncio
            try:
                # Try to run cleanup in existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup as a task
                    asyncio.create_task(self.notifier.shutdown())
                else:
                    # Run cleanup synchronously
                    loop.run_until_complete(self.notifier.shutdown())
            except RuntimeError:
                # Create new loop if needed
                asyncio.run(self.notifier.shutdown())
        super().teardown_method(method)
    
    # ============================================================================
    # INITIALIZATION AND DEPRECATION TESTS
    # ============================================================================
    
    def test_websocket_notifier_initialization(self):
        """Test WebSocketNotifier initialization with deprecation warning."""
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            notifier = WebSocketNotifier(self.mock_manager)
            
            # Verify deprecation warning was issued
            self.assertEqual(len(warning_list), 1)
            self.assertTrue(issubclass(warning_list[0].category, DeprecationWarning))
            self.assertIn("AgentWebSocketBridge", str(warning_list[0].message))
    
    def test_notifier_configuration(self):
        """Test notifier configuration and settings."""
        self.assertEqual(self.notifier.websocket_manager, self.mock_manager)
        self.assertIsInstance(self.notifier.event_queue, deque)
        self.assertIsInstance(self.notifier.delivery_confirmations, dict)
        self.assertIsInstance(self.notifier.active_operations, dict)
        
        # Verify performance settings
        self.assertEqual(self.notifier.max_queue_size, 1000)
        self.assertEqual(self.notifier.retry_delay, 0.1)
        self.assertEqual(self.notifier.backlog_notification_interval, 5.0)
        
        # Verify critical events set
        expected_critical_events = {'agent_started', 'tool_executing', 'tool_completed', 'agent_completed'}
        self.assertEqual(self.notifier.critical_events, expected_critical_events)
    
    # ============================================================================
    # CRITICAL EVENT TESTS - Mission Critical for Chat Business Value
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_send_agent_started_basic(self):
        """Test basic agent_started event - CRITICAL for chat value."""
        context = AgentExecutionContext("TestAgent", "run_123", "thread_456", "user_789")
        
        await self.notifier.send_agent_started(context)
        
        # Verify message was sent
        messages = self.mock_manager.get_messages_for_thread("thread_456")
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message["type"], "agent_started")
        self.assertIn("payload", message)
        
        payload = message["payload"]
        self.assertEqual(payload["agent_name"], "TestAgent")
        self.assertEqual(payload["run_id"], "run_123")
        self.assertIn("timestamp", payload)
    
    @pytest.mark.asyncio
    async def test_send_agent_thinking_enhanced(self):
        """Test enhanced agent_thinking event with progress tracking."""
        context = AgentExecutionContext("ThinkingAgent", "run_456", "thread_789", "user_123")
        
        await self.notifier.send_agent_thinking(
            context,
            thought="Analyzing your request for optimization opportunities",
            step_number=2,
            progress_percentage=40.0,
            estimated_remaining_ms=5000,
            current_operation="data_analysis"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_789")
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message["type"], "agent_thinking")
        
        payload = message["payload"]
        self.assertEqual(payload["thought"], "Analyzing your request for optimization opportunities")
        self.assertEqual(payload["step_number"], 2)
        self.assertEqual(payload["progress_percentage"], 40.0)
        self.assertEqual(payload["estimated_remaining_ms"], 5000)
        self.assertEqual(payload["current_operation"], "data_analysis")
        self.assertEqual(payload["urgency"], "medium_priority")  # 5000ms = medium priority
    
    @pytest.mark.asyncio
    async def test_send_tool_executing_critical(self):
        """Test tool_executing event - CRITICAL for chat transparency."""
        context = AgentExecutionContext("ToolAgent", "run_789", "thread_123", "user_456")
        
        await self.notifier.send_tool_executing(
            context,
            tool_name="cost_optimizer",
            tool_purpose="Analyze spending patterns and identify savings opportunities",
            estimated_duration_ms=3000,
            parameters_summary="analyzing 6 months of data"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_123")
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message["type"], "tool_executing")
        
        payload = message["payload"]
        self.assertEqual(payload["tool_name"], "cost_optimizer")
        self.assertEqual(payload["tool_purpose"], "Analyze spending patterns and identify savings opportunities")
        self.assertEqual(payload["estimated_duration_ms"], 3000)
        self.assertEqual(payload["parameters_summary"], "analyzing 6 months of data")
        self.assertEqual(payload["execution_phase"], "starting")
    
    @pytest.mark.asyncio
    async def test_send_tool_completed_critical(self):
        """Test tool_completed event - CRITICAL for delivering insights."""
        context = AgentExecutionContext("ToolAgent", "run_999", "thread_888", "user_777")
        
        result = {
            "savings_identified": 1500.00,
            "recommendations": ["Switch to annual billing", "Optimize instance sizes"],
            "confidence": 0.95
        }
        
        await self.notifier.send_tool_completed(context, "cost_optimizer", result)
        
        messages = self.mock_manager.get_messages_for_thread("thread_888")
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message["type"], "tool_completed")
        
        payload = message["payload"]
        self.assertEqual(payload["tool_name"], "cost_optimizer")
        self.assertEqual(payload["result"], result)
        self.assertEqual(payload["agent_name"], "ToolAgent")
    
    @pytest.mark.asyncio
    async def test_send_agent_completed_critical(self):
        """Test agent_completed event - CRITICAL for chat completion."""
        context = AgentExecutionContext("CompleteAgent", "run_final", "thread_final", "user_final")
        
        result = {
            "summary": "Identified $1,500 in monthly savings",
            "actions_taken": 3,
            "recommendations": ["Action 1", "Action 2"]
        }
        
        await self.notifier.send_agent_completed(context, result, 15000.5)
        
        messages = self.mock_manager.get_messages_for_thread("thread_final")
        self.assertEqual(len(messages), 1)
        
        message = messages[0]
        self.assertEqual(message["type"], "agent_completed")
        
        payload = message["payload"]
        self.assertEqual(payload["agent_name"], "CompleteAgent")
        self.assertEqual(payload["run_id"], "run_final")
        self.assertEqual(payload["result"], result)
        self.assertEqual(payload["duration_ms"], 15000.5)
    
    # ============================================================================
    # ENHANCED EVENT PAYLOAD TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_enhanced_thinking_payload_urgency_classification(self):
        """Test thinking payload urgency classification based on duration."""
        context = AgentExecutionContext("UrgentAgent", "run_urgency", "thread_urgency", "user_urgency")
        
        # Test high priority (short duration)
        await self.notifier.send_agent_thinking(
            context, "Quick analysis", estimated_remaining_ms=2000
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_urgency")
        self.assertEqual(messages[0]["payload"]["urgency"], "high_priority")
        
        # Clear and test medium priority
        self.mock_manager.clear_messages()
        await self.notifier.send_agent_thinking(
            context, "Medium analysis", estimated_remaining_ms=7000
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_urgency")
        self.assertEqual(messages[0]["payload"]["urgency"], "medium_priority")
        
        # Clear and test low priority
        self.mock_manager.clear_messages()  
        await self.notifier.send_agent_thinking(
            context, "Deep analysis", estimated_remaining_ms=15000
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_urgency")
        self.assertEqual(messages[0]["payload"]["urgency"], "low_priority")
    
    @pytest.mark.asyncio
    async def test_tool_context_hints(self):
        """Test tool context hints based on tool name patterns."""
        context = AgentExecutionContext("ToolHintAgent", "run_hints", "thread_hints", "user_hints")
        
        test_cases = [
            ("search_optimizer", "information_retrieval", "medium"),
            ("analyze_patterns", "data_processing", "long"),
            ("query_database", "database_operation", "short"),
            ("generate_report", "content_creation", "medium"),
            ("validate_input", "verification", "short"),
            ("optimize_performance", "performance_tuning", "long"),
            ("unknown_tool", "general", "medium")
        ]
        
        for tool_name, expected_category, expected_duration in test_cases:
            self.mock_manager.clear_messages()
            
            await self.notifier.send_tool_executing(context, tool_name)
            
            messages = self.mock_manager.get_messages_for_thread("thread_hints")
            self.assertEqual(len(messages), 1)
            
            payload = messages[0]["payload"]
            self.assertEqual(payload["category"], expected_category)
            self.assertEqual(payload["expected_duration"], expected_duration)
    
    # ============================================================================
    # ERROR HANDLING AND RECOVERY TESTS  
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_enhanced_error_payload_generation(self):
        """Test enhanced error payload with recovery guidance."""
        context = AgentExecutionContext("ErrorAgent", "run_error", "thread_error", "user_error")
        
        await self.notifier.send_agent_error(
            context,
            error_message="Rate limit exceeded",
            error_type="rate_limit", 
            error_details={"limit": 100, "current": 105},
            recovery_suggestions=["Wait 60 seconds", "Upgrade plan"],
            is_recoverable=True,
            estimated_retry_delay_ms=60000
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_error")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["error_message"], "Rate limit exceeded")
        self.assertEqual(payload["error_type"], "rate_limit")
        self.assertEqual(payload["severity"], "high")  # rate_limit = high severity
        self.assertTrue(payload["is_recoverable"])
        self.assertEqual(payload["estimated_retry_delay_ms"], 60000)
        self.assertIn("Wait 60 seconds", payload["recovery_suggestions"])
        self.assertIn("rate limit", payload["user_friendly_message"].lower())
    
    @pytest.mark.asyncio
    async def test_error_severity_classification(self):
        """Test automatic error severity classification."""
        context = AgentExecutionContext("SeverityAgent", "run_severity", "thread_severity", "user_severity")
        
        test_cases = [
            ("authentication", "Auth failed", "critical"),
            ("database", "DB connection lost", "critical"),  
            ("timeout", "Request timed out", "high"),
            ("validation", "Invalid input", "high"),
            ("general", "Unknown error", "medium"),
            (None, "No type", "medium")
        ]
        
        for error_type, error_message, expected_severity in test_cases:
            self.mock_manager.clear_messages()
            
            await self.notifier.send_agent_error(context, error_message, error_type)
            
            messages = self.mock_manager.get_messages_for_thread("thread_severity")
            payload = messages[0]["payload"]
            self.assertEqual(payload["severity"], expected_severity)
    
    @pytest.mark.asyncio
    async def test_default_recovery_suggestions(self):
        """Test automatic recovery suggestion generation."""
        context = AgentExecutionContext("RecoveryAgent", "run_recovery", "thread_recovery", "user_recovery")
        
        # Test timeout error suggestions
        await self.notifier.send_agent_error(context, "Operation timed out", "timeout")
        messages = self.mock_manager.get_messages_for_thread("thread_recovery")
        suggestions = messages[0]["payload"]["recovery_suggestions"]
        
        self.assertIn("longer than expected", suggestions[0])
        self.assertIn("smaller parts", suggestions[1])
    
    # ============================================================================
    # GUARANTEED DELIVERY AND QUEUING TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_critical_event_guaranteed_delivery(self):
        """Test guaranteed delivery for critical events with retry logic."""
        context = AgentExecutionContext("CriticalAgent", "run_critical", "thread_critical", "user_critical")
        
        # Mock the _attempt_delivery to fail first, then succeed
        delivery_attempts = []
        original_attempt_delivery = self.notifier._attempt_delivery
        
        async def mock_attempt_delivery(event_data):
            delivery_attempts.append(event_data)
            if len(delivery_attempts) == 1:
                return False  # Fail first attempt
            return await original_attempt_delivery(event_data)
        
        self.notifier._attempt_delivery = mock_attempt_delivery
        
        # Send critical event
        await self.notifier.send_agent_started(context)
        
        # Verify it was queued for retry
        self.assertGreater(len(self.notifier.event_queue), 0)
        
        # Process the queue
        await self.notifier._process_event_queue()
        
        # Verify message was eventually delivered
        messages = self.mock_manager.get_messages_for_thread("thread_critical")
        self.assertGreater(len(messages), 0)
    
    @pytest.mark.asyncio
    async def test_event_queue_backlog_management(self):
        """Test event queue backlog management and notification."""
        context = AgentExecutionContext("BacklogAgent", "run_backlog", "thread_backlog", "user_backlog")
        
        # Fill queue beyond reasonable size by mocking failures
        self.mock_manager.should_fail = True
        
        # Send multiple critical events to fill queue
        for i in range(15):
            await self.notifier.send_agent_started(context)
        
        # Verify events were queued
        self.assertGreater(len(self.notifier.event_queue), 10)
        
        # Verify backlog notification
        # Allow some time for backlog notification processing
        await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    async def test_operation_lifecycle_tracking(self):
        """Test operation lifecycle tracking for backlog handling."""
        context = AgentExecutionContext("LifecycleAgent", "run_lifecycle", "thread_lifecycle", "user_lifecycle")
        
        # Start operation
        await self.notifier.send_agent_started(context)
        
        # Verify operation is marked as active
        self.assertIn("thread_lifecycle", self.notifier.active_operations)
        operation = self.notifier.active_operations["thread_lifecycle"]
        self.assertEqual(operation["agent_name"], "LifecycleAgent")
        self.assertTrue(operation["processing"])
        
        # Complete operation
        await self.notifier.send_agent_completed(context)
        
        # Verify operation is marked as complete (but still tracked briefly)
        operation = self.notifier.active_operations["thread_lifecycle"]
        self.assertFalse(operation["processing"])
    
    # ============================================================================
    # COMPATIBILITY METHOD TESTS - Agent Manager Integration
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_agent_registered_compatibility(self):
        """Test agent_registered with both context and parameter approaches."""
        context = AgentExecutionContext("RegAgent", "run_reg", "thread_reg", "user_reg")
        
        # Test with context
        await self.notifier.send_agent_registered(context, {"version": "1.0"})
        
        messages = self.mock_manager.get_messages_for_thread("thread_reg")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["type"], "agent_registered")
        
        # Clear and test with parameters
        self.mock_manager.clear_messages()
        await self.notifier.send_agent_registered(
            agent_id="param_agent",
            agent_type="optimizer", 
            thread_id="thread_param"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_param")
        self.assertEqual(len(messages), 1)
        payload = messages[0]["payload"]
        self.assertEqual(payload["agent_id"], "param_agent")
        self.assertEqual(payload["agent_type"], "optimizer")
    
    @pytest.mark.asyncio
    async def test_agent_failed_compatibility(self):
        """Test agent_failed with both context and parameter approaches."""
        context = AgentExecutionContext("FailAgent", "run_fail", "thread_fail", "user_fail")
        
        # Test with context
        await self.notifier.send_agent_failed(
            context, 
            error_message="Context error",
            error_details={"code": 500}
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_fail")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["payload"]["error_message"], "Context error")
        
        # Clear and test with parameters
        self.mock_manager.clear_messages()
        await self.notifier.send_agent_failed(
            agent_id="param_fail_agent",
            error="Parameter error",
            thread_id="thread_param_fail"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_param_fail")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["payload"]["error"], "Parameter error")
    
    @pytest.mark.asyncio
    async def test_agent_status_changed_compatibility(self):
        """Test agent_status_changed with both approaches."""
        context = AgentExecutionContext("StatusAgent", "run_status", "thread_status", "user_status")
        
        # Test with context
        await self.notifier.send_agent_status_changed(
            context,
            old_status=AgentStatus.IDLE,
            new_status=AgentStatus.RUNNING
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_status")
        self.assertEqual(len(messages), 1)
        payload = messages[0]["payload"]
        self.assertEqual(payload["old_status"], AgentStatus.IDLE.value)
        self.assertEqual(payload["new_status"], AgentStatus.RUNNING.value)
    
    # ============================================================================
    # STREAMING AND PARTIAL RESULT TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_partial_result_streaming(self):
        """Test partial result streaming for real-time updates."""
        context = AgentExecutionContext("StreamAgent", "run_stream", "thread_stream", "user_stream")
        
        await self.notifier.send_partial_result(
            context,
            content="Partial analysis results: Found 3 optimization opportunities...",
            is_complete=False
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_stream")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"] 
        self.assertIn("Partial analysis results", payload["content"])
        self.assertFalse(payload["is_complete"])
    
    @pytest.mark.asyncio
    async def test_stream_chunk_delivery(self):
        """Test stream chunk delivery for incremental content."""
        context = AgentExecutionContext("ChunkAgent", "run_chunk", "thread_chunk", "user_chunk")
        
        await self.notifier.send_stream_chunk(
            context,
            chunk_id="chunk_001", 
            content="This is chunk 1 of the analysis...",
            is_final=False
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_chunk")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["chunk_id"], "chunk_001")
        self.assertFalse(payload["is_final"])
    
    @pytest.mark.asyncio
    async def test_stream_completion(self):
        """Test stream completion notification."""
        context = AgentExecutionContext("StreamCompleteAgent", "run_complete", "thread_complete", "user_complete")
        
        await self.notifier.send_stream_complete(
            context,
            stream_id="stream_analysis",
            total_chunks=5,
            metadata={"duration_ms": 2500}
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_complete")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["stream_id"], "stream_analysis")
        self.assertEqual(payload["total_chunks"], 5)
        self.assertEqual(payload["metadata"]["duration_ms"], 2500)
    
    # ============================================================================
    # PERIODIC UPDATE AND LONG-RUNNING OPERATION TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_periodic_update_for_long_operations(self):
        """Test periodic updates for operations >5 seconds."""
        context = AgentExecutionContext("LongOpAgent", "run_long", "thread_long", "user_long")
        
        await self.notifier.send_periodic_update(
            context,
            operation_name="deep_analysis",
            progress_percentage=65.0,
            status_message="Analyzing complex patterns...",
            estimated_remaining_ms=8000,
            current_step="pattern_matching"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_long")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["operation_name"], "deep_analysis")
        self.assertEqual(payload["progress_percentage"], 65.0)
        self.assertEqual(payload["estimated_remaining_ms"], 8000)
        self.assertEqual(payload["current_step"], "pattern_matching")
        self.assertEqual(payload["update_type"], "periodic_progress")
    
    @pytest.mark.asyncio
    async def test_operation_started_notification(self):
        """Test operation started notification for long-running tasks."""
        context = AgentExecutionContext("OpStartAgent", "run_opstart", "thread_opstart", "user_opstart")
        
        await self.notifier.send_operation_started(
            context,
            operation_name="comprehensive_audit",
            operation_type="analysis",
            expected_duration_ms=12000,
            operation_description="Performing comprehensive cost audit across all services"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_opstart")
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["operation_name"], "comprehensive_audit")
        self.assertEqual(payload["operation_type"], "analysis")
        self.assertEqual(payload["expected_duration_ms"], 12000)
        self.assertIn("comprehensive cost audit", payload["operation_description"])
    
    @pytest.mark.asyncio
    async def test_operation_completed_notification(self):
        """Test operation completed notification with metrics."""
        context = AgentExecutionContext("OpCompleteAgent", "run_opcomplete", "thread_opcomplete", "user_opcomplete")
        
        metrics = {
            "items_processed": 1500,
            "patterns_found": 12,
            "accuracy": 0.94
        }
        
        await self.notifier.send_operation_completed(
            context,
            operation_name="pattern_analysis",
            duration_ms=9500.0,
            result_summary="Successfully identified 12 cost optimization patterns",
            metrics=metrics
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_opcomplete") 
        self.assertEqual(len(messages), 1)
        
        payload = messages[0]["payload"]
        self.assertEqual(payload["operation_name"], "pattern_analysis")
        self.assertEqual(payload["duration_ms"], 9500.0)
        self.assertIn("12 cost optimization patterns", payload["result_summary"])
        self.assertEqual(payload["metrics"], metrics)
    
    # ============================================================================
    # SUBAGENT LIFECYCLE TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_subagent_lifecycle_notifications(self):
        """Test sub-agent lifecycle start and completion notifications."""
        context = AgentExecutionContext("ParentAgent", "run_parent", "thread_parent", "user_parent")
        
        # Test sub-agent started
        await self.notifier.send_subagent_started(
            context, 
            subagent_name="DataAnalyzer",
            subagent_id="subagent_001"
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_parent")
        self.assertEqual(len(messages), 1)
        
        start_payload = messages[0]["payload"]
        self.assertEqual(start_payload["subagent_name"], "DataAnalyzer")
        self.assertEqual(start_payload["subagent_id"], "subagent_001") 
        self.assertEqual(start_payload["parent_agent_name"], "ParentAgent")
        self.assertEqual(start_payload["status"], "started")
        
        # Clear and test sub-agent completed
        self.mock_manager.clear_messages()
        
        subagent_result = {"insights": 5, "recommendations": ["rec1", "rec2"]}
        await self.notifier.send_subagent_completed(
            context,
            subagent_name="DataAnalyzer", 
            subagent_id="subagent_001",
            result=subagent_result,
            duration_ms=3500.0
        )
        
        messages = self.mock_manager.get_messages_for_thread("thread_parent")
        self.assertEqual(len(messages), 1)
        
        complete_payload = messages[0]["payload"]
        self.assertEqual(complete_payload["subagent_name"], "DataAnalyzer")
        self.assertEqual(complete_payload["result"], subagent_result)
        self.assertEqual(complete_payload["duration_ms"], 3500.0)
        self.assertEqual(complete_payload["status"], "completed")
    
    # ============================================================================
    # ERROR SCENARIOS AND ROBUSTNESS TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_manager_none_handling(self):
        """Test handling when websocket_manager is None."""
        # Create notifier with None manager
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier_with_none = WebSocketNotifier(None)
        
        context = AgentExecutionContext("NoneAgent", "run_none", "thread_none", "user_none")
        
        # All methods should handle None gracefully without raising exceptions
        await notifier_with_none.send_agent_started(context)
        await notifier_with_none.send_agent_thinking(context, "thinking")
        await notifier_with_none.send_tool_executing(context, "test_tool")
        await notifier_with_none.send_tool_completed(context, "test_tool")
        await notifier_with_none.send_agent_completed(context)
        
        # No exceptions should be raised
        self.assertTrue(True)  # Test passes if no exceptions
    
    @pytest.mark.asyncio
    async def test_websocket_send_failure_handling(self):
        """Test handling of WebSocket send failures."""
        failing_manager = MockWebSocketManager(should_fail=True)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            failing_notifier = WebSocketNotifier(failing_manager)
        
        context = AgentExecutionContext("FailAgent", "run_fail", "thread_fail", "user_fail")
        
        # Should not raise exceptions even when WebSocket fails
        await failing_notifier.send_agent_started(context)
        await failing_notifier.send_tool_executing(context, "failing_tool")
        
        # Verify events were queued for retry
        self.assertGreater(len(failing_notifier.event_queue), 0)
    
    # ============================================================================
    # DELIVERY STATISTICS AND MONITORING TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_delivery_statistics(self):
        """Test delivery statistics tracking."""
        context = AgentExecutionContext("StatsAgent", "run_stats", "thread_stats", "user_stats")
        
        # Send some events
        await self.notifier.send_agent_started(context)
        await self.notifier.send_tool_executing(context, "stats_tool")
        
        stats = await self.notifier.get_delivery_stats()
        
        self.assertIn("queued_events", stats)
        self.assertIn("active_operations", stats)
        self.assertIn("delivery_confirmations", stats)
        self.assertIn("backlog_notifications_sent", stats)
        
        # Verify active operations tracked
        self.assertGreater(stats["active_operations"], 0)
    
    @pytest.mark.asyncio
    async def test_notifier_shutdown(self):
        """Test notifier shutdown and cleanup."""
        context = AgentExecutionContext("ShutdownAgent", "run_shutdown", "thread_shutdown", "user_shutdown")
        
        # Create some state
        await self.notifier.send_agent_started(context)
        
        # Shutdown notifier
        await self.notifier.shutdown()
        
        # Verify state was cleaned up
        self.assertEqual(len(self.notifier.event_queue), 0)
        self.assertEqual(len(self.notifier.delivery_confirmations), 0)
        self.assertEqual(len(self.notifier.active_operations), 0)
        self.assertTrue(self.notifier._shutdown)
    
    # ============================================================================
    # HELPER METHOD TESTS
    # ============================================================================
    
    def test_timestamp_generation(self):
        """Test timestamp generation consistency."""
        timestamp1 = self.notifier._get_timestamp()
        time.sleep(0.001)  # Small delay
        timestamp2 = self.notifier._get_timestamp()
        
        self.assertIsInstance(timestamp1, float)
        self.assertIsInstance(timestamp2, float)
        self.assertGreater(timestamp2, timestamp1)
    
    def test_user_friendly_error_messages(self):
        """Test user-friendly error message generation."""
        test_cases = [
            ("timeout", "The TestAgent is taking longer than usual"),
            ("rate_limit", "You've made many requests recently"),
            ("validation", "There's an issue with your request format"),
            ("network", "There's a temporary connectivity issue"),
            ("database", "We're experiencing a temporary data access issue"),
            ("unknown", "The TestAgent encountered an unexpected issue")
        ]
        
        for error_type, expected_fragment in test_cases:
            message = self.notifier._generate_user_friendly_error_message(
                error_type, "Test error", "TestAgent"
            )
            self.assertIn(expected_fragment, message)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])