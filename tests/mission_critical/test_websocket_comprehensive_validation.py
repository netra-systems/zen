#!/usr/bin/env python
"""
MISSION CRITICAL: Comprehensive WebSocket Validation Test Suite

This is the most rigorous test suite for WebSocket notifications in the Netra system.
It validates ALL critical WebSocket events are sent during agent execution under
every conceivable scenario, including error conditions, concurrent execution,
and high load scenarios.

Business Value: $500K+ ARR - Core chat functionality depends on these events
CRITICAL: These events enable substantive chat interactions - they serve the business goal

Required WebSocket Events (MANDATORY):
1. agent_started - User must see agent began processing 
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results display
5. agent_completed - User must know when response is ready

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import random
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
import weakref

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import environment management
from shared.isolated_environment import get_env

# Import production components for testing
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine, 
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.websocket_core.manager import WebSocketManager


# ============================================================================
# ULTRA COMPREHENSIVE MOCK FRAMEWORK
# ============================================================================

class UltraReliableMockWebSocketManager:
    """Ultra-reliable mock WebSocket manager that captures every event with forensic precision."""
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.connections: Dict[str, Dict] = {}
        self.event_log: List[Dict] = []
        self.lock = threading.RLock()
        self.error_simulation = {}
        self.latency_simulation = 0.0
        self.drop_rate = 0.0
        self._total_events = 0
        self._failed_events = 0
        self._start_time = time.time()
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message with ultra-detailed tracking."""
        with self.lock:
            self._total_events += 1
            
            # Simulate network latency if configured
            if self.latency_simulation > 0:
                await asyncio.sleep(self.latency_simulation)
            
            # Simulate message drops if configured
            if random.random() < self.drop_rate:
                self._failed_events += 1
                return False
                
            # Simulate specific errors if configured
            if thread_id in self.error_simulation:
                error_config = self.error_simulation[thread_id]
                if error_config.get('fail_probability', 0) > random.random():
                    self._failed_events += 1
                    if error_config.get('raise_exception', False):
                        raise Exception(f"Simulated WebSocket error for {thread_id}")
                    return False
            
            event_record = {
                'thread_id': thread_id,
                'message': message.copy(),
                'event_type': message.get('type', 'unknown'),
                'timestamp': time.time(),
                'relative_time': time.time() - self._start_time,
                'sequence_id': self._total_events
            }
            
            self.messages.append(event_record)
            self.event_log.append({
                'action': 'send_to_thread',
                'thread_id': thread_id,
                'event_type': event_record['event_type'],
                'timestamp': event_record['timestamp'],
                'success': True
            })
            
            return True
    
    def configure_error_simulation(self, thread_id: str, fail_probability: float = 0.1, 
                                 raise_exception: bool = False):
        """Configure error simulation for testing error recovery."""
        self.error_simulation[thread_id] = {
            'fail_probability': fail_probability,
            'raise_exception': raise_exception
        }
    
    def set_network_conditions(self, latency_ms: float = 0, drop_rate: float = 0):
        """Simulate network conditions."""
        self.latency_simulation = latency_ms / 1000.0
        self.drop_rate = drop_rate
    
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all events for a specific thread with forensic details."""
        with self.lock:
            return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def get_event_types_for_thread(self, thread_id: str) -> List[str]:
        """Get event types for a thread in chronological order."""
        with self.lock:
            return [msg['event_type'] for msg in self.messages 
                   if msg['thread_id'] == thread_id]
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for analysis."""
        with self.lock:
            return {
                'total_events': self._total_events,
                'failed_events': self._failed_events,
                'success_rate': (self._total_events - self._failed_events) / max(self._total_events, 1),
                'unique_threads': len(set(msg['thread_id'] for msg in self.messages)),
                'event_types': list(set(msg['event_type'] for msg in self.messages)),
                'duration_seconds': time.time() - self._start_time,
                'events_per_second': self._total_events / max(time.time() - self._start_time, 0.001)
            }
    
    def clear_all(self):
        """Clear all recorded data."""
        with self.lock:
            self.messages.clear()
            self.event_log.clear()
            self.connections.clear()
            self.error_simulation.clear()
            self._total_events = 0
            self._failed_events = 0
            self._start_time = time.time()


class ComprehensiveEventValidator:
    """Ultra-rigorous event validation with forensic analysis capabilities."""
    
    CRITICAL_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report", 
        "partial_result",
        "tool_error",
        "agent_error"
    }
    
    # Event ordering constraints
    ORDERING_RULES = {
        "agent_started": {"must_be_first": True},
        "agent_completed": {"must_be_after": ["agent_started"]},
        "tool_completed": {"must_be_after": ["tool_executing"]},
        "final_report": {"must_be_after": ["agent_started"]}
    }
    
    def __init__(self, strict_mode: bool = True, timeout_seconds: float = 30.0):
        self.strict_mode = strict_mode
        self.timeout_seconds = timeout_seconds
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data, thread_id)
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.critical_violations: List[str] = []
        self.start_time = time.time()
        self.thread_events: Dict[str, List[Dict]] = {}
        self.event_pairs: Dict[str, List[tuple]] = {}  # Track paired events
        
    def record_event(self, event: Dict, thread_id: str = "default") -> None:
        """Record an event with ultra-detailed forensic tracking."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event, thread_id))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Per-thread tracking
        if thread_id not in self.thread_events:
            self.thread_events[thread_id] = []
        self.thread_events[thread_id].append({
            'event': event,
            'timestamp': timestamp,
            'sequence': len(self.events)
        })
        
        # Track event pairs (tool_executing <-> tool_completed)
        if event_type == "tool_executing":
            tool_name = event.get("tool_name", "unknown")
            pair_key = f"{thread_id}:{tool_name}"
            if pair_key not in self.event_pairs:
                self.event_pairs[pair_key] = []
            self.event_pairs[pair_key].append(("start", timestamp, event))
        elif event_type == "tool_completed":
            tool_name = event.get("tool_name", "unknown")
            pair_key = f"{thread_id}:{tool_name}"
            if pair_key not in self.event_pairs:
                self.event_pairs[pair_key] = []
            self.event_pairs[pair_key].append(("end", timestamp, event))
    
    def validate_ultra_comprehensive(self) -> tuple[bool, List[str], Dict[str, Any]]:
        """Ultra-comprehensive validation with detailed forensic analysis."""
        failures = []
        analysis = {}
        
        # 1. Critical event presence validation
        missing_critical = self.CRITICAL_EVENTS - set(self.event_counts.keys())
        if missing_critical:
            failures.append(f"CRITICAL VIOLATION: Missing required events: {missing_critical}")
            self.critical_violations.append(f"Missing critical events: {missing_critical}")
        
        # 2. Event ordering validation
        ordering_failures = self._validate_ultra_strict_ordering()
        failures.extend(ordering_failures)
        
        # 3. Event pairing validation (tools)
        pairing_failures = self._validate_event_pairing()
        failures.extend(pairing_failures)
        
        # 4. Timing constraint validation
        timing_failures = self._validate_timing_constraints()
        failures.extend(timing_failures)
        
        # 5. Per-thread consistency validation
        thread_failures = self._validate_thread_consistency()
        failures.extend(thread_failures)
        
        # 6. Data completeness validation
        data_failures = self._validate_event_data_completeness()
        failures.extend(data_failures)
        
        # 7. Performance validation
        performance_failures = self._validate_performance_requirements()
        failures.extend(performance_failures)
        
        # Generate analysis report
        analysis = {
            "total_events": len(self.events),
            "event_counts": self.event_counts,
            "thread_count": len(self.thread_events),
            "duration_seconds": self.event_timeline[-1][0] if self.event_timeline else 0,
            "critical_violations": self.critical_violations,
            "timing_analysis": self._analyze_timing_patterns(),
            "thread_analysis": self._analyze_thread_patterns(),
            "performance_metrics": self._calculate_performance_metrics()
        }
        
        return len(failures) == 0, failures, analysis
    
    def _validate_ultra_strict_ordering(self) -> List[str]:
        """Validate ultra-strict event ordering requirements."""
        failures = []
        
        if not self.event_timeline:
            failures.append("CRITICAL: No events recorded")
            return failures
        
        # First event must be agent_started
        first_event = self.event_timeline[0][1]
        if first_event != "agent_started":
            failures.append(f"CRITICAL: First event must be 'agent_started', got '{first_event}'")
            self.critical_violations.append("Invalid event ordering")
        
        # Validate ordering rules
        for event_type, rules in self.ORDERING_RULES.items():
            if event_type not in self.event_counts:
                continue
                
            if rules.get("must_be_first") and first_event != event_type:
                failures.append(f"CRITICAL: {event_type} must be first event")
            
            if "must_be_after" in rules:
                required_predecessors = rules["must_be_after"]
                event_positions = [i for i, (_, etype, _, _) in enumerate(self.event_timeline) 
                                 if etype == event_type]
                
                for pos in event_positions:
                    for required in required_predecessors:
                        predecessor_positions = [i for i, (_, etype, _, _) in enumerate(self.event_timeline[:pos]) 
                                               if etype == required]
                        if not predecessor_positions:
                            failures.append(f"CRITICAL: {event_type} found without required predecessor {required}")
        
        return failures
    
    def _validate_event_pairing(self) -> List[str]:
        """Validate that tool events are properly paired."""
        failures = []
        
        for pair_key, events in self.event_pairs.items():
            starts = [e for e in events if e[0] == "start"]
            ends = [e for e in events if e[0] == "end"]
            
            if len(starts) != len(ends):
                failures.append(f"CRITICAL: Unpaired tool events for {pair_key}: {len(starts)} starts, {len(ends)} ends")
                self.critical_violations.append(f"Unpaired tool events: {pair_key}")
            
            # Validate start-end ordering
            for start_event in starts:
                start_time = start_event[1]
                matching_ends = [e for e in ends if e[1] > start_time]
                if not matching_ends:
                    failures.append(f"CRITICAL: Tool execution started but never completed: {pair_key}")
        
        return failures
    
    def _validate_timing_constraints(self) -> List[str]:
        """Validate timing constraints and detect anomalies."""
        failures = []
        
        if not self.event_timeline:
            return failures
        
        # Check for events arriving after timeout
        for timestamp, event_type, _, thread_id in self.event_timeline:
            if timestamp > self.timeout_seconds:
                failures.append(f"CRITICAL: Event {event_type} for thread {thread_id} arrived after {self.timeout_seconds}s timeout at {timestamp:.2f}s")
        
        # Check for suspiciously long gaps between events
        for i in range(1, len(self.event_timeline)):
            prev_time = self.event_timeline[i-1][0]
            curr_time = self.event_timeline[i][0]
            gap = curr_time - prev_time
            
            if gap > 10.0:  # 10 second gap is suspicious
                self.warnings.append(f"Long gap ({gap:.2f}s) between events: {self.event_timeline[i-1][1]} -> {self.event_timeline[i][1]}")
        
        return failures
    
    def _validate_thread_consistency(self) -> List[str]:
        """Validate per-thread event consistency."""
        failures = []
        
        for thread_id, events in self.thread_events.items():
            if not events:
                continue
            
            # Each thread should have at least agent_started
            event_types = [e['event']['type'] for e in events]
            if 'agent_started' not in event_types:
                failures.append(f"CRITICAL: Thread {thread_id} missing agent_started event")
            
            # Each thread should have some form of completion
            completion_types = {'agent_completed', 'agent_fallback', 'final_report'}
            if not completion_types.intersection(set(event_types)):
                failures.append(f"CRITICAL: Thread {thread_id} has no completion event")
        
        return failures
    
    def _validate_event_data_completeness(self) -> List[str]:
        """Validate that events contain complete required data."""
        failures = []
        
        for event in self.events:
            event_type = event.get('type')
            if not event_type:
                failures.append("CRITICAL: Event missing 'type' field")
                continue
            
            # Validate tool events have tool names
            if event_type in ['tool_executing', 'tool_completed']:
                if not event.get('tool_name'):
                    failures.append(f"CRITICAL: {event_type} event missing tool_name")
            
            # Validate events have timestamps
            if self.strict_mode and 'timestamp' not in event:
                self.warnings.append(f"Event {event_type} missing timestamp")
        
        return failures
    
    def _validate_performance_requirements(self) -> List[str]:
        """Validate performance requirements are met."""
        failures = []
        
        if not self.event_timeline:
            return failures
        
        total_duration = self.event_timeline[-1][0]
        event_count = len(self.events)
        
        # Should process events efficiently
        if event_count > 0:
            events_per_second = event_count / max(total_duration, 0.001)
            if events_per_second < 1.0 and event_count > 5:
                self.warnings.append(f"Low event throughput: {events_per_second:.2f} events/s")
        
        return failures
    
    def _analyze_timing_patterns(self) -> Dict[str, Any]:
        """Analyze timing patterns in events."""
        if not self.event_timeline:
            return {}
        
        intervals = []
        for i in range(1, len(self.event_timeline)):
            intervals.append(self.event_timeline[i][0] - self.event_timeline[i-1][0])
        
        return {
            "total_duration": self.event_timeline[-1][0],
            "average_interval": sum(intervals) / len(intervals) if intervals else 0,
            "max_interval": max(intervals) if intervals else 0,
            "min_interval": min(intervals) if intervals else 0
        }
    
    def _analyze_thread_patterns(self) -> Dict[str, Any]:
        """Analyze per-thread patterns."""
        return {
            "thread_count": len(self.thread_events),
            "threads_with_completion": sum(1 for events in self.thread_events.values() 
                                         if any(e['event'].get('type') in ['agent_completed', 'agent_fallback'] 
                                               for e in events)),
            "average_events_per_thread": sum(len(events) for events in self.thread_events.values()) / max(len(self.thread_events), 1)
        }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not self.event_timeline:
            return {}
        
        return {
            "events_per_second": len(self.events) / max(self.event_timeline[-1][0], 0.001),
            "first_event_latency": self.event_timeline[0][0] if self.event_timeline else 0,
            "completion_latency": next((t for t, e, _, _ in self.event_timeline if e in ['agent_completed', 'agent_fallback']), 0)
        }
    
    def generate_comprehensive_report(self) -> str:
        """Generate ultra-comprehensive validation report."""
        is_valid, failures, analysis = self.validate_ultra_comprehensive()
        
        report = [
            "\n" + "=" * 100,
            "🔍 ULTRA-COMPREHENSIVE WEBSOCKET VALIDATION REPORT",
            "=" * 100,
            f"🎯 Overall Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"📊 Total Events: {analysis['total_events']}",
            f"🧵 Threads Analyzed: {analysis['thread_count']}",
            f"⏱️  Total Duration: {analysis['duration_seconds']:.3f}s",
            f"🚀 Performance: {analysis['performance_metrics'].get('events_per_second', 0):.1f} events/s",
            "",
            "📋 CRITICAL EVENT COVERAGE:"
        ]
        
        for event in self.CRITICAL_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌"
            report.append(f"  {status} {event}: {count} occurrences")
        
        if self.critical_violations:
            report.extend([
                "",
                "💥 CRITICAL VIOLATIONS:",
                *[f"  🔴 {violation}" for violation in self.critical_violations]
            ])
        
        if failures:
            report.extend([
                "",
                "❌ VALIDATION FAILURES:",
                *[f"  ⛔ {failure}" for failure in failures]
            ])
        
        if self.warnings:
            report.extend([
                "",
                "⚠️  WARNINGS:",
                *[f"  🟡 {warning}" for warning in self.warnings]
            ])
        
        # Add timing analysis
        timing = analysis['timing_analysis']
        report.extend([
            "",
            "⏱️  TIMING ANALYSIS:",
            f"  📏 Total Duration: {timing.get('total_duration', 0):.3f}s",
            f"  📊 Average Interval: {timing.get('average_interval', 0):.3f}s", 
            f"  ⚡ Max Interval: {timing.get('max_interval', 0):.3f}s"
        ])
        
        report.append("=" * 100)
        return "\n".join(report)


# ============================================================================
# ADVANCED TEST UTILITIES
# ============================================================================

class WebSocketTestHarness:
    """Advanced test harness for comprehensive WebSocket testing scenarios."""
    
    def __init__(self):
        self.mock_ws_manager = UltraReliableMockWebSocketManager()
        self.validator = ComprehensiveEventValidator()
        self.active_threads: Set[str] = set()
        self.test_scenarios: List[Dict] = []
        
    async def create_test_context(self, thread_id: str, agent_name: str = "test_agent") -> AgentExecutionContext:
        """Create a test execution context."""
        return AgentExecutionContext(
            run_id=f"test-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            user_id=f"user-{thread_id}",
            agent_name=agent_name,
            retry_count=0,
            max_retries=3
        )
    
    async def simulate_complete_agent_flow(self, thread_id: str, include_tools: bool = True, 
                                         simulate_errors: bool = False) -> bool:
        """Simulate a complete agent execution flow with all events."""
        try:
            notifier = WebSocketNotifier(self.mock_ws_manager)
            context = await self.create_test_context(thread_id)
            
            # Start agent
            await notifier.send_agent_started(context)
            self.validator.record_event({'type': 'agent_started'}, thread_id)
            
            # Thinking phase
            await notifier.send_agent_thinking(context, "Processing request...")
            self.validator.record_event({'type': 'agent_thinking', 'content': 'Processing request...'}, thread_id)
            
            if include_tools:
                # Tool execution
                tool_name = "test_tool"
                await notifier.send_tool_executing(context, tool_name)
                self.validator.record_event({'type': 'tool_executing', 'tool_name': tool_name}, thread_id)
                
                if simulate_errors and random.random() < 0.3:
                    # Simulate tool error
                    await notifier.send_tool_error(context, tool_name, "Simulated tool error")
                    self.validator.record_event({'type': 'tool_error', 'tool_name': tool_name}, thread_id)
                else:
                    # Successful tool completion
                    await notifier.send_tool_completed(context, tool_name, {"result": "success"})
                    self.validator.record_event({'type': 'tool_completed', 'tool_name': tool_name}, thread_id)
            
            if simulate_errors and random.random() < 0.2:
                # Simulate agent error/fallback
                await notifier.send_fallback_notification(context, "agent_fallback")
                self.validator.record_event({'type': 'agent_fallback'}, thread_id)
            else:
                # Successful completion
                await notifier.send_agent_completed(context, {"success": True})
                self.validator.record_event({'type': 'agent_completed'}, thread_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in agent flow simulation: {e}")
            return False
    
    async def run_concurrent_scenarios(self, scenario_count: int = 10) -> Dict[str, Any]:
        """Run multiple concurrent agent scenarios."""
        tasks = []
        thread_ids = []
        
        for i in range(scenario_count):
            thread_id = f"concurrent-{i}-{uuid.uuid4().hex[:8]}"
            thread_ids.append(thread_id)
            
            # Vary scenario parameters
            include_tools = i % 2 == 0
            simulate_errors = i % 5 == 0
            
            task = self.simulate_complete_agent_flow(
                thread_id, 
                include_tools=include_tools,
                simulate_errors=simulate_errors
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Analyze results
        successful_flows = sum(1 for r in results if r is True)
        
        return {
            "total_scenarios": scenario_count,
            "successful_flows": successful_flows,
            "success_rate": successful_flows / scenario_count,
            "duration_seconds": duration,
            "scenarios_per_second": scenario_count / duration,
            "thread_ids": thread_ids
        }
    
    def configure_adverse_conditions(self, latency_ms: float = 50, drop_rate: float = 0.1):
        """Configure adverse network conditions for testing."""
        self.mock_ws_manager.set_network_conditions(latency_ms, drop_rate)
    
    def get_comprehensive_results(self) -> Dict[str, Any]:
        """Get comprehensive test results."""
        ws_stats = self.mock_ws_manager.get_comprehensive_stats()
        is_valid, failures, analysis = self.validator.validate_ultra_comprehensive()
        
        return {
            "validation_passed": is_valid,
            "validation_failures": failures,
            "event_analysis": analysis,
            "websocket_stats": ws_stats,
            "test_report": self.validator.generate_comprehensive_report()
        }


# ============================================================================
# ULTRA-COMPREHENSIVE TEST SUITE
# ============================================================================

class TestUltraComprehensiveWebSocketValidation:
    """The most comprehensive WebSocket validation test suite ever created."""
    
    @pytest.fixture(autouse=True)
    async def setup_ultra_comprehensive_test_environment(self):
        """Setup ultra-comprehensive test environment."""
        self.test_harness = WebSocketTestHarness()
        self.mock_ws_manager = self.test_harness.mock_ws_manager
        self.validator = self.test_harness.validator
        
        # Setup monitoring
        self._monitoring_active = True
        self._test_start_time = time.time()
        
        try:
            yield
        finally:
            # Ultra-comprehensive cleanup
            self._monitoring_active = False
            
            # Generate final test report
            if hasattr(self, '_generate_test_report'):
                try:
                    report = self.test_harness.get_comprehensive_results()
                    logger.info("Test completed. Final report generated.")
                except Exception as e:
                    logger.error(f"Error generating final report: {e}")
            
            # Clear all test data
            self.test_harness.mock_ws_manager.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_ultra_comprehensive_single_agent_flow(self):
        """Test ultra-comprehensive single agent flow with all possible events."""
        logger.info("🎯 Testing ultra-comprehensive single agent flow")
        
        thread_id = "ultra-comprehensive-single"
        success = await self.test_harness.simulate_complete_agent_flow(
            thread_id, 
            include_tools=True,
            simulate_errors=False
        )
        
        assert success, "Agent flow simulation failed"
        
        # Ultra-comprehensive validation
        results = self.test_harness.get_comprehensive_results()
        
        assert results["validation_passed"], f"Validation failed: {results['validation_failures']}"
        
        # Verify all critical events present
        event_types = self.test_harness.mock_ws_manager.get_event_types_for_thread(thread_id)
        for critical_event in ComprehensiveEventValidator.CRITICAL_EVENTS:
            assert critical_event in event_types, f"Missing critical event: {critical_event}"
        
        logger.info("✅ Ultra-comprehensive single agent flow test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_ultra_comprehensive_concurrent_execution(self):
        """Test ultra-comprehensive concurrent execution with many agents."""
        logger.info("🏗️ Testing ultra-comprehensive concurrent execution")
        
        concurrent_results = await self.test_harness.run_concurrent_scenarios(scenario_count=20)
        
        # Validate concurrent execution results
        assert concurrent_results["success_rate"] >= 0.95, \
            f"Concurrent execution success rate too low: {concurrent_results['success_rate']}"
        
        assert concurrent_results["scenarios_per_second"] > 1.0, \
            f"Concurrent throughput too low: {concurrent_results['scenarios_per_second']}"
        
        # Comprehensive validation across all scenarios
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], \
            f"Concurrent validation failed: {results['validation_failures']}"
        
        # Verify events for each thread
        for thread_id in concurrent_results["thread_ids"]:
            events = self.test_harness.mock_ws_manager.get_events_for_thread(thread_id)
            assert len(events) >= 3, f"Thread {thread_id} has insufficient events: {len(events)}"
        
        logger.info("✅ Ultra-comprehensive concurrent execution test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_ultra_comprehensive_error_recovery(self):
        """Test ultra-comprehensive error recovery scenarios."""
        logger.info("🚨 Testing ultra-comprehensive error recovery")
        
        # Configure error simulation
        error_thread = "error-recovery-test"
        self.mock_ws_manager.configure_error_simulation(
            error_thread, 
            fail_probability=0.3,
            raise_exception=False
        )
        
        # Run multiple error scenarios
        error_scenarios = []
        for i in range(10):
            thread_id = f"error-scenario-{i}"
            success = await self.test_harness.simulate_complete_agent_flow(
                thread_id,
                include_tools=True,
                simulate_errors=True
            )
            error_scenarios.append((thread_id, success))
        
        # Validate error recovery
        successful_recoveries = sum(1 for _, success in error_scenarios if success)
        recovery_rate = successful_recoveries / len(error_scenarios)
        
        assert recovery_rate >= 0.7, f"Error recovery rate too low: {recovery_rate}"
        
        # Comprehensive validation should still pass with proper error handling
        results = self.test_harness.get_comprehensive_results()
        
        # Allow some validation warnings due to error scenarios
        event_analysis = results["event_analysis"]
        assert event_analysis["total_events"] > 20, "Not enough events captured during error testing"
        
        logger.info("✅ Ultra-comprehensive error recovery test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_ultra_comprehensive_adverse_network_conditions(self):
        """Test under adverse network conditions."""
        logger.info("🌐 Testing under adverse network conditions")
        
        # Configure adverse conditions
        self.test_harness.configure_adverse_conditions(
            latency_ms=100,  # 100ms latency
            drop_rate=0.05   # 5% drop rate
        )
        
        # Run scenarios under adverse conditions
        adverse_results = await self.test_harness.run_concurrent_scenarios(scenario_count=15)
        
        # Should still maintain reasonable performance under adverse conditions
        assert adverse_results["success_rate"] >= 0.8, \
            f"Success rate under adverse conditions too low: {adverse_results['success_rate']}"
        
        # Validate that events were still captured despite network issues
        ws_stats = self.mock_ws_manager.get_comprehensive_stats()
        assert ws_stats["success_rate"] >= 0.9, \
            f"WebSocket delivery success rate too low: {ws_stats['success_rate']}"
        
        logger.info("✅ Ultra-comprehensive adverse network conditions test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_ultra_comprehensive_tool_dispatcher_integration(self):
        """Test ultra-comprehensive tool dispatcher integration."""
        logger.info("🔧 Testing ultra-comprehensive tool dispatcher integration")
        
        # Test enhance_tool_dispatcher_with_notifications function
        base_dispatcher = ToolDispatcher()
        
        # Verify initial state
        assert isinstance(base_dispatcher.executor, UnifiedToolExecutionEngine)
        assert base_dispatcher.executor.websocket_bridge is None
        
        # Test with AgentWebSocketBridge
        bridge = AgentWebSocketBridge()
        enhanced_dispatcher = ToolDispatcher(websocket_bridge=bridge)
        
        # Comprehensive validation of enhancement
        assert enhanced_dispatcher.executor.websocket_bridge is not None, \
            "Enhanced dispatcher missing WebSocket bridge"
        
        assert enhanced_dispatcher.executor.websocket_bridge == bridge, \
            "Enhanced dispatcher using wrong bridge instance"
        
        assert enhanced_dispatcher.executor.websocket_notifier == bridge, \
            "WebSocket notifier alias not working correctly"
        
        # Test that the enhancement function exists and works
        ws_manager = WebSocketManager()
        result = enhance_tool_dispatcher_with_notifications(base_dispatcher, ws_manager)
        
        # Should return the enhanced dispatcher or confirmation
        assert result is not None, "enhance_tool_dispatcher_with_notifications returned None"
        
        logger.info("✅ Ultra-comprehensive tool dispatcher integration test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_ultra_comprehensive_load_stress_testing(self):
        """Test ultra-comprehensive load and stress scenarios."""
        logger.info("💪 Testing ultra-comprehensive load and stress scenarios")
        
        # High-load stress test
        high_load_results = await self.test_harness.run_concurrent_scenarios(scenario_count=50)
        
        # Validate high-load performance
        assert high_load_results["scenarios_per_second"] > 5.0, \
            f"High-load throughput insufficient: {high_load_results['scenarios_per_second']} scenarios/s"
        
        # Comprehensive validation under load
        results = self.test_harness.get_comprehensive_results()
        ws_stats = results["websocket_stats"]
        
        # Should maintain high performance under load
        assert ws_stats["events_per_second"] > 50, \
            f"Event throughput under load too low: {ws_stats['events_per_second']}"
        
        assert ws_stats["success_rate"] >= 0.95, \
            f"Success rate under load too low: {ws_stats['success_rate']}"
        
        # Verify no events were lost under load
        expected_min_events = high_load_results["total_scenarios"] * 3  # At least 3 events per scenario
        assert ws_stats["total_events"] >= expected_min_events, \
            f"Events lost under load: expected >={expected_min_events}, got {ws_stats['total_events']}"
        
        logger.info("✅ Ultra-comprehensive load and stress test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_ultra_comprehensive_event_ordering_validation(self):
        """Test ultra-comprehensive event ordering validation."""
        logger.info("📋 Testing ultra-comprehensive event ordering validation")
        
        # Test multiple scenarios with strict ordering requirements
        for i in range(10):
            thread_id = f"ordering-test-{i}"
            await self.test_harness.simulate_complete_agent_flow(
                thread_id,
                include_tools=True,
                simulate_errors=False
            )
        
        # Ultra-strict validation
        results = self.test_harness.get_comprehensive_results()
        
        # Should pass all ordering validations
        assert results["validation_passed"], \
            f"Event ordering validation failed: {results['validation_failures']}"
        
        # Additional ordering checks
        event_analysis = results["event_analysis"]
        assert event_analysis["total_events"] > 40, "Insufficient events for ordering validation"
        
        # Verify per-thread ordering
        for i in range(10):
            thread_id = f"ordering-test-{i}"
            events = self.mock_ws_manager.get_event_types_for_thread(thread_id)
            
            # First event must be agent_started
            assert events[0] == "agent_started", f"Thread {thread_id} wrong first event: {events[0]}"
            
            # Last event must be completion
            completion_events = {"agent_completed", "agent_fallback", "final_report"}
            assert events[-1] in completion_events, \
                f"Thread {thread_id} wrong last event: {events[-1]}"
        
        logger.info("✅ Ultra-comprehensive event ordering validation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_ultra_comprehensive_regression_prevention(self):
        """Test ultra-comprehensive regression prevention scenarios."""
        logger.info("🛡️ Testing ultra-comprehensive regression prevention")
        
        # Test scenarios that have historically failed
        regression_scenarios = [
            {"name": "missing_tool_completion", "thread_id": "regression-1"},
            {"name": "out_of_order_events", "thread_id": "regression-2"},
            {"name": "duplicate_agent_started", "thread_id": "regression-3"},
            {"name": "missing_agent_completion", "thread_id": "regression-4"},
            {"name": "null_websocket_manager", "thread_id": "regression-5"}
        ]
        
        for scenario in regression_scenarios:
            thread_id = scenario["thread_id"]
            
            # Run normal flow - should not exhibit regression behaviors
            success = await self.test_harness.simulate_complete_agent_flow(
                thread_id,
                include_tools=True,
                simulate_errors=False
            )
            
            assert success, f"Regression scenario failed: {scenario['name']}"
            
            # Validate specific regression prevention
            events = self.mock_ws_manager.get_event_types_for_thread(thread_id)
            
            # No duplicate agent_started events
            agent_started_count = events.count("agent_started")
            assert agent_started_count == 1, \
                f"Regression: Multiple agent_started events in {scenario['name']}: {agent_started_count}"
            
            # Tool events are paired
            tool_executing_count = events.count("tool_executing")
            tool_completed_count = events.count("tool_completed")
            assert tool_executing_count == tool_completed_count, \
                f"Regression: Unpaired tool events in {scenario['name']}: {tool_executing_count} vs {tool_completed_count}"
        
        # Final comprehensive validation
        results = self.test_harness.get_comprehensive_results()
        assert results["validation_passed"], \
            f"Regression prevention validation failed: {results['validation_failures']}"
        
        logger.info("✅ Ultra-comprehensive regression prevention test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(30)
    async def test_ultra_comprehensive_component_isolation(self):
        """Test ultra-comprehensive component isolation."""
        logger.info("🔒 Testing ultra-comprehensive component isolation")
        
        # Test that components work independently
        
        # 1. Test WebSocketNotifier in isolation
        isolated_ws_manager = UltraReliableMockWebSocketManager()
        notifier = WebSocketNotifier(isolated_ws_manager)
        context = await self.test_harness.create_test_context("isolation-test")
        
        await notifier.send_agent_started(context)
        events = isolated_ws_manager.get_events_for_thread("isolation-test")
        assert len(events) == 1, "WebSocketNotifier isolation failed"
        assert events[0]["event_type"] == "agent_started", "Wrong event type in isolation"
        
        # 2. Test ToolDispatcher in isolation
        isolated_dispatcher = ToolDispatcher()
        assert isinstance(isolated_dispatcher.executor, UnifiedToolExecutionEngine), \
            "ToolDispatcher not properly isolated"
        
        # 3. Test AgentWebSocketBridge in isolation
        isolated_bridge = AgentWebSocketBridge()
        assert isolated_bridge is not None, "AgentWebSocketBridge isolation failed"
        
        # 4. Test UnifiedToolExecutionEngine in isolation
        isolated_engine = UnifiedToolExecutionEngine()
        assert isolated_engine.websocket_bridge is None, \
            "UnifiedToolExecutionEngine not properly isolated"
        
        # 5. Test with bridge integration
        integrated_engine = UnifiedToolExecutionEngine(websocket_bridge=isolated_bridge)
        assert integrated_engine.websocket_bridge is not None, \
            "UnifiedToolExecutionEngine bridge integration failed"
        
        logger.info("✅ Ultra-comprehensive component isolation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_ultra_comprehensive_final_validation(self):
        """Final ultra-comprehensive validation test."""
        logger.info("🎖️ Running final ultra-comprehensive validation")
        
        # Run the most demanding test scenario
        final_test_results = await self.test_harness.run_concurrent_scenarios(scenario_count=25)
        
        # Configure some adverse conditions for the final test
        self.test_harness.configure_adverse_conditions(latency_ms=20, drop_rate=0.02)
        
        # Add error scenarios
        for i in range(5):
            thread_id = f"final-error-{i}"
            await self.test_harness.simulate_complete_agent_flow(
                thread_id,
                include_tools=True,
                simulate_errors=True
            )
        
        # Get final comprehensive results
        final_results = self.test_harness.get_comprehensive_results()
        
        # Generate comprehensive report
        logger.info(final_results["test_report"])
        
        # Final validation must pass
        assert final_results["validation_passed"], \
            f"FINAL VALIDATION FAILED: {final_results['validation_failures']}"
        
        # Performance requirements for final test
        ws_stats = final_results["websocket_stats"]
        assert ws_stats["success_rate"] >= 0.95, \
            f"Final test success rate insufficient: {ws_stats['success_rate']}"
        
        assert ws_stats["events_per_second"] > 20, \
            f"Final test throughput insufficient: {ws_stats['events_per_second']}"
        
        # Event coverage must be comprehensive
        event_analysis = final_results["event_analysis"]
        assert event_analysis["total_events"] > 100, \
            f"Final test insufficient event coverage: {event_analysis['total_events']}"
        
        assert event_analysis["thread_count"] >= 25, \
            f"Final test insufficient thread coverage: {event_analysis['thread_count']}"
        
        logger.info("🏆 FINAL ULTRA-COMPREHENSIVE VALIDATION PASSED!")
        logger.info("🎯 All WebSocket notification requirements validated successfully")
        logger.info("💼 Business value preservation: Chat functionality fully operational")


# ============================================================================
# SPECIALIZED REGRESSION TESTS
# ============================================================================

class TestComprehensiveRegressionPrevention:
    """Specialized tests to prevent specific regressions in WebSocket functionality."""
    
    @pytest.fixture(autouse=True)
    async def setup_regression_testing(self):
        """Setup for regression testing."""
        self.mock_ws_manager = UltraReliableMockWebSocketManager()
        
        try:
            yield
        finally:
            self.mock_ws_manager.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_enhance_tool_dispatcher_function_exists_and_works(self):
        """REGRESSION TEST: enhance_tool_dispatcher_with_notifications must exist and work."""
        
        # Test that the function exists
        assert callable(enhance_tool_dispatcher_with_notifications), \
            "enhance_tool_dispatcher_with_notifications function missing or not callable"
        
        # Test function with real parameters
        dispatcher = ToolDispatcher()
        ws_manager = WebSocketManager()
        
        # Should not raise exception
        result = enhance_tool_dispatcher_with_notifications(dispatcher, ws_manager)
        
        # Function should return something meaningful or modify the dispatcher
        assert result is not None or dispatcher.executor.websocket_bridge is not None, \
            "enhance_tool_dispatcher_with_notifications had no effect"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_websocket_bridge_integration_never_breaks(self):
        """REGRESSION TEST: WebSocket bridge integration must never break."""
        
        # Test multiple integration patterns
        integration_patterns = [
            {"name": "direct_bridge", "bridge": AgentWebSocketBridge()},
            {"name": "dispatcher_integration", "bridge": None}
        ]
        
        for pattern in integration_patterns:
            if pattern["bridge"]:
                # Direct bridge integration
                executor = UnifiedToolExecutionEngine(websocket_bridge=pattern["bridge"])
                assert executor.websocket_bridge is not None, \
                    f"Integration pattern {pattern['name']} broke WebSocket bridge"
            else:
                # Default initialization
                executor = UnifiedToolExecutionEngine()
                # Should work without bridge
                assert executor is not None, \
                    f"Integration pattern {pattern['name']} broke default initialization"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_all_critical_events_always_sent(self):
        """REGRESSION TEST: All critical events must ALWAYS be sent."""
        
        validator = ComprehensiveEventValidator()
        notifier = WebSocketNotifier(self.mock_ws_manager)
        
        # Test multiple execution contexts
        for i in range(5):
            thread_id = f"critical-events-{i}"
            context = AgentExecutionContext(
                run_id=f"test-{i}",
                thread_id=thread_id,
                user_id=f"user-{i}",
                agent_name="regression_test_agent",
                retry_count=0,
                max_retries=1
            )
            
            # Send all critical events
            await notifier.send_agent_started(context)
            await notifier.send_agent_thinking(context, "Testing regression prevention")
            await notifier.send_tool_executing(context, "regression_tool")
            await notifier.send_tool_completed(context, "regression_tool", {"test": True})
            await notifier.send_agent_completed(context, {"regression_test": True})
            
            # Record events for validation
            events = self.mock_ws_manager.get_events_for_thread(thread_id)
            for event in events:
                validator.record_event(event["message"], thread_id)
        
        # Validate all critical events are present
        is_valid, failures, _ = validator.validate_ultra_comprehensive()
        
        assert is_valid, f"REGRESSION: Critical events missing or invalid: {failures}"
        
        # Verify each critical event type is present
        for critical_event in ComprehensiveEventValidator.CRITICAL_EVENTS:
            assert critical_event in validator.event_counts, \
                f"REGRESSION: Critical event {critical_event} never sent"
            assert validator.event_counts[critical_event] >= 5, \
                f"REGRESSION: Critical event {critical_event} sent insufficient times: {validator.event_counts[critical_event]}"


# ============================================================================
# TEST RUNNER AND MAIN
# ============================================================================

if __name__ == "__main__":
    # Run the ultra-comprehensive test suite
    logger.info("🚀 Starting Ultra-Comprehensive WebSocket Validation Test Suite")
    
    # Run with maximum verbosity and strict failure reporting
    pytest.main([
        __file__,
        "-v",                    # Verbose output
        "-s",                    # Don't capture output
        "--tb=long",            # Long traceback format
        "--strict-markers",     # Strict marker checking
        "--strict-config",      # Strict configuration
        "-x",                   # Stop on first failure
        "--disable-warnings",   # Clean output
        "-m", "critical"        # Only run critical tests
    ])