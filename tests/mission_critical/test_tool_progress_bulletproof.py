#!/usr/bin/env python
"""MISSION CRITICAL: Bulletproof Tool Progress Updates Test Suite

Business Value: $1M+ ARR - Ensures tool execution progress reaches users in real-time
This test suite provides comprehensive validation of tool progress updates including:
- Granular progress tracking for long-running tools
- Concurrent tool execution progress
- Tool failure and recovery scenarios
- Edge cases and performance under extreme load

CRITICAL: Tool progress visibility is essential for user trust during AI operations.
"""

import asyncio
import json
import os
import random
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import enhanced tool execution components
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.tool_dispatcher_execution import ToolExecutionEngine
from netra_backend.app.schemas.tool import ToolInput, ToolResult
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.websocket_core.manager import WebSocketManager


# ============================================================================
# TEST DATA STRUCTURES
# ============================================================================

@dataclass
class ToolProgressEvent:
    """Represents a tool progress event for validation."""
    event_type: str
    tool_name: str
    timestamp: float
    thread_id: str
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    estimated_duration_ms: Optional[int] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionMetrics:
    """Metrics for tool execution performance."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration_ms: float = 0
    event_delivery_latency_ms: List[float] = field(default_factory=list)
    events_per_second: float = 0
    concurrent_peak: int = 0


# ============================================================================
# ENHANCED MOCK CLASSES
# ============================================================================

class AdvancedMockWebSocketManager:
    """Advanced mock WebSocket manager for comprehensive testing."""
    
    def __init__(self, simulate_failures: bool = False, failure_rate: float = 0.0):
        self.messages: List[Dict] = []
        self.tool_events: List[ToolProgressEvent] = []
        self.connections: Dict[str, Any] = {}
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.event_timestamps: List[float] = []
        self.concurrent_executions: Set[str] = set()
        self.max_concurrent = 0
        self.delivery_confirmations: Dict[str, float] = {}
        self.event_queue: List[Dict] = []
        self.backlog_count = 0
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate WebSocket message delivery with optional failures."""
        # Track event timing
        send_time = time.time()
        self.event_timestamps.append(send_time)
        
        # Simulate random failures if enabled
        if self.simulate_failures and random.random() < self.failure_rate:
            self.backlog_count += 1
            self.event_queue.append(message)
            return False
        
        # Record message
        event_data = {
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': send_time
        }
        
        self.messages.append(event_data)
        
        # Process tool-specific events
        if event_data['event_type'] in ['tool_executing', 'tool_completed', 'tool_started']:
            tool_event = self._extract_tool_event(event_data)
            self.tool_events.append(tool_event)
            
            # Track concurrent executions
            if event_data['event_type'] == 'tool_executing':
                self.concurrent_executions.add(tool_event.tool_name)
                self.max_concurrent = max(self.max_concurrent, len(self.concurrent_executions))
            elif event_data['event_type'] == 'tool_completed':
                self.concurrent_executions.discard(tool_event.tool_name)
        
        # Track delivery confirmation
        msg_id = message.get('id', str(uuid.uuid4()))
        self.delivery_confirmations[msg_id] = send_time
        
        # Simulate delivery latency
        await asyncio.sleep(random.uniform(0.001, 0.005))
        
        return True
    
    def _extract_tool_event(self, event_data: Dict) -> ToolProgressEvent:
        """Extract tool progress event from message data."""
        payload = event_data['message'].get('payload', {})
        return ToolProgressEvent(
            event_type=event_data['event_type'],
            tool_name=payload.get('tool_name', 'unknown'),
            timestamp=event_data['timestamp'],
            thread_id=event_data['thread_id'],
            status=payload.get('status'),
            progress_percentage=payload.get('progress_percentage'),
            estimated_duration_ms=payload.get('estimated_duration_ms'),
            error=payload.get('error'),
            result=payload.get('result'),
            metadata=payload
        )
    
    def get_tool_execution_pairs(self, thread_id: str) -> List[Tuple[ToolProgressEvent, ToolProgressEvent]]:
        """Get matched pairs of tool execution events."""
        thread_events = [e for e in self.tool_events if e.thread_id == thread_id]
        pairs = []
        executing_map = {}
        
        for event in thread_events:
            if event.event_type == 'tool_executing':
                executing_map[event.tool_name] = event
            elif event.event_type == 'tool_completed' and event.tool_name in executing_map:
                pairs.append((executing_map[event.tool_name], event))
                del executing_map[event.tool_name]
        
        return pairs
    
    def calculate_metrics(self) -> ToolExecutionMetrics:
        """Calculate comprehensive metrics for tool executions."""
        metrics = ToolExecutionMetrics()
        
        # Count executions
        pairs = self.get_tool_execution_pairs(None)  # Get all pairs
        metrics.total_executions = len(pairs)
        
        for start_event, end_event in pairs:
            duration_ms = (end_event.timestamp - start_event.timestamp) * 1000
            metrics.total_duration_ms += duration_ms
            
            if end_event.status == 'success':
                metrics.successful_executions += 1
            else:
                metrics.failed_executions += 1
        
        # Calculate event delivery rate
        if self.event_timestamps:
            time_span = max(self.event_timestamps) - min(self.event_timestamps)
            if time_span > 0:
                metrics.events_per_second = len(self.event_timestamps) / time_span
        
        # Record peak concurrency
        metrics.concurrent_peak = self.max_concurrent
        
        return metrics
    
    def get_event_sequence_validation(self, thread_id: str) -> Dict[str, bool]:
        """Validate event sequence integrity."""
        thread_events = [e for e in self.tool_events if e.thread_id == thread_id]
        
        validation = {
            'has_start_events': False,
            'has_executing_events': False,
            'has_completed_events': False,
            'proper_sequence': True,
            'no_orphaned_events': True,
            'all_tools_completed': True
        }
        
        tool_states = {}
        
        for event in thread_events:
            tool_name = event.tool_name
            
            if event.event_type == 'tool_started':
                validation['has_start_events'] = True
                if tool_name in tool_states and tool_states[tool_name] != 'completed':
                    validation['proper_sequence'] = False
                tool_states[tool_name] = 'started'
                
            elif event.event_type == 'tool_executing':
                validation['has_executing_events'] = True
                if tool_name not in tool_states or tool_states[tool_name] == 'completed':
                    tool_states[tool_name] = 'executing'
                elif tool_states[tool_name] != 'started':
                    validation['proper_sequence'] = False
                else:
                    tool_states[tool_name] = 'executing'
                    
            elif event.event_type == 'tool_completed':
                validation['has_completed_events'] = True
                if tool_name not in tool_states:
                    validation['no_orphaned_events'] = False
                tool_states[tool_name] = 'completed'
        
        # Check if all tools completed
        for state in tool_states.values():
            if state != 'completed':
                validation['all_tools_completed'] = False
                break
        
        return validation
    
    def clear_all(self):
        """Clear all recorded data."""
        self.messages.clear()
        self.tool_events.clear()
        self.connections.clear()
        self.event_timestamps.clear()
        self.concurrent_executions.clear()
        self.max_concurrent = 0
        self.delivery_confirmations.clear()
        self.event_queue.clear()
        self.backlog_count = 0


class SimulatedLongRunningTool:
    """Simulates a long-running tool with progress updates."""
    
    def __init__(self, name: str, duration_ms: int = 5000, 
                 update_interval_ms: int = 500, should_fail: bool = False):
        self.name = name
        self.duration_ms = duration_ms
        self.update_interval_ms = update_interval_ms
        self.should_fail = should_fail
        self.progress_callback = None
        self.execution_count = 0
    
    async def execute(self, **kwargs) -> Any:
        """Execute tool with progress updates."""
        self.execution_count += 1
        start_time = time.time()
        
        # Calculate number of updates
        num_updates = self.duration_ms // self.update_interval_ms
        
        for i in range(num_updates):
            # Calculate progress
            progress = ((i + 1) / num_updates) * 100
            remaining_ms = self.duration_ms - ((i + 1) * self.update_interval_ms)
            
            # Send progress update if callback available
            if self.progress_callback:
                await self.progress_callback(
                    progress_percentage=progress,
                    estimated_remaining_ms=remaining_ms,
                    current_operation=f"Processing step {i+1}/{num_updates}"
                )
            
            # Simulate work
            await asyncio.sleep(self.update_interval_ms / 1000)
            
            # Simulate failure at midpoint if configured
            if self.should_fail and progress >= 50:
                raise Exception(f"Tool {self.name} failed at {progress:.0f}%")
        
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            'tool': self.name,
            'execution': self.execution_count,
            'duration_ms': elapsed_ms,
            'status': 'completed'
        }


# ============================================================================
# COMPREHENSIVE UNIT TESTS
# ============================================================================

class TestToolProgressGranularity:
    """Test granular tool progress tracking."""
    
    @pytest.fixture(autouse=True)
    def setup_granularity_tests(self):
        """Setup for granularity tests."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        yield
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_contextual_tool_purpose_detection(self):
        """Test that tool purpose is correctly detected from tool names."""
        
        test_cases = [
            ("search_database", "Finding relevant information"),
            ("analyze_metrics", "Performing data analysis"),
            ("generate_report", "Creating content or reports"),
            ("validate_input", "Checking data integrity"),
            ("optimize_query", "Improving performance"),
            ("export_csv", "Exporting results"),
            ("llm_inference", "Processing with AI model"),
            ("calculation_engine", "Computing metrics"),
            ("transform_data", "Converting data format"),
            ("custom_tool", "Executing custom_tool operation")
        ]
        
        for tool_name, expected_purpose in test_cases:
            purpose = self.executor._get_tool_purpose(tool_name, None)
            assert expected_purpose in purpose, \
                f"Tool {tool_name} should have purpose containing '{expected_purpose}', got '{purpose}'"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_duration_estimation(self):
        """Test tool execution duration estimation."""
        
        test_cases = [
            ("search_tool", 3000),
            ("analyze_data", 15000),
            ("generate_content", 8000),
            ("optimize_performance", 30000),
            ("llm_model", 12000),
            ("unknown_tool", 5000)  # Default
        ]
        
        for tool_name, expected_duration in test_cases:
            duration = self.executor._estimate_tool_duration(tool_name, None)
            assert duration == expected_duration, \
                f"Tool {tool_name} should have duration {expected_duration}ms, got {duration}ms"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_parameter_summary_generation(self):
        """Test generation of user-friendly parameter summaries."""
        
        # Test with dict parameters
        params = {
            "query": "SELECT * FROM users WHERE active = true",
            "table_name": "users",
            "limit": 100,
            "filters": [{"field": "status", "value": "active"}]
        }
        
        summary = self.executor._create_parameters_summary(params)
        assert "Query:" in summary
        assert "Table: users" in summary
        assert "Limit: 100" in summary
        assert "Filters: 1 applied" in summary
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_unified_tool_execution_with_context(self):
        """Test enhanced tool execution with contextual information."""
        
        context = AgentExecutionContext(
            run_id="context-test",
            thread_id="context-thread",
            user_id="context-user",
            agent_name="context_agent"
        )
        
        # Create a tool that looks like a search operation
        tool = SimulatedLongRunningTool("search_documents", duration_ms=2000)
        tool_input = ToolInput(tool_name="search_documents", parameters={"query": "test"})
        
        # Mock parent execution
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         return_value=ToolResult(result="search results")):
            
            result = await self.executor.execute_tool_with_input(
                tool_input, tool, {'context': context}
            )
            
            # Verify enhanced events were sent
            events = self.mock_ws.tool_events
            executing_events = [e for e in events if e.event_type == 'tool_executing']
            
            assert len(executing_events) > 0
            event = executing_events[0]
            
            # Check for enhanced metadata
            assert event.metadata.get('tool_purpose') == "Finding relevant information"
            assert event.metadata.get('estimated_duration_ms') == 3000
            assert event.metadata.get('execution_phase') == 'starting'


class TestConcurrentToolProgress:
    """Test concurrent tool execution progress tracking."""
    
    @pytest.fixture(autouse=True)
    def setup_concurrent_tests(self):
        """Setup for concurrent execution tests."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        yield
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_massive_concurrent_tool_execution(self):
        """Test progress tracking with massive concurrent tool executions."""
        
        num_tools = 100
        num_threads = 10
        
        async def execute_tool_batch(thread_id: str, batch_size: int):
            """Execute a batch of tools for a thread."""
            tasks = []
            
            for i in range(batch_size):
                context = AgentExecutionContext(
                    run_id=f"concurrent-{thread_id}-{i}",
                    thread_id=thread_id,
                    user_id=f"user-{thread_id}",
                    agent_name="concurrent_agent"
                )
                
                tool = SimulatedLongRunningTool(
                    f"tool_{thread_id}_{i}",
                    duration_ms=random.randint(10, 100),
                    should_fail=(random.random() < 0.1)  # 10% failure rate
                )
                
                tool_input = ToolInput(
                    tool_name=tool.name,
                    parameters={"batch": thread_id, "index": i}
                )
                
                # Mock parent execution
                async def mock_execute():
                    with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                     return_value=ToolResult(result=f"result_{i}")):
                        try:
                            return await self.executor.execute_tool_with_input(
                                tool_input, tool, {'context': context}
                            )
                        except Exception:
                            return None  # Expected for simulated failures
                
                tasks.append(mock_execute())
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Execute all batches concurrently
        start_time = time.time()
        
        thread_tasks = []
        for thread_num in range(num_threads):
            thread_id = f"thread_{thread_num}"
            tools_per_thread = num_tools // num_threads
            thread_tasks.append(execute_tool_batch(thread_id, tools_per_thread))
        
        all_results = await asyncio.gather(*thread_tasks)
        
        duration = time.time() - start_time
        
        # Calculate metrics
        metrics = self.mock_ws.calculate_metrics()
        
        # Verify high concurrency was achieved
        assert metrics.concurrent_peak >= 5, \
            f"Should achieve high concurrency, got peak of {metrics.concurrent_peak}"
        
        # Verify throughput
        tools_per_second = num_tools / duration
        assert tools_per_second > 20, \
            f"Should process >20 tools/s, got {tools_per_second:.1f}"
        
        # Verify event delivery rate
        assert metrics.events_per_second > 40, \
            f"Should deliver >40 events/s, got {metrics.events_per_second:.1f}"
        
        logger.info(f"Concurrent execution metrics: {metrics.concurrent_peak} peak, "
                   f"{tools_per_second:.1f} tools/s, {metrics.events_per_second:.1f} events/s")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_progress_event_ordering(self):
        """Test that tool progress events maintain proper ordering."""
        
        # Execute multiple tools in sequence
        thread_id = "ordering-test"
        tool_names = ["tool_a", "tool_b", "tool_c"]
        
        for tool_name in tool_names:
            context = AgentExecutionContext(
                run_id=f"order-{tool_name}",
                thread_id=thread_id,
                user_id="order-user",
                agent_name="ordering_agent"
            )
            
            tool = SimulatedLongRunningTool(tool_name, duration_ms=50)
            tool_input = ToolInput(tool_name=tool_name, parameters={})
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result="ordered")):
                await self.executor.execute_tool_with_input(
                    tool_input, tool, {'context': context}
                )
        
        # Validate event sequence
        validation = self.mock_ws.get_event_sequence_validation(thread_id)
        
        assert validation['has_executing_events'], "Should have executing events"
        assert validation['has_completed_events'], "Should have completed events"
        assert validation['proper_sequence'], "Events should be in proper sequence"
        assert validation['no_orphaned_events'], "Should have no orphaned events"
        assert validation['all_tools_completed'], "All tools should complete"
        
        # Verify pairs match
        pairs = self.mock_ws.get_tool_execution_pairs(thread_id)
        assert len(pairs) == len(tool_names), \
            f"Should have {len(tool_names)} execution pairs, got {len(pairs)}"


class TestToolFailureRecovery:
    """Test tool failure scenarios and recovery."""
    
    @pytest.fixture(autouse=True)
    def setup_failure_tests(self):
        """Setup for failure recovery tests."""
        self.mock_ws = AdvancedMockWebSocketManager(
            simulate_failures=True,
            failure_rate=0.2  # 20% failure rate
        )
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        yield
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_tool_failure_with_progress_tracking(self):
        """Test that tool failures still produce proper progress events."""
        
        context = AgentExecutionContext(
            run_id="failure-test",
            thread_id="failure-thread",
            user_id="failure-user",
            agent_name="failure_agent"
        )
        
        # Create a tool that will fail midway
        tool = SimulatedLongRunningTool(
            "failing_tool",
            duration_ms=1000,
            should_fail=True
        )
        
        tool_input = ToolInput(tool_name="failing_tool", parameters={})
        
        # Mock parent to simulate the failure
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         side_effect=Exception("Tool failed at 50%")):
            
            with pytest.raises(Exception, match="Tool failed"):
                await self.executor.execute_tool_with_input(
                    tool_input, tool, {'context': context}
                )
        
        # Verify failure events were sent
        events = self.mock_ws.tool_events
        completed_events = [e for e in events if e.event_type == 'tool_completed']
        
        assert len(completed_events) > 0, "Should have completion event for failed tool"
        
        failure_event = completed_events[0]
        assert failure_event.status == 'error', "Should indicate error status"
        assert failure_event.error is not None, "Should include error information"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_delivery_failures_with_retry(self):
        """Test WebSocket delivery failures and retry mechanisms."""
        
        # Create notifier with the failing WebSocket manager
        notifier = WebSocketNotifier(self.mock_ws)
        
        context = AgentExecutionContext(
            run_id="retry-test",
            thread_id="retry-thread",
            user_id="retry-user",
            agent_name="retry_agent"
        )
        
        # Send multiple events, some will fail
        events_to_send = 20
        
        for i in range(events_to_send):
            await notifier.send_tool_executing(
                context,
                f"tool_{i}",
                tool_purpose="Testing retry",
                estimated_duration_ms=1000
            )
            
            # Small delay to simulate realistic timing
            await asyncio.sleep(0.01)
        
        # Check backlog handling
        assert self.mock_ws.backlog_count > 0, \
            "Should have some events in backlog due to failures"
        
        # Process backlog
        await notifier._process_event_queue()
        
        # Verify delivery stats
        stats = await notifier.get_delivery_stats()
        assert 'queued_events' in stats
        assert 'delivery_confirmations' in stats
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_cascading_tool_failures(self):
        """Test handling of cascading tool failures."""
        
        # Create a chain of tools where failure propagates
        tools = [
            SimulatedLongRunningTool("tool_1", duration_ms=100, should_fail=False),
            SimulatedLongRunningTool("tool_2", duration_ms=100, should_fail=True),
            SimulatedLongRunningTool("tool_3", duration_ms=100, should_fail=False)
        ]
        
        context = AgentExecutionContext(
            run_id="cascade-test",
            thread_id="cascade-thread",
            user_id="cascade-user",
            agent_name="cascade_agent"
        )
        
        results = []
        
        for tool in tools:
            tool_input = ToolInput(tool_name=tool.name, parameters={})
            
            try:
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 side_effect=Exception("Failed") if tool.should_fail else None,
                                 return_value=ToolResult(result="success")):
                    
                    result = await self.executor.execute_tool_with_input(
                        tool_input, tool, {'context': context}
                    )
                    results.append(("success", tool.name))
            except Exception:
                results.append(("failed", tool.name))
                # Continue to next tool despite failure
        
        # Verify all tools attempted and events sent
        assert len(results) == 3, "Should attempt all tools"
        assert results[1][0] == "failed", "Second tool should fail"
        
        # Check event integrity
        events = self.mock_ws.tool_events
        tool_names = {e.tool_name for e in events}
        
        assert "tool_1" in tool_names, "Should have events for tool_1"
        assert "tool_2" in tool_names, "Should have events for tool_2 despite failure"
        assert "tool_3" in tool_names, "Should have events for tool_3 after failure"


class TestEdgeCasesAndStress:
    """Test edge cases and stress scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_edge_tests(self):
        """Setup for edge case tests."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor =(self.mock_ws)
        yield
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_extremely_long_running_tool(self):
        """Test progress tracking for extremely long-running tools."""
        
        context = AgentExecutionContext(
            run_id="long-test",
            thread_id="long-thread",
            user_id="long-user",
            agent_name="long_agent"
        )
        
        # Create a tool that runs for "hours" (simulated)
        tool = SimulatedLongRunningTool(
            "data_migration",
            duration_ms=100,  # Simulate with 100ms but pretend it's hours
            update_interval_ms=10
        )
        
        tool_input = ToolInput(
            tool_name="data_migration",
            parameters={"records": 1000000}
        )
        
        # Set up progress callback to capture updates
        progress_updates = []
        
        async def capture_progress(**kwargs):
            progress_updates.append(kwargs)
        
        tool.progress_callback = capture_progress
        
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         return_value=ToolResult(result="migration complete")):
            
            await self.executor.execute_tool_with_input(
                tool_input, tool, {'context': context}
            )
        
        # Verify multiple progress updates were captured
        assert len(progress_updates) > 5, \
            f"Should have multiple progress updates, got {len(progress_updates)}"
        
        # Verify progress increases monotonically
        percentages = [u.get('progress_percentage', 0) for u in progress_updates]
        assert all(percentages[i] <= percentages[i+1] for i in range(len(percentages)-1)), \
            "Progress should increase monotonically"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_rapid_tool_switching(self):
        """Test rapid switching between different tools."""
        
        context = AgentExecutionContext(
            run_id="switch-test",
            thread_id="switch-thread",
            user_id="switch-user",
            agent_name="switch_agent"
        )
        
        # Rapidly switch between different tool types
        tool_sequence = [
            ("search_tool", 10),
            ("analyze_tool", 20),
            ("search_tool", 10),  # Same tool again
            ("generate_tool", 30),
            ("validate_tool", 10),
            ("search_tool", 10)   # Third time
        ]
        
        start_time = time.time()
        
        for tool_name, duration_ms in tool_sequence:
            tool = SimulatedLongRunningTool(tool_name, duration_ms=duration_ms)
            tool_input = ToolInput(tool_name=tool_name, parameters={})
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result=f"{tool_name}_result")):
                
                await self.executor.execute_tool_with_input(
                    tool_input, tool, {'context': context}
                )
        
        elapsed = time.time() - start_time
        
        # Verify all tools executed and events sent
        events = self.mock_ws.tool_events
        executing_events = [e for e in events if e.event_type == 'tool_executing']
        
        assert len(executing_events) == len(tool_sequence), \
            f"Should have executing event for each tool, got {len(executing_events)}"
        
        # Verify rapid execution
        assert elapsed < 1.0, f"Rapid switching should complete quickly, took {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_memory_intensive_tool_tracking(self):
        """Test progress tracking for memory-intensive operations."""
        
        context = AgentExecutionContext(
            run_id="memory-test",
            thread_id="memory-thread",
            user_id="memory-user",
            agent_name="memory_agent"
        )
        
        # Simulate a tool processing large data
        large_data = {"data": ["x" * 1000 for _ in range(100)]}  # ~100KB of data
        
        tool = SimulatedLongRunningTool("data_processor", duration_ms=50)
        tool_input = ToolInput(
            tool_name="data_processor",
            parameters=large_data
        )
        
        # Track memory usage through events
        initial_event_count = len(self.mock_ws.messages)
        
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         return_value=ToolResult(result="processed")):
            
            await self.executor.execute_tool_with_input(
                tool_input, tool, {'context': context}
            )
        
        # Verify events don't contain full data (should be summarized)
        events = self.mock_ws.tool_events
        executing_events = [e for e in events if e.event_type == 'tool_executing']
        
        if executing_events and 'parameters_summary' in executing_events[0].metadata:
            summary = executing_events[0].metadata['parameters_summary']
            assert len(summary) < 500, \
                "Parameter summary should be concise, not include full data"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_zero_duration_tool(self):
        """Test tools that complete instantly."""
        
        context = AgentExecutionContext(
            run_id="instant-test",
            thread_id="instant-thread",
            user_id="instant-user",
            agent_name="instant_agent"
        )
        
        # Create a tool with zero duration
        tool = SimulatedLongRunningTool("instant_tool", duration_ms=0)
        tool_input = ToolInput(tool_name="instant_tool", parameters={})
        
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         return_value=ToolResult(result="instant")):
            
            result = await self.executor.execute_tool_with_input(
                tool_input, tool, {'context': context}
            )
        
        # Verify events still sent for instant tools
        events = self.mock_ws.tool_events
        assert len(events) >= 2, "Should have events even for instant tools"
        
        # Check timing
        pairs = self.mock_ws.get_tool_execution_pairs(context.thread_id)
        if pairs:
            start_event, end_event = pairs[0]
            duration_ms = (end_event.timestamp - start_event.timestamp) * 1000
            assert duration_ms < 100, f"Instant tool should complete quickly, took {duration_ms:.1f}ms"


# ============================================================================
# INTEGRATION TESTS WITH REAL COMPONENTS
# ============================================================================

class TestRealServiceIntegration:
    """Integration tests with real service components."""
    
    @pytest.fixture(autouse=True)
    async def setup_real_services(self):
        """Setup real service components for integration testing."""
        # Import real components
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        
        # Create real components
        self.mock_llm = MagicMock()
        self.tool_dispatcher = ToolDispatcher()
        self.registry = AgentRegistry(self.mock_llm, self.tool_dispatcher)
        self.mock_ws = AdvancedMockWebSocketManager()
        
        # Set WebSocket manager (triggers enhancement)
        self.registry.set_websocket_manager(self.mock_ws)
        
        yield
        
        # Cleanup
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_real_agent_registry_integration(self):
        """Test tool progress with real AgentRegistry integration."""
        
        # Verify enhancement occurred
        assert hasattr(self.tool_dispatcher, '_websocket_enhanced'), \
            "Tool dispatcher should be enhanced"
        assert isinstance(self.tool_dispatcher.executor, UnifiedToolExecutionEngine), \
            "Should have enhanced executor"
        
        # Create a real tool execution context
        context = AgentExecutionContext(
            run_id="registry-test",
            thread_id="registry-thread",
            user_id="registry-user",
            agent_name="registry_agent"
        )
        
        # Execute through the enhanced dispatcher
        tool = SimulatedLongRunningTool("registry_tool", duration_ms=50)
        tool_input = ToolInput(tool_name="registry_tool", parameters={})
        
        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                         return_value=ToolResult(result="registry_result")):
            
            result = await self.tool_dispatcher.executor.execute_tool_with_input(
                tool_input, tool, {'context': context}
            )
        
        # Verify WebSocket events through registry enhancement
        events = self.mock_ws.tool_events
        assert len(events) >= 2, "Should have tool events through registry"
        
        # Verify event quality
        validation = self.mock_ws.get_event_sequence_validation("registry-thread")
        assert validation['all_tools_completed'], "Tools should complete through registry"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_supervisor_agent_tool_orchestration(self):
        """Test tool progress in supervisor agent orchestration."""
        
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        
        # Create execution engine with WebSocket support
        engine = ExecutionEngine()
        
        # Mock WebSocket injection
        if hasattr(engine, 'set_websocket_notifier'):
            notifier = WebSocketNotifier(self.mock_ws)
            engine.set_websocket_notifier(notifier)
        
        # Create complex execution context
        context = AgentExecutionContext(
            run_id="supervisor-test",
            thread_id="supervisor-thread",
            user_id="supervisor-user",
            agent_name="supervisor_agent"
        )
        
        # Simulate supervisor executing multiple tools
        tool_sequence = [
            ("data_extraction", {"source": "database"}),
            ("data_validation", {"rules": ["not_null", "unique"]}),
            ("data_analysis", {"metrics": ["mean", "std"]}),
            ("report_generation", {"format": "pdf"})
        ]
        
        for tool_name, params in tool_sequence:
            tool = SimulatedLongRunningTool(tool_name, duration_ms=30)
            tool_input = ToolInput(tool_name=tool_name, parameters=params)
            
            # Execute through supervisor pattern
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result=f"{tool_name}_complete")):
                
                if self.tool_dispatcher.executor:
                    await self.tool_dispatcher.executor.execute_tool_with_input(
                        tool_input, tool, {'context': context}
                    )
        
        # Verify orchestration events
        events = self.mock_ws.tool_events
        tool_names = {e.tool_name for e in events}
        
        for tool_name, _ in tool_sequence:
            assert tool_name in tool_names, f"Should have events for {tool_name}"
        
        # Verify execution metrics
        metrics = self.mock_ws.calculate_metrics()
        assert metrics.total_executions >= len(tool_sequence), \
            f"Should execute all {len(tool_sequence)} tools"


# ============================================================================
# PERFORMANCE AND LOAD TESTS
# ============================================================================

class TestExtremeLoad:
    """Test system behavior under extreme load."""
    
    @pytest.fixture(autouse=True)
    def setup_load_tests(self):
        """Setup for load tests."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        yield
        self.mock_ws.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_thousand_concurrent_tools(self):
        """Test system with 1000+ concurrent tool executions."""
        
        num_tools = 1000
        batch_size = 100
        
        async def execute_batch(batch_id: int):
            """Execute a batch of tools."""
            tasks = []
            
            for i in range(batch_size):
                tool_id = batch_id * batch_size + i
                context = AgentExecutionContext(
                    run_id=f"load-{tool_id}",
                    thread_id=f"load-thread-{batch_id}",
                    user_id=f"load-user-{batch_id}",
                    agent_name="load_agent"
                )
                
                tool = SimulatedLongRunningTool(
                    f"load_tool_{tool_id}",
                    duration_ms=random.randint(1, 10)
                )
                
                tool_input = ToolInput(
                    tool_name=tool.name,
                    parameters={"id": tool_id}
                )
                
                async def execute_single():
                    with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                     return_value=ToolResult(result=f"result_{tool_id}")):
                        try:
                            return await self.executor.execute_tool_with_input(
                                tool_input, tool, {'context': context}
                            )
                        except Exception:
                            return None
                
                tasks.append(execute_single())
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Execute all batches
        start_time = time.time()
        
        batch_tasks = []
        for batch_id in range(num_tools // batch_size):
            batch_tasks.append(execute_batch(batch_id))
        
        await asyncio.gather(*batch_tasks)
        
        duration = time.time() - start_time
        
        # Calculate performance metrics
        metrics = self.mock_ws.calculate_metrics()
        tools_per_second = num_tools / duration
        
        # Verify system handled the load
        assert tools_per_second > 100, \
            f"Should handle >100 tools/s under load, got {tools_per_second:.1f}"
        
        assert metrics.events_per_second > 200, \
            f"Should deliver >200 events/s under load, got {metrics.events_per_second:.1f}"
        
        logger.info(f"Extreme load test: {num_tools} tools in {duration:.2f}s "
                   f"({tools_per_second:.1f} tools/s, {metrics.events_per_second:.1f} events/s)")
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_sustained_load_stability(self):
        """Test system stability under sustained load."""
        
        duration_seconds = 5
        tools_per_second = 50
        
        start_time = time.time()
        error_count = 0
        total_executed = 0
        
        while time.time() - start_time < duration_seconds:
            # Execute a burst of tools
            burst_tasks = []
            
            for i in range(tools_per_second):
                context = AgentExecutionContext(
                    run_id=f"sustained-{total_executed + i}",
                    thread_id="sustained-thread",
                    user_id="sustained-user",
                    agent_name="sustained_agent"
                )
                
                tool = SimulatedLongRunningTool(
                    f"sustained_tool_{total_executed + i}",
                    duration_ms=5
                )
                
                tool_input = ToolInput(
                    tool_name=tool.name,
                    parameters={}
                )
                
                async def execute_with_tracking():
                    with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                     return_value=ToolResult(result="sustained")):
                        try:
                            return await self.executor.execute_tool_with_input(
                                tool_input, tool, {'context': context}
                            )
                        except Exception:
                            nonlocal error_count
                            error_count += 1
                            return None
                
                burst_tasks.append(execute_with_tracking())
            
            await asyncio.gather(*burst_tasks, return_exceptions=True)
            total_executed += tools_per_second
            
            # Small delay between bursts
            await asyncio.sleep(0.9)
        
        # Verify sustained performance
        actual_duration = time.time() - start_time
        actual_rate = total_executed / actual_duration
        
        assert actual_rate > 40, \
            f"Should sustain >40 tools/s, got {actual_rate:.1f}"
        
        assert error_count < total_executed * 0.01, \
            f"Error rate should be <1%, got {error_count}/{total_executed}"
        
        # Check event delivery consistency
        metrics = self.mock_ws.calculate_metrics()
        assert metrics.total_executions > 0, "Should have successful executions"
        
        logger.info(f"Sustained load: {total_executed} tools over {actual_duration:.1f}s "
                   f"({actual_rate:.1f} tools/s, {error_count} errors)")


# ============================================================================
# VALIDATION RUNNER
# ============================================================================

def run_bulletproof_tool_progress_validation():
    """Run comprehensive bulletproof validation of tool progress updates."""
    
    logger.info("\n" + "=" * 80)
    logger.info("BULLETPROOF TOOL PROGRESS UPDATES - COMPREHENSIVE VALIDATION")
    logger.info("=" * 80)
    
    # Run all test classes
    test_results = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "-m", "critical",  # Run critical tests
        "--durations=10"  # Show slowest tests
    ])
    
    if test_results == 0:
        logger.info("\n✅ ALL BULLETPROOF TOOL PROGRESS TESTS PASSED")
        logger.info("Tool progress updates are bulletproof and production-ready ($1M+ ARR protected)")
    else:
        logger.error("\n❌ BULLETPROOF TOOL PROGRESS TESTS FAILED")
        logger.error("CRITICAL: Tool progress update system has vulnerabilities!")
    
    return test_results


if __name__ == "__main__":
    # Run comprehensive validation
    exit_code = run_bulletproof_tool_progress_validation()
    sys.exit(exit_code)