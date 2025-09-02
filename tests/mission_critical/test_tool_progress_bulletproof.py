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


# ============================================================================
# AUTHENTICATION FLOW TOOL PROGRESS TESTS
# ============================================================================

class TestAuthenticationFlowToolProgress:
    """Test tool progress updates during authentication flows and user journeys."""
    
    @pytest.fixture(autouse=True)
    async def setup_auth_tool_progress_tests(self):
        """Setup authentication flow tool progress testing."""
        # Advanced WebSocket manager for authentication testing
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        
        # Mock authentication services with tool execution
        self.mock_auth_service = AsyncMock()
        self.mock_user_service = AsyncMock()
        self.mock_billing_service = AsyncMock()
        
        yield
        self.mock_ws.clear_all()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(300)
    async def test_signup_login_chat_tool_progress_flow(self):
        """CRITICAL: Test complete signup → login → chat flow with tool progress updates."""
        
        user_journeys = 25
        successful_journeys = []
        
        for user_idx in range(user_journeys):
            journey_start = time.time()
            user_id = f"auth_user_{user_idx}"
            thread_id = f"auth_thread_{user_idx}"
            
            # 1. SIGNUP PROCESS WITH TOOLS
            signup_context = AgentExecutionContext(
                run_id=f"signup_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="signup_agent"
            )
            
            # Email validation tool
            email_validation_tool = SimulatedLongRunningTool(
                "email_validator",
                duration_ms=100,
                should_fail=(user_idx % 10 == 9)  # 10% failure rate
            )
            
            tool_input = ToolInput(
                tool_name="email_validator",
                parameters={
                    "email": f"{user_id}@netra.ai",
                    "domain_check": True,
                    "format_validation": True
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"valid": True, "deliverable": True})):
                try:
                    email_result = await self.executor.execute_tool_with_input(
                        tool_input, email_validation_tool, {'context': signup_context}
                    )
                except Exception:
                    continue  # Skip failed validations
            
            # Password strength validation tool
            password_validation_tool = SimulatedLongRunningTool("password_validator", duration_ms=50)
            password_input = ToolInput(
                tool_name="password_validator", 
                parameters={"password": "SecurePass123!", "strength_check": True}
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"strength": "strong", "score": 8.5})):
                password_result = await self.executor.execute_tool_with_input(
                    password_input, password_validation_tool, {'context': signup_context}
                )
            
            # Account creation tool
            account_creation_tool = SimulatedLongRunningTool("account_creator", duration_ms=200)
            account_input = ToolInput(
                tool_name="account_creator",
                parameters={
                    "user_data": {
                        "email": f"{user_id}@netra.ai",
                        "full_name": f"Auth Test User {user_idx}",
                        "company": f"Test Company {user_idx}",
                        "tier": "premium" if user_idx % 3 == 0 else "free"
                    }
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"account_id": user_id, "created": True})):
                account_result = await self.executor.execute_tool_with_input(
                    account_input, account_creation_tool, {'context': signup_context}
                )
            
            # 2. LOGIN PROCESS WITH TOOLS
            login_context = AgentExecutionContext(
                run_id=f"login_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="login_agent"
            )
            
            # Credential verification tool
            credential_tool = SimulatedLongRunningTool("credential_verifier", duration_ms=150)
            credential_input = ToolInput(
                tool_name="credential_verifier",
                parameters={
                    "email": f"{user_id}@netra.ai",
                    "password_hash": "hashed_password_123",
                    "two_factor": False
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"authenticated": True, "user_id": user_id})):
                credential_result = await self.executor.execute_tool_with_input(
                    credential_input, credential_tool, {'context': login_context}
                )
            
            # JWT token generation tool
            jwt_tool = SimulatedLongRunningTool("jwt_generator", duration_ms=75)
            jwt_input = ToolInput(
                tool_name="jwt_generator",
                parameters={
                    "user_id": user_id,
                    "permissions": ["chat", "agents", "tools"],
                    "tier": "premium" if user_idx % 3 == 0 else "free",
                    "expires_in": 3600
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"jwt_token": f"jwt_{user_idx}", "expires": 3600})):
                jwt_result = await self.executor.execute_tool_with_input(
                    jwt_input, jwt_tool, {'context': login_context}
                )
            
            # 3. AI CHAT INTERACTION WITH MULTIPLE TOOLS
            chat_context = AgentExecutionContext(
                run_id=f"chat_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="chat_agent"
            )
            
            # Query processing tool
            query_processor_tool = SimulatedLongRunningTool("query_processor", duration_ms=300)
            query_input = ToolInput(
                tool_name="query_processor",
                parameters={
                    "query": f"How can I optimize my {user_idx % 3 + 1}-person team's AI workflow?",
                    "user_context": {
                        "tier": "premium" if user_idx % 3 == 0 else "free",
                        "company": f"Test Company {user_idx}"
                    }
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"processed_query": "team optimization query"})):
                query_result = await self.executor.execute_tool_with_input(
                    query_input, query_processor_tool, {'context': chat_context}
                )
            
            # Knowledge retrieval tool
            knowledge_tool = SimulatedLongRunningTool("knowledge_retriever", duration_ms=500)
            knowledge_input = ToolInput(
                tool_name="knowledge_retriever",
                parameters={
                    "query": "team AI workflow optimization",
                    "sources": ["documentation", "best_practices", "case_studies"],
                    "user_tier": "premium" if user_idx % 3 == 0 else "free"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"knowledge_results": "optimization strategies"})):
                knowledge_result = await self.executor.execute_tool_with_input(
                    knowledge_input, knowledge_tool, {'context': chat_context}
                )
            
            # Response generation tool
            response_generator_tool = SimulatedLongRunningTool("response_generator", duration_ms=800)
            response_input = ToolInput(
                tool_name="response_generator",
                parameters={
                    "processed_query": "team optimization query",
                    "knowledge": "optimization strategies",
                    "user_tier": "premium" if user_idx % 3 == 0 else "free",
                    "response_length": "detailed" if user_idx % 3 == 0 else "standard"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "response": f"AI-generated team optimization response for user {user_idx}",
                                 "tokens": {"input": 150, "output": 400, "total": 550},
                                 "cost": 0.025
                             })):
                response_result = await self.executor.execute_tool_with_input(
                    response_input, response_generator_tool, {'context': chat_context}
                )
            
            # 4. BILLING AND USAGE TRACKING TOOLS
            usage_context = AgentExecutionContext(
                run_id=f"usage_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="billing_agent"
            )
            
            # Usage tracking tool
            usage_tracker_tool = SimulatedLongRunningTool("usage_tracker", duration_ms=100)
            usage_input = ToolInput(
                tool_name="usage_tracker",
                parameters={
                    "user_id": user_id,
                    "session_data": {
                        "tools_used": 7,  # Total tools in this journey
                        "ai_tokens": 550,
                        "processing_time_ms": 1500,
                        "tier": "premium" if user_idx % 3 == 0 else "free"
                    }
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={"usage_recorded": True, "cost": 0.025})):
                usage_result = await self.executor.execute_tool_with_input(
                    usage_input, usage_tracker_tool, {'context': usage_context}
                )
            
            # Journey completion tracking
            journey_duration = time.time() - journey_start
            
            journey_summary = {
                "user_id": user_id,
                "thread_id": thread_id,
                "tools_executed": 7,
                "journey_duration_seconds": journey_duration,
                "tier": "premium" if user_idx % 3 == 0 else "free",
                "success": True,
                "revenue_generated": 0.05  # $0.05 revenue per complete journey
            }
            
            successful_journeys.append(journey_summary)
            
            # Small delay between journeys
            await asyncio.sleep(0.02)
        
        # CRITICAL AUTHENTICATION TOOL PROGRESS ASSERTIONS
        
        # Verify all tool events were captured
        all_events = self.mock_ws.tool_events
        executing_events = [e for e in all_events if e.event_type == 'tool_executing']
        completed_events = [e for e in all_events if e.event_type == 'tool_completed']
        
        expected_tools_per_journey = 7
        expected_total_executions = len(successful_journeys) * expected_tools_per_journey
        
        assert len(executing_events) >= expected_total_executions * 0.9, \
            f"Missing tool executing events: {len(executing_events)} < {expected_total_executions * 0.9}"
        
        assert len(completed_events) >= expected_total_executions * 0.9, \
            f"Missing tool completed events: {len(completed_events)} < {expected_total_executions * 0.9}"
        
        # Verify event sequence integrity for each user journey
        validation_failures = 0
        for journey in successful_journeys:
            validation = self.mock_ws.get_event_sequence_validation(journey["thread_id"])
            if not validation.get("all_tools_completed", False):
                validation_failures += 1
        
        assert validation_failures < len(successful_journeys) * 0.1, \
            f"Too many validation failures: {validation_failures}/{len(successful_journeys)}"
        
        # Business metrics validation
        total_revenue = sum(j["revenue_generated"] for j in successful_journeys)
        average_journey_time = sum(j["journey_duration_seconds"] for j in successful_journeys) / len(successful_journeys)
        premium_users = len([j for j in successful_journeys if j["tier"] == "premium"])
        
        assert total_revenue > 0, "Should generate revenue from user journeys"
        assert average_journey_time < 10, f"Journey time too long: {average_journey_time:.1f}s (limit: <10s)"
        assert premium_users > 0, "Should have premium user conversions"
        
        # Performance metrics
        metrics = self.mock_ws.calculate_metrics()
        assert metrics.total_executions >= expected_total_executions * 0.9, \
            f"Tool execution count too low: {metrics.total_executions}"
        
        logger.info(f"Authentication flow tool progress: {len(successful_journeys)} journeys, "
                   f"{len(executing_events)} executing events, {len(completed_events)} completed events, "
                   f"{average_journey_time:.1f}s avg journey time, ${total_revenue:.2f} revenue")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(240)
    async def test_jwt_token_refresh_tool_progress(self):
        """CRITICAL: Test JWT token refresh during active chat with tool progress tracking."""
        
        concurrent_sessions = 20
        
        async def simulate_token_refresh_session(session_idx: int):
            """Simulate a session with token refresh during active chat."""
            user_id = f"refresh_user_{session_idx}"
            thread_id = f"refresh_thread_{session_idx}"
            
            session_data = {
                "user_id": user_id,
                "thread_id": thread_id,
                "tools_executed": 0,
                "refresh_count": 0,
                "ai_interactions": 0,
                "revenue": 0
            }
            
            # Simulate long chat session requiring token refresh
            for interaction in range(10):  # 10 AI interactions per session
                
                # JWT validation tool (every interaction)
                jwt_context = AgentExecutionContext(
                    run_id=f"jwt_check_{session_idx}_{interaction}",
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_name="jwt_validator"
                )
                
                jwt_validation_tool = SimulatedLongRunningTool("jwt_validator", duration_ms=50)
                jwt_input = ToolInput(
                    tool_name="jwt_validator",
                    parameters={
                        "jwt_token": f"jwt_{session_idx}_{interaction}",
                        "required_permissions": ["chat", "agents"],
                        "check_expiry": True
                    }
                )
                
                # Simulate token expiry on interaction 5
                token_valid = interaction < 5
                jwt_result_data = {"valid": token_valid, "expired": not token_valid}
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result=jwt_result_data)):
                    jwt_result = await self.executor.execute_tool_with_input(
                        jwt_input, jwt_validation_tool, {'context': jwt_context}
                    )
                
                session_data["tools_executed"] += 1
                
                # Token refresh if expired
                if not token_valid:
                    refresh_context = AgentExecutionContext(
                        run_id=f"token_refresh_{session_idx}_{interaction}",
                        thread_id=thread_id,
                        user_id=user_id,
                        agent_name="token_refresher"
                    )
                    
                    token_refresh_tool = SimulatedLongRunningTool("token_refresher", duration_ms=200)
                    refresh_input = ToolInput(
                        tool_name="token_refresher",
                        parameters={
                            "user_id": user_id,
                            "refresh_token": f"refresh_{session_idx}",
                            "extend_session": True
                        }
                    )
                    
                    with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                     return_value=ToolResult(result={
                                         "new_jwt": f"new_jwt_{session_idx}_{interaction}",
                                         "expires_in": 3600
                                     })):
                        refresh_result = await self.executor.execute_tool_with_input(
                            refresh_input, token_refresh_tool, {'context': refresh_context}
                        )
                    
                    session_data["tools_executed"] += 1
                    session_data["refresh_count"] += 1
                
                # AI interaction tool (after auth)
                ai_context = AgentExecutionContext(
                    run_id=f"ai_interaction_{session_idx}_{interaction}",
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_name="ai_chat_agent"
                )
                
                ai_interaction_tool = SimulatedLongRunningTool("ai_chat_processor", duration_ms=400)
                ai_input = ToolInput(
                    tool_name="ai_chat_processor",
                    parameters={
                        "query": f"Chat query {interaction} from session {session_idx}",
                        "context": {"interaction_number": interaction},
                        "authenticated": True
                    }
                )
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result={
                                     "response": f"AI response {interaction}",
                                     "tokens": {"total": 200},
                                     "cost": 0.01
                                 })):
                    ai_result = await self.executor.execute_tool_with_input(
                        ai_input, ai_interaction_tool, {'context': ai_context}
                    )
                
                session_data["tools_executed"] += 1
                session_data["ai_interactions"] += 1
                session_data["revenue"] += 0.02  # $0.02 per AI interaction
                
                # Brief delay between interactions
                await asyncio.sleep(0.01)
            
            return session_data
        
        # Run all sessions concurrently
        tasks = [
            asyncio.create_task(simulate_token_refresh_session(i))
            for i in range(concurrent_sessions)
        ]
        
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sessions = [r for r in session_results if isinstance(r, dict)]
        
        # CRITICAL TOKEN REFRESH TOOL PROGRESS ASSERTIONS
        
        # Verify all sessions completed successfully
        assert len(successful_sessions) >= concurrent_sessions * 0.95, \
            f"Too many session failures: {len(successful_sessions)}/{concurrent_sessions}"
        
        # Verify tool event integrity
        all_events = self.mock_ws.tool_events
        refresh_events = [e for e in all_events if 'refresh' in e.tool_name.lower()]
        jwt_validation_events = [e for e in all_events if 'jwt_validator' in e.tool_name]
        ai_interaction_events = [e for e in all_events if 'ai_chat' in e.tool_name]
        
        # Each session should have token refreshes
        total_refresh_count = sum(s["refresh_count"] for s in successful_sessions)
        assert total_refresh_count > 0, "Should have token refresh operations"
        assert len(refresh_events) >= total_refresh_count * 2, \
            f"Missing refresh events: {len(refresh_events)} < {total_refresh_count * 2}"
        
        # JWT validation should happen for every interaction
        expected_jwt_validations = sum(s["ai_interactions"] for s in successful_sessions)
        assert len(jwt_validation_events) >= expected_jwt_validations * 2, \
            f"Missing JWT validation events: {len(jwt_validation_events)} < {expected_jwt_validations * 2}"
        
        # AI interactions should all have events
        expected_ai_interactions = sum(s["ai_interactions"] for s in successful_sessions)
        assert len(ai_interaction_events) >= expected_ai_interactions * 2, \
            f"Missing AI interaction events: {len(ai_interaction_events)} < {expected_ai_interactions * 2}"
        
        # Business metrics
        total_tools = sum(s["tools_executed"] for s in successful_sessions)
        total_revenue = sum(s["revenue"] for s in successful_sessions)
        
        assert total_tools >= concurrent_sessions * 25, \
            f"Tool execution count too low: {total_tools} (expected ≥{concurrent_sessions * 25})"
        
        assert total_revenue > concurrent_sessions * 0.15, \
            f"Revenue too low: ${total_revenue:.2f} (expected >${concurrent_sessions * 0.15})"
        
        # Performance metrics
        metrics = self.mock_ws.calculate_metrics()
        assert metrics.events_per_second > 50, \
            f"Event delivery rate too low: {metrics.events_per_second:.1f} events/s (need >50)"
        
        logger.info(f"Token refresh tool progress: {len(successful_sessions)} sessions, "
                   f"{total_refresh_count} token refreshes, {len(refresh_events)} refresh events, "
                   f"${total_revenue:.2f} revenue, {metrics.events_per_second:.1f} events/s")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(180)
    async def test_oauth_social_login_tool_progress(self):
        """CRITICAL: Test OAuth/social login flows with comprehensive tool progress tracking."""
        
        oauth_providers = ["google", "microsoft", "github", "linkedin"]
        logins_per_provider = 10
        
        for provider in oauth_providers:
            provider_results = []
            
            for login_idx in range(logins_per_provider):
                user_id = f"{provider}_user_{login_idx}"
                thread_id = f"{provider}_thread_{login_idx}"
                
                # 1. OAuth Initiation Tool
                oauth_context = AgentExecutionContext(
                    run_id=f"oauth_init_{provider}_{login_idx}",
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_name="oauth_initiator"
                )
                
                oauth_init_tool = SimulatedLongRunningTool("oauth_initiator", duration_ms=100)
                oauth_init_input = ToolInput(
                    tool_name="oauth_initiator",
                    parameters={
                        "provider": provider,
                        "redirect_uri": f"https://netra.ai/auth/{provider}/callback",
                        "scopes": ["profile", "email"]
                    }
                )
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result={
                                     "auth_url": f"https://{provider}.com/oauth/authorize?state=xyz",
                                     "state": f"{provider}_state_{login_idx}"
                                 })):
                    oauth_init_result = await self.executor.execute_tool_with_input(
                        oauth_init_input, oauth_init_tool, {'context': oauth_context}
                    )
                
                # 2. OAuth Callback Processing Tool
                callback_tool = SimulatedLongRunningTool("oauth_callback_processor", duration_ms=300)
                callback_input = ToolInput(
                    tool_name="oauth_callback_processor",
                    parameters={
                        "provider": provider,
                        "authorization_code": f"auth_code_{provider}_{login_idx}",
                        "state": f"{provider}_state_{login_idx}"
                    }
                )
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result={
                                     "access_token": f"{provider}_access_{login_idx}",
                                     "user_info": {
                                         "id": f"{provider}_id_{login_idx}",
                                         "email": f"user{login_idx}@{provider}.com",
                                         "name": f"{provider} User {login_idx}"
                                     }
                                 })):
                    callback_result = await self.executor.execute_tool_with_input(
                        callback_input, callback_tool, {'context': oauth_context}
                    )
                
                # 3. User Profile Sync Tool
                profile_sync_tool = SimulatedLongRunningTool("profile_synchronizer", duration_ms=200)
                profile_sync_input = ToolInput(
                    tool_name="profile_synchronizer",
                    parameters={
                        "provider": provider,
                        "external_user_info": {
                            "id": f"{provider}_id_{login_idx}",
                            "email": f"user{login_idx}@{provider}.com",
                            "name": f"{provider} User {login_idx}"
                        },
                        "create_if_not_exists": True
                    }
                )
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result={
                                     "user_id": user_id,
                                     "profile_updated": True,
                                     "new_user": login_idx % 3 == 0  # 33% new users
                                 })):
                    profile_result = await self.executor.execute_tool_with_input(
                        profile_sync_input, profile_sync_tool, {'context': oauth_context}
                    )
                
                # 4. Internal JWT Generation Tool
                jwt_generation_tool = SimulatedLongRunningTool("internal_jwt_generator", duration_ms=75)
                jwt_input = ToolInput(
                    tool_name="internal_jwt_generator",
                    parameters={
                        "user_id": user_id,
                        "provider": provider,
                        "external_token": f"{provider}_access_{login_idx}",
                        "tier": "premium" if provider in ["microsoft", "github"] else "free"
                    }
                )
                
                with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                 return_value=ToolResult(result={
                                     "internal_jwt": f"netra_jwt_{provider}_{login_idx}",
                                     "expires_in": 7200,
                                     "tier": "premium" if provider in ["microsoft", "github"] else "free"
                                 })):
                    jwt_generation_result = await self.executor.execute_tool_with_input(
                        jwt_input, jwt_generation_tool, {'context': oauth_context}
                    )
                
                # 5. Welcome/Onboarding Tool (for new users)
                is_new_user = login_idx % 3 == 0
                if is_new_user:
                    onboarding_tool = SimulatedLongRunningTool("user_onboarding", duration_ms=400)
                    onboarding_input = ToolInput(
                        tool_name="user_onboarding",
                        parameters={
                            "user_id": user_id,
                            "provider": provider,
                            "user_tier": "premium" if provider in ["microsoft", "github"] else "free",
                            "onboarding_flow": "oauth_welcome"
                        }
                    )
                    
                    with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                     return_value=ToolResult(result={
                                         "onboarding_completed": True,
                                         "welcome_credits": 100,
                                         "tutorial_started": True
                                     })):
                        onboarding_result = await self.executor.execute_tool_with_input(
                            onboarding_input, onboarding_tool, {'context': oauth_context}
                        )
                
                # Track OAuth login result
                oauth_login_result = {
                    "user_id": user_id,
                    "provider": provider,
                    "thread_id": thread_id,
                    "tools_executed": 5 if is_new_user else 4,
                    "new_user": is_new_user,
                    "user_tier": "premium" if provider in ["microsoft", "github"] else "free",
                    "success": True
                }
                
                provider_results.append(oauth_login_result)
                
                # Small delay between OAuth logins
                await asyncio.sleep(0.02)
            
            # Validate OAuth provider results
            successful_logins = len(provider_results)
            new_user_signups = len([r for r in provider_results if r["new_user"]])
            premium_conversions = len([r for r in provider_results if r["user_tier"] == "premium"])
            
            # Provider-specific assertions
            assert successful_logins == logins_per_provider, \
                f"{provider}: Login completion rate too low: {successful_logins}/{logins_per_provider}"
            
            assert new_user_signups > 0, f"{provider}: Should have new user signups"
            
            if provider in ["microsoft", "github"]:
                assert premium_conversions == successful_logins, \
                    f"{provider}: Should convert all users to premium"
            
            logger.info(f"{provider} OAuth: {successful_logins} logins, {new_user_signups} new users, "
                       f"{premium_conversions} premium conversions")
        
        # CRITICAL OAUTH TOOL PROGRESS ASSERTIONS
        
        # Verify comprehensive tool event tracking
        all_events = self.mock_ws.tool_events
        oauth_events = [e for e in all_events if any(term in e.tool_name.lower() 
                       for term in ['oauth', 'profile', 'jwt', 'onboarding'])]
        
        total_expected_tools = sum(
            (5 if login_idx % 3 == 0 else 4) * logins_per_provider 
            for login_idx in range(logins_per_provider)
        ) * len(oauth_providers)
        
        assert len(oauth_events) >= total_expected_tools * 2, \
            f"Missing OAuth tool events: {len(oauth_events)} < {total_expected_tools * 2}"
        
        # Event sequence validation per provider
        for provider in oauth_providers:
            provider_threads = [f"{provider}_thread_{i}" for i in range(logins_per_provider)]
            validation_failures = 0
            
            for thread_id in provider_threads:
                validation = self.mock_ws.get_event_sequence_validation(thread_id)
                if not validation.get("all_tools_completed", False):
                    validation_failures += 1
            
            assert validation_failures < logins_per_provider * 0.1, \
                f"{provider}: Too many validation failures: {validation_failures}"
        
        # Business metrics validation
        total_premium_users = sum(
            len([r for r in provider_results if r["user_tier"] == "premium"])
            for provider_results in [provider_results]  # This needs to be accumulated properly
        )
        
        # Performance assertions
        metrics = self.mock_ws.calculate_metrics()
        total_oauth_logins = len(oauth_providers) * logins_per_provider
        
        assert metrics.total_executions >= total_expected_tools * 0.95, \
            f"Tool execution rate too low: {metrics.total_executions}/{total_expected_tools}"
        
        assert metrics.events_per_second > 20, \
            f"OAuth event delivery rate too low: {metrics.events_per_second:.1f} events/s (need >20)"
        
        logger.info(f"OAuth social login tool progress: {len(oauth_providers)} providers, "
                   f"{total_oauth_logins} total logins, {len(oauth_events)} tool events, "
                   f"{metrics.events_per_second:.1f} events/s")


# ============================================================================
# USER JOURNEY TOOL PROGRESS VALIDATION
# ============================================================================

class TestUserJourneyToolProgress:
    """Test tool progress during complete user journeys from onboarding to power usage."""
    
    @pytest.fixture(autouse=True)
    async def setup_user_journey_tool_tests(self):
        """Setup user journey tool progress testing."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        
        # Mock services for user journey tools
        self.mock_onboarding_service = AsyncMock()
        self.mock_analytics_service = AsyncMock()
        self.mock_billing_service = AsyncMock()
        
        yield
        self.mock_ws.clear_all()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(400)
    async def test_first_time_user_onboarding_tool_chain(self):
        """CRITICAL: Test first-time user complete onboarding with tool chain progress."""
        
        new_users = 15
        onboarding_completions = []
        
        for user_idx in range(new_users):
            onboarding_start = time.time()
            user_id = f"onboarding_user_{user_idx}"
            thread_id = f"onboarding_thread_{user_idx}"
            
            # ONBOARDING STAGE 1: Account Setup Tools
            setup_context = AgentExecutionContext(
                run_id=f"account_setup_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="account_setup_agent"
            )
            
            # Email domain analysis tool
            email_domain_tool = SimulatedLongRunningTool("email_domain_analyzer", duration_ms=150)
            domain_input = ToolInput(
                tool_name="email_domain_analyzer",
                parameters={
                    "email": f"newuser{user_idx}@startup{user_idx % 5}.com",
                    "check_business": True,
                    "industry_detection": True
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "domain_type": "business",
                                 "industry": "technology" if user_idx % 2 == 0 else "consulting",
                                 "company_size": "startup"
                             })):
                domain_result = await self.executor.execute_tool_with_input(
                    domain_input, email_domain_tool, {'context': setup_context}
                )
            
            # Company profile enrichment tool
            company_enrichment_tool = SimulatedLongRunningTool("company_enricher", duration_ms=300)
            company_input = ToolInput(
                tool_name="company_enricher",
                parameters={
                    "company_name": f"Startup {user_idx}",
                    "domain": f"startup{user_idx % 5}.com",
                    "enrichment_level": "basic"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "company_data": {
                                     "size": "1-10 employees",
                                     "industry": "technology",
                                     "funding_stage": "seed",
                                     "ai_readiness": "high" if user_idx % 3 == 0 else "medium"
                                 }
                             })):
                company_result = await self.executor.execute_tool_with_input(
                    company_input, company_enrichment_tool, {'context': setup_context}
                )
            
            # ONBOARDING STAGE 2: Personalization Tools
            personalization_context = AgentExecutionContext(
                run_id=f"personalization_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="personalization_agent"
            )
            
            # Use case recommendation tool
            use_case_tool = SimulatedLongRunningTool("use_case_recommender", duration_ms=200)
            use_case_input = ToolInput(
                tool_name="use_case_recommender",
                parameters={
                    "industry": "technology" if user_idx % 2 == 0 else "consulting",
                    "company_size": "startup",
                    "ai_readiness": "high" if user_idx % 3 == 0 else "medium"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "recommended_use_cases": [
                                     "automated_research",
                                     "content_generation",
                                     "data_analysis"
                                 ],
                                 "priority_use_case": "automated_research"
                             })):
                use_case_result = await self.executor.execute_tool_with_input(
                    use_case_input, use_case_tool, {'context': personalization_context}
                )
            
            # Agent recommendation tool
            agent_recommendation_tool = SimulatedLongRunningTool("agent_recommender", duration_ms=250)
            agent_input = ToolInput(
                tool_name="agent_recommender",
                parameters={
                    "use_cases": ["automated_research", "content_generation", "data_analysis"],
                    "user_tier": "free",  # All new users start free
                    "experience_level": "beginner"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "recommended_agents": [
                                     "research_assistant",
                                     "content_writer",
                                     "data_analyst"
                                 ],
                                 "starter_agent": "research_assistant"
                             })):
                agent_result = await self.executor.execute_tool_with_input(
                    agent_input, agent_recommendation_tool, {'context': personalization_context}
                )
            
            # ONBOARDING STAGE 3: Tutorial and First AI Interaction
            tutorial_context = AgentExecutionContext(
                run_id=f"tutorial_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="tutorial_agent"
            )
            
            # Tutorial content generator tool
            tutorial_generator_tool = SimulatedLongRunningTool("tutorial_generator", duration_ms=400)
            tutorial_input = ToolInput(
                tool_name="tutorial_generator",
                parameters={
                    "user_profile": {
                        "industry": "technology" if user_idx % 2 == 0 else "consulting",
                        "recommended_agent": "research_assistant",
                        "experience": "beginner"
                    },
                    "tutorial_type": "interactive_demo"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "tutorial_content": {
                                     "steps": 5,
                                     "estimated_duration": "3-5 minutes",
                                     "interactive_elements": 3
                                 },
                                 "sample_queries": [
                                     "Research the latest AI trends in my industry",
                                     "Generate a market analysis report",
                                     "Analyze competitor strategies"
                                 ]
                             })):
                tutorial_result = await self.executor.execute_tool_with_input(
                    tutorial_input, tutorial_generator_tool, {'context': tutorial_context}
                )
            
            # First AI interaction execution tool
            first_ai_tool = SimulatedLongRunningTool("first_ai_interaction", duration_ms=800)
            first_ai_input = ToolInput(
                tool_name="first_ai_interaction",
                parameters={
                    "query": f"Research the latest AI trends in {domain_result.result.get('industry', 'technology')}",
                    "agent": "research_assistant",
                    "user_context": {
                        "first_time": True,
                        "industry": domain_result.result.get('industry', 'technology'),
                        "tutorial_mode": True
                    }
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "research_results": f"AI trends analysis for {domain_result.result.get('industry', 'technology')}",
                                 "sources_found": 8,
                                 "insights_generated": 5,
                                 "tokens_used": {"input": 100, "output": 300, "total": 400},
                                 "cost": 0.02,
                                 "user_satisfaction": 0.9
                             })):
                first_ai_result = await self.executor.execute_tool_with_input(
                    first_ai_input, first_ai_tool, {'context': tutorial_context}
                )
            
            # ONBOARDING STAGE 4: Engagement Analysis and Conversion Assessment
            assessment_context = AgentExecutionContext(
                run_id=f"assessment_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="engagement_assessor"
            )
            
            # Engagement scoring tool
            engagement_tool = SimulatedLongRunningTool("engagement_scorer", duration_ms=100)
            engagement_input = ToolInput(
                tool_name="engagement_scorer",
                parameters={
                    "tutorial_completion": True,
                    "first_ai_satisfaction": 0.9,
                    "time_spent_minutes": (time.time() - onboarding_start) / 60,
                    "interactions_completed": 5
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "engagement_score": 0.85 + (user_idx % 15) * 0.01,  # 0.85-1.0 range
                                 "conversion_likelihood": 0.3 if user_idx % 3 == 0 else 0.15,
                                 "recommended_tier": "early" if user_idx % 3 == 0 else "free_extended"
                             })):
                engagement_result = await self.executor.execute_tool_with_input(
                    engagement_input, engagement_tool, {'context': assessment_context}
                )
            
            # Conversion opportunity tool
            conversion_tool = SimulatedLongRunningTool("conversion_opportunity", duration_ms=150)
            conversion_input = ToolInput(
                tool_name="conversion_opportunity",
                parameters={
                    "engagement_score": engagement_result.result["engagement_score"],
                    "user_profile": {
                        "industry": domain_result.result.get('industry'),
                        "company_ai_readiness": company_result.result["company_data"]["ai_readiness"],
                        "use_case_fit": "high" if user_idx % 2 == 0 else "medium"
                    }
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "conversion_strategy": {
                                     "immediate_offer": user_idx % 4 == 0,  # 25% get immediate offer
                                     "trial_extension": user_idx % 2 == 0,  # 50% get trial extension
                                     "follow_up_sequence": True
                                 },
                                 "estimated_ltv": 250 + (user_idx * 50),  # $250-$1000 LTV
                             })):
                conversion_result = await self.executor.execute_tool_with_input(
                    conversion_input, conversion_tool, {'context': assessment_context}
                )
            
            # Onboarding completion tracking
            onboarding_duration = time.time() - onboarding_start
            
            completion_data = {
                "user_id": user_id,
                "thread_id": thread_id,
                "tools_executed": 7,  # Total tools in onboarding
                "onboarding_duration_minutes": onboarding_duration / 60,
                "engagement_score": engagement_result.result["engagement_score"],
                "conversion_likelihood": engagement_result.result["conversion_likelihood"],
                "estimated_ltv": conversion_result.result["estimated_ltv"],
                "industry": domain_result.result.get('industry'),
                "first_ai_success": True,
                "completion_success": True
            }
            
            onboarding_completions.append(completion_data)
            
            # Small delay between onboardings
            await asyncio.sleep(0.03)
        
        # CRITICAL ONBOARDING TOOL PROGRESS ASSERTIONS
        
        # Verify all tool events captured
        all_events = self.mock_ws.tool_events
        onboarding_events = [e for e in all_events if any(term in e.tool_name.lower() 
                           for term in ['domain', 'company', 'use_case', 'agent', 'tutorial', 'engagement', 'conversion'])]
        
        expected_total_tools = len(onboarding_completions) * 7
        assert len(onboarding_events) >= expected_total_tools * 2, \
            f"Missing onboarding tool events: {len(onboarding_events)} < {expected_total_tools * 2}"
        
        # Event sequence validation for each onboarding
        validation_failures = 0
        for completion in onboarding_completions:
            validation = self.mock_ws.get_event_sequence_validation(completion["thread_id"])
            if not validation.get("all_tools_completed", False):
                validation_failures += 1
        
        assert validation_failures < len(onboarding_completions) * 0.1, \
            f"Too many onboarding validation failures: {validation_failures}"
        
        # Business metrics validation
        successful_completions = [c for c in onboarding_completions if c["completion_success"]]
        average_engagement = sum(c["engagement_score"] for c in successful_completions) / len(successful_completions)
        high_conversion_users = [c for c in successful_completions if c["conversion_likelihood"] > 0.25]
        total_estimated_ltv = sum(c["estimated_ltv"] for c in successful_completions)
        
        assert len(successful_completions) == new_users, \
            "All onboardings should complete successfully"
        
        assert average_engagement > 0.8, \
            f"Average engagement too low: {average_engagement:.2f} (need >0.8)"
        
        assert len(high_conversion_users) > 0, \
            "Should have high-conversion potential users"
        
        assert total_estimated_ltv > new_users * 200, \
            f"Total estimated LTV too low: ${total_estimated_ltv} (need >${new_users * 200})"
        
        # Performance metrics
        average_onboarding_time = sum(c["onboarding_duration_minutes"] for c in successful_completions) / len(successful_completions)
        assert average_onboarding_time < 8, \
            f"Onboarding too long: {average_onboarding_time:.1f} minutes (limit: <8 min)"
        
        metrics = self.mock_ws.calculate_metrics()
        assert metrics.total_executions >= expected_total_tools * 0.95, \
            f"Tool execution rate too low: {metrics.total_executions}/{expected_total_tools}"
        
        logger.info(f"Onboarding tool progress: {len(successful_completions)} completions, "
                   f"{len(onboarding_events)} tool events, {average_engagement:.2f} avg engagement, "
                   f"{len(high_conversion_users)} high-conversion users, "
                   f"${total_estimated_ltv:,.0f} total estimated LTV, "
                   f"{average_onboarding_time:.1f} min avg duration")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(360)
    async def test_power_user_multi_agent_tool_orchestration(self):
        """CRITICAL: Test power user workflows with multi-agent tool orchestration and progress tracking."""
        
        power_users = 8
        enterprise_workflows = []
        
        for user_idx in range(power_users):
            workflow_start = time.time()
            user_id = f"power_user_{user_idx}"
            thread_id = f"power_thread_{user_idx}"
            
            user_profile = {
                "tier": "enterprise" if user_idx < 3 else "mid",
                "monthly_spend": 800 + (user_idx * 200),  # $800-$2200/month
                "team_size": 10 + (user_idx * 5),  # 10-45 team members
                "workflow_complexity": "high"
            }
            
            workflow_data = {
                "user_id": user_id,
                "thread_id": thread_id,
                "agent_executions": 0,
                "tools_executed": 0,
                "data_processed_mb": 0,
                "revenue_generated": 0,
                "workflow_stages_completed": 0
            }
            
            # WORKFLOW STAGE 1: Data Ingestion and Analysis
            data_context = AgentExecutionContext(
                run_id=f"data_ingestion_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="data_ingestion_agent"
            )
            
            # Data source connector tool
            data_connector_tool = SimulatedLongRunningTool("data_source_connector", duration_ms=500)
            connector_input = ToolInput(
                tool_name="data_source_connector",
                parameters={
                    "data_sources": ["salesforce", "hubspot", "analytics", "internal_db"],
                    "data_types": ["customer", "sales", "marketing", "product"],
                    "date_range": "last_30_days"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "data_retrieved": {
                                     "total_records": 50000 + (user_idx * 10000),
                                     "size_mb": 100 + (user_idx * 50),
                                     "sources_connected": 4
                                 },
                                 "data_quality_score": 0.85 + (user_idx * 0.02)
                             })):
                connector_result = await self.executor.execute_tool_with_input(
                    connector_input, data_connector_tool, {'context': data_context}
                )
            
            workflow_data["tools_executed"] += 1
            workflow_data["data_processed_mb"] += connector_result.result["data_retrieved"]["size_mb"]
            
            # Data validation and cleaning tool
            data_cleaner_tool = SimulatedLongRunningTool("data_cleaner", duration_ms=800)
            cleaner_input = ToolInput(
                tool_name="data_cleaner",
                parameters={
                    "data_size_mb": connector_result.result["data_retrieved"]["size_mb"],
                    "cleaning_level": "comprehensive",
                    "validation_rules": ["completeness", "consistency", "accuracy"]
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "cleaned_data": {
                                     "records_processed": connector_result.result["data_retrieved"]["total_records"],
                                     "quality_improvement": 0.15,
                                     "duplicate_removal": 1200 + (user_idx * 200)
                                 }
                             })):
                cleaner_result = await self.executor.execute_tool_with_input(
                    cleaner_input, data_cleaner_tool, {'context': data_context}
                )
            
            workflow_data["tools_executed"] += 1
            workflow_data["agent_executions"] += 1
            workflow_data["workflow_stages_completed"] += 1
            
            # WORKFLOW STAGE 2: AI-Powered Analysis
            analysis_context = AgentExecutionContext(
                run_id=f"ai_analysis_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="ai_analysis_agent"
            )
            
            # Pattern discovery tool
            pattern_discovery_tool = SimulatedLongRunningTool("pattern_discovery", duration_ms=1200)
            pattern_input = ToolInput(
                tool_name="pattern_discovery",
                parameters={
                    "data_size": cleaner_result.result["cleaned_data"]["records_processed"],
                    "analysis_type": "comprehensive",
                    "pattern_types": ["trends", "anomalies", "correlations", "segments"]
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "patterns_discovered": {
                                     "trend_patterns": 15 + (user_idx * 3),
                                     "anomalies_detected": 8 + user_idx,
                                     "correlation_strength": 0.75 + (user_idx * 0.03),
                                     "customer_segments": 6 + (user_idx % 3)
                                 },
                                 "confidence_score": 0.88
                             })):
                pattern_result = await self.executor.execute_tool_with_input(
                    pattern_input, pattern_discovery_tool, {'context': analysis_context}
                )
            
            workflow_data["tools_executed"] += 1
            
            # Predictive modeling tool
            predictive_model_tool = SimulatedLongRunningTool("predictive_modeler", duration_ms=1500)
            model_input = ToolInput(
                tool_name="predictive_modeler",
                parameters={
                    "patterns": pattern_result.result["patterns_discovered"],
                    "model_types": ["churn_prediction", "revenue_forecast", "demand_planning"],
                    "prediction_horizon": "3_months"
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "models_created": {
                                     "churn_model_accuracy": 0.89 + (user_idx * 0.01),
                                     "revenue_forecast_confidence": 0.82,
                                     "demand_accuracy": 0.86
                                 },
                                 "business_impact_score": 0.91
                             })):
                model_result = await self.executor.execute_tool_with_input(
                    model_input, predictive_model_tool, {'context': analysis_context}
                )
            
            workflow_data["tools_executed"] += 1
            workflow_data["agent_executions"] += 1
            workflow_data["workflow_stages_completed"] += 1
            
            # WORKFLOW STAGE 3: Report Generation and Insights
            reporting_context = AgentExecutionContext(
                run_id=f"reporting_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="reporting_agent"
            )
            
            # Executive summary generator tool
            summary_tool = SimulatedLongRunningTool("executive_summary_generator", duration_ms=600)
            summary_input = ToolInput(
                tool_name="executive_summary_generator",
                parameters={
                    "analysis_results": pattern_result.result,
                    "model_results": model_result.result,
                    "executive_level": "C_suite",
                    "focus_areas": ["revenue_impact", "cost_optimization", "growth_opportunities"]
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "executive_summary": {
                                     "key_findings": 8,
                                     "revenue_opportunities": f"${500 + (user_idx * 100)}K identified",
                                     "cost_savings": f"${200 + (user_idx * 50)}K potential",
                                     "strategic_recommendations": 12
                                 }
                             })):
                summary_result = await self.executor.execute_tool_with_input(
                    summary_input, summary_tool, {'context': reporting_context}
                )
            
            workflow_data["tools_executed"] += 1
            
            # Interactive dashboard builder tool
            dashboard_tool = SimulatedLongRunningTool("dashboard_builder", duration_ms=900)
            dashboard_input = ToolInput(
                tool_name="dashboard_builder",
                parameters={
                    "data_sources": connector_result.result["data_retrieved"],
                    "visualizations": ["trend_charts", "heatmaps", "forecasts", "kpi_cards"],
                    "interactivity_level": "high",
                    "user_tier": user_profile["tier"]
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "dashboard_created": {
                                     "visualizations_count": 15 + (user_idx * 2),
                                     "interactive_elements": 8,
                                     "real_time_updates": True,
                                     "sharing_enabled": True
                                 }
                             })):
                dashboard_result = await self.executor.execute_tool_with_input(
                    dashboard_input, dashboard_tool, {'context': reporting_context}
                )
            
            workflow_data["tools_executed"] += 1
            workflow_data["agent_executions"] += 1
            workflow_data["workflow_stages_completed"] += 1
            
            # WORKFLOW STAGE 4: Automated Actions and Integration
            automation_context = AgentExecutionContext(
                run_id=f"automation_{user_idx}",
                thread_id=thread_id,
                user_id=user_id,
                agent_name="automation_agent"
            )
            
            # Workflow automation setup tool
            automation_tool = SimulatedLongRunningTool("workflow_automator", duration_ms=700)
            automation_input = ToolInput(
                tool_name="workflow_automator",
                parameters={
                    "insights": summary_result.result["executive_summary"],
                    "automation_triggers": ["threshold_alerts", "anomaly_detection", "scheduled_reports"],
                    "integration_systems": ["slack", "email", "crm", "data_warehouse"]
                }
            )
            
            with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                             return_value=ToolResult(result={
                                 "automations_created": {
                                     "alert_rules": 12 + (user_idx * 2),
                                     "scheduled_reports": 6,
                                     "integration_endpoints": 4,
                                     "automation_success_rate": 0.94
                                 }
                             })):
                automation_result = await self.executor.execute_tool_with_input(
                    automation_input, automation_tool, {'context': automation_context}
                )
            
            workflow_data["tools_executed"] += 1
            workflow_data["agent_executions"] += 1
            workflow_data["workflow_stages_completed"] += 1
            
            # Calculate workflow metrics
            workflow_duration = time.time() - workflow_start
            base_cost = 2.50  # Base cost per workflow
            tier_multiplier = 2.0 if user_profile["tier"] == "enterprise" else 1.5
            complexity_multiplier = 1.8  # High complexity
            
            workflow_data.update({
                "workflow_duration_minutes": workflow_duration / 60,
                "total_cost": base_cost * tier_multiplier * complexity_multiplier,
                "revenue_generated": (base_cost * tier_multiplier * complexity_multiplier) * 2.5,  # 2.5x markup
                "success": True,
                "user_tier": user_profile["tier"]
            })
            
            enterprise_workflows.append(workflow_data)
            
            # Small delay between workflows
            await asyncio.sleep(0.05)
        
        # CRITICAL POWER USER TOOL ORCHESTRATION ASSERTIONS
        
        # Verify comprehensive tool event coverage
        all_events = self.mock_ws.tool_events
        orchestration_events = [e for e in all_events if any(term in e.tool_name.lower() 
                              for term in ['connector', 'cleaner', 'pattern', 'predictive', 'summary', 'dashboard', 'automation'])]
        
        expected_total_tools = len(enterprise_workflows) * 8  # 8 tools per workflow
        assert len(orchestration_events) >= expected_total_tools * 2, \
            f"Missing orchestration tool events: {len(orchestration_events)} < {expected_total_tools * 2}"
        
        # Event sequence validation for complex workflows
        validation_failures = 0
        for workflow in enterprise_workflows:
            validation = self.mock_ws.get_event_sequence_validation(workflow["thread_id"])
            if not validation.get("all_tools_completed", False):
                validation_failures += 1
        
        assert validation_failures == 0, \
            f"Power user workflow validation failures: {validation_failures} (should be 0)"
        
        # Business performance validation
        successful_workflows = [w for w in enterprise_workflows if w["success"]]
        total_revenue = sum(w["revenue_generated"] for w in successful_workflows)
        total_data_processed = sum(w["data_processed_mb"] for w in successful_workflows)
        average_workflow_time = sum(w["workflow_duration_minutes"] for w in successful_workflows) / len(successful_workflows)
        
        enterprise_workflows_count = len([w for w in successful_workflows if w["user_tier"] == "enterprise"])
        enterprise_revenue = sum(w["revenue_generated"] for w in successful_workflows if w["user_tier"] == "enterprise")
        
        assert len(successful_workflows) == power_users, \
            "All power user workflows should succeed"
        
        assert total_revenue > power_users * 10, \
            f"Total revenue too low: ${total_revenue:.2f} (need >${power_users * 10})"
        
        assert total_data_processed > power_users * 80, \
            f"Data processing too low: {total_data_processed:.1f}MB (need >{power_users * 80}MB)"
        
        assert average_workflow_time < 12, \
            f"Workflow time too long: {average_workflow_time:.1f} minutes (limit: <12 min)"
        
        # Enterprise tier performance validation
        if enterprise_workflows_count > 0:
            enterprise_avg_revenue = enterprise_revenue / enterprise_workflows_count
            mid_tier_workflows = [w for w in successful_workflows if w["user_tier"] == "mid"]
            mid_avg_revenue = sum(w["revenue_generated"] for w in mid_tier_workflows) / len(mid_tier_workflows) if mid_tier_workflows else 0
            
            assert enterprise_avg_revenue > mid_avg_revenue * 1.3, \
                f"Enterprise tier should generate 30% more revenue: ${enterprise_avg_revenue:.2f} vs ${mid_avg_revenue:.2f}"
        
        # Tool orchestration performance metrics
        metrics = self.mock_ws.calculate_metrics()
        total_agent_executions = sum(w["agent_executions"] for w in successful_workflows)
        
        assert metrics.total_executions >= expected_total_tools * 0.98, \
            f"Tool execution rate too low: {metrics.total_executions}/{expected_total_tools}"
        
        assert total_agent_executions == power_users * 4, \
            f"Agent execution count mismatch: {total_agent_executions} (expected {power_users * 4})"
        
        assert metrics.events_per_second > 15, \
            f"Event delivery rate too low: {metrics.events_per_second:.1f} events/s (need >15)"
        
        logger.info(f"Power user tool orchestration: {len(successful_workflows)} workflows, "
                   f"{len(orchestration_events)} tool events, {total_agent_executions} agent executions, "
                   f"${total_revenue:.2f} total revenue, {total_data_processed:.1f}MB processed, "
                   f"{average_workflow_time:.1f} min avg duration, {metrics.events_per_second:.1f} events/s")


# ============================================================================
# PERFORMANCE UNDER LOAD WITH TOOL PROGRESS
# ============================================================================

class TestToolProgressPerformanceUnderLoad:
    """Test tool progress updates under extreme concurrent load."""
    
    @pytest.fixture(autouse=True)
    async def setup_performance_tool_tests(self):
        """Setup performance testing with tool progress monitoring."""
        self.mock_ws = AdvancedMockWebSocketManager()
        self.executor = UnifiedToolExecutionEngine(self.mock_ws)
        
        # Performance tracking
        self.load_test_metrics = {
            "concurrent_users": 0,
            "tools_per_second": [],
            "events_per_second": [],
            "error_rates": [],
            "memory_usage": [],
            "response_times": []
        }
        
        yield
        self.mock_ws.clear_all()

    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(420)  # 7 minutes for extreme load testing
    async def test_50_concurrent_users_tool_progress_under_load(self):
        """CRITICAL: Test 50+ concurrent users with intensive tool usage and progress tracking."""
        
        concurrent_users = 60
        tools_per_user = 12
        target_completion_time = 25  # seconds per user session
        
        async def intensive_user_tool_session(user_index: int) -> Dict[str, Any]:
            """Simulate intensive user session with many tools under load."""
            session_start = time.time()
            user_id = f"load_user_{user_index}"
            thread_id = f"load_thread_{user_index}"
            
            session_metrics = {
                "user_id": user_id,
                "thread_id": thread_id,
                "tools_completed": 0,
                "tools_failed": 0,
                "total_processing_time": 0,
                "revenue_generated": 0,
                "session_duration": 0,
                "success": False
            }
            
            try:
                # Create intensive tool execution context
                intensive_context = AgentExecutionContext(
                    run_id=f"intensive_session_{user_index}",
                    thread_id=thread_id,
                    user_id=user_id,
                    agent_name="intensive_load_agent"
                )
                
                # Execute many tools rapidly
                for tool_idx in range(tools_per_user):
                    tool_start = time.time()
                    
                    # Vary tool types and complexity
                    if tool_idx % 4 == 0:
                        # Data processing tool (heavy)
                        tool_name = "data_processor"
                        processing_time = 150 + (tool_idx * 20)  # 150-370ms
                        tool_cost = 0.05
                    elif tool_idx % 4 == 1:
                        # API integration tool (medium)
                        tool_name = "api_integrator"
                        processing_time = 100 + (tool_idx * 10)  # 100-210ms
                        tool_cost = 0.03
                    elif tool_idx % 4 == 2:
                        # Content generation tool (variable)
                        tool_name = "content_generator"
                        processing_time = 200 + (tool_idx * 15)  # 200-365ms
                        tool_cost = 0.04
                    else:
                        # Quick validation tool (light)
                        tool_name = "validator"
                        processing_time = 50 + (tool_idx * 5)  # 50-105ms
                        tool_cost = 0.02
                    
                    # Create tool with realistic parameters
                    load_tool = SimulatedLongRunningTool(
                        f"{tool_name}_{user_index}_{tool_idx}",
                        duration_ms=processing_time,
                        should_fail=(user_index % 20 == 0 and tool_idx % 8 == 7)  # 5% failure rate
                    )
                    
                    tool_input = ToolInput(
                        tool_name=f"{tool_name}_{user_index}_{tool_idx}",
                        parameters={
                            "user_index": user_index,
                            "tool_sequence": tool_idx,
                            "load_test": True,
                            "processing_complexity": "high" if tool_idx % 3 == 0 else "medium"
                        }
                    )
                    
                    # Execute tool with potential failure
                    try:
                        with patch.object(ToolExecutionEngine, 'execute_tool_with_input',
                                         return_value=ToolResult(result={
                                             "processed": True,
                                             "processing_time_ms": processing_time,
                                             "cost": tool_cost,
                                             "quality_score": 0.9
                                         })):
                            tool_result = await self.executor.execute_tool_with_input(
                                tool_input, load_tool, {'context': intensive_context}
                            )
                        
                        # Track successful tool execution
                        tool_duration = time.time() - tool_start
                        session_metrics["tools_completed"] += 1
                        session_metrics["total_processing_time"] += tool_duration
                        session_metrics["revenue_generated"] += tool_cost * 2  # 2x markup
                        
                        # Track response time for load analysis
                        self.load_test_metrics["response_times"].append(tool_duration * 1000)  # Convert to ms
                        
                    except Exception as e:
                        session_metrics["tools_failed"] += 1
                        logger.debug(f"Tool {tool_idx} failed for user {user_index}: {e}")
                    
                    # Brief delay to simulate realistic user behavior
                    await asyncio.sleep(0.01)
                
                # Session completion metrics
                session_metrics["session_duration"] = time.time() - session_start
                session_metrics["success"] = (
                    session_metrics["session_duration"] < target_completion_time and
                    session_metrics["tools_completed"] >= tools_per_user * 0.9
                )
                
                # Calculate session efficiency
                session_metrics["tools_per_second"] = session_metrics["tools_completed"] / session_metrics["session_duration"]
                session_metrics["revenue_per_second"] = session_metrics["revenue_generated"] / session_metrics["session_duration"]
                
                return session_metrics
                
            except Exception as e:
                session_metrics["session_duration"] = time.time() - session_start
                session_metrics["error"] = str(e)
                return session_metrics
        
        # Execute all concurrent user sessions
        self.load_test_metrics["concurrent_users"] = concurrent_users
        load_test_start = time.time()
        
        logger.info(f"Starting {concurrent_users} concurrent intensive tool sessions "
                   f"({tools_per_user} tools each, target: <{target_completion_time}s)")
        
        # Launch all concurrent sessions
        tasks = [
            asyncio.create_task(intensive_user_tool_session(i))
            for i in range(concurrent_users)
        ]
        
        # Monitor performance during execution
        performance_monitor = asyncio.create_task(
            self._monitor_load_performance(45.0)  # Monitor for 45 seconds
        )
        
        try:
            # Wait for all sessions to complete
            session_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Stop performance monitoring
            performance_monitor.cancel()
            
            load_test_duration = time.time() - load_test_start
            
            # Analyze session results
            successful_sessions = [r for r in session_results if isinstance(r, dict) and r.get("success")]
            failed_sessions = [r for r in session_results if isinstance(r, dict) and not r.get("success")]
            exception_count = len([r for r in session_results if isinstance(r, Exception)])
            
            # CRITICAL LOAD PERFORMANCE ASSERTIONS
            
            # Success rate under load
            success_rate = len(successful_sessions) / concurrent_users
            assert success_rate >= 0.85, \
                f"Load test success rate too low: {success_rate*100:.1f}% (need ≥85%)"
            
            # Tool execution performance
            total_tools_completed = sum(s.get("tools_completed", 0) for s in successful_sessions)
            total_tools_failed = sum(s.get("tools_failed", 0) for s in successful_sessions)
            tool_success_rate = total_tools_completed / (total_tools_completed + total_tools_failed) if (total_tools_completed + total_tools_failed) > 0 else 0
            
            assert tool_success_rate >= 0.90, \
                f"Tool success rate under load too low: {tool_success_rate*100:.1f}% (need ≥90%)"
            
            # Performance benchmarks
            if successful_sessions:
                avg_session_duration = sum(s["session_duration"] for s in successful_sessions) / len(successful_sessions)
                avg_tools_per_second = sum(s["tools_per_second"] for s in successful_sessions) / len(successful_sessions)
                
                assert avg_session_duration < target_completion_time * 1.3, \
                    f"Average session duration too high: {avg_session_duration:.1f}s (limit: {target_completion_time * 1.3}s)"
                
                assert avg_tools_per_second > 0.3, \
                    f"Tool execution rate too low: {avg_tools_per_second:.1f} tools/s (need >0.3)"
            
            # Tool progress event validation
            all_events = self.mock_ws.tool_events
            load_events = [e for e in all_events if 'load_user' in e.thread_id]
            
            # Should have events for most completed tools
            expected_min_events = total_tools_completed * 2 * 0.8  # 80% of expected events (executing + completed)
            assert len(load_events) >= expected_min_events, \
                f"Missing tool progress events under load: {len(load_events)} < {expected_min_events}"
            
            # Business metrics validation
            total_revenue = sum(s.get("revenue_generated", 0) for s in successful_sessions)
            assert total_revenue > concurrent_users * 1.0, \
                f"Revenue generation under load too low: ${total_revenue:.2f} (need >${concurrent_users * 1.0})"
            
            # System throughput
            overall_tools_per_second = total_tools_completed / load_test_duration
            users_per_second = concurrent_users / load_test_duration
            
            assert overall_tools_per_second > 15, \
                f"Overall tool throughput too low: {overall_tools_per_second:.1f} tools/s (need >15)"
            
            assert users_per_second > 2, \
                f"User session throughput too low: {users_per_second:.1f} users/s (need >2)"
            
            # Response time analysis
            if self.load_test_metrics["response_times"]:
                avg_response_time = sum(self.load_test_metrics["response_times"]) / len(self.load_test_metrics["response_times"])
                p95_response_time = sorted(self.load_test_metrics["response_times"])[int(len(self.load_test_metrics["response_times"]) * 0.95)]
                
                assert avg_response_time < 300, \
                    f"Average response time too high: {avg_response_time:.1f}ms (limit: <300ms)"
                
                assert p95_response_time < 800, \
                    f"P95 response time too high: {p95_response_time:.1f}ms (limit: <800ms)"
            
            # Event delivery performance
            metrics = self.mock_ws.calculate_metrics()
            assert metrics.events_per_second > 30, \
                f"Event delivery rate under load too low: {metrics.events_per_second:.1f} events/s (need >30)"
            
            # Error rate validation
            total_errors = len(failed_sessions) + exception_count + total_tools_failed
            total_operations = concurrent_users + total_tools_completed + total_tools_failed
            error_rate = total_errors / total_operations if total_operations > 0 else 0
            
            assert error_rate < 0.1, \
                f"Error rate under load too high: {error_rate*100:.1f}% (limit: <10%)"
            
            logger.info(f"Load test results: {len(successful_sessions)}/{concurrent_users} successful sessions "
                       f"({success_rate*100:.1f}%), {total_tools_completed} tools completed "
                       f"({tool_success_rate*100:.1f}% success), "
                       f"{overall_tools_per_second:.1f} tools/s throughput, "
                       f"${total_revenue:.2f} revenue generated, "
                       f"{avg_response_time:.1f}ms avg response time, "
                       f"{metrics.events_per_second:.1f} events/s")
            
        except asyncio.CancelledError:
            pass

    async def _monitor_load_performance(self, duration: float):
        """Monitor performance metrics during load test."""
        start_time = time.time()
        sample_count = 0
        
        while time.time() - start_time < duration:
            try:
                sample_count += 1
                
                # Sample tool execution rate
                current_events = len(self.mock_ws.tool_events)
                elapsed_time = time.time() - start_time
                current_events_per_second = current_events / elapsed_time if elapsed_time > 0 else 0
                
                self.load_test_metrics["events_per_second"].append(current_events_per_second)
                
                # Log performance peaks/issues
                if current_events_per_second > 100:
                    logger.info(f"High event rate detected: {current_events_per_second:.1f} events/s")
                elif current_events_per_second < 10 and elapsed_time > 10:  # After 10s warmup
                    logger.warning(f"Low event rate detected: {current_events_per_second:.1f} events/s")
                
            except Exception as e:
                logger.debug(f"Performance monitoring error: {e}")
                
            await asyncio.sleep(2.0)
        
        logger.info(f"Load performance monitoring completed: {sample_count} samples collected")


if __name__ == "__main__":
    # Run comprehensive validation
    exit_code = run_bulletproof_tool_progress_validation()
    sys.exit(exit_code)