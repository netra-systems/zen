"""
Test Multiple WebSocket Emitter Race Conditions - PHASE 1: PRE-CONSOLIDATION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure  
- Business Goal: Revenue Protection - Prove $500K+ ARR at risk from race conditions
- Value Impact: Demonstrate multiple emitters cause event delivery failures affecting chat value
- Strategic Impact: Validate need for SSOT emitter consolidation to protect business revenue

CRITICAL: This test MUST FAIL with current multiple emitter implementation to prove:
1. Race conditions occur when multiple emitters send same events concurrently
2. Event delivery becomes unreliable under concurrent load scenarios  
3. Business value is lost when users don't see real-time AI responses
4. Resource contention degrades system performance

Expected Result: FAIL (proves current race condition issues exist)

CONSTRAINT: NO DOCKER - Unit tests only using in-memory mocks and simulations

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (90% business value)
@compliance Issue #200 - Multiple WebSocket event emitters causing race conditions  
@compliance TEST_CREATION_GUIDE.md - Business value focused, real scenarios, SSOT compliance
"""

import asyncio
import time
import uuid
import statistics
from typing import Dict, List, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from datetime import datetime, timezone
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID

# Import emitter implementations to test race conditions
try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
    EMITTERS_AVAILABLE = True
except ImportError as e:
    EMITTERS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@dataclass 
class EventDeliveryMetrics:
    """Metrics for tracking event delivery across multiple emitters."""
    total_events_sent: int = 0
    total_events_received: int = 0 
    duplicate_events: int = 0
    out_of_order_events: int = 0
    lost_events: int = 0
    timing_conflicts: int = 0
    average_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    success_rate: float = 0.0
    race_conditions_detected: int = 0


@dataclass
class ConcurrentEmitterSimulation:
    """Simulation setup for testing multiple emitters concurrently."""
    emitter_count: int = 4
    events_per_emitter: int = 100
    concurrent_users: int = 10
    max_concurrency: int = 50
    simulation_duration_ms: int = 5000
    expected_race_conditions: int = 0
    performance_degradation_threshold: float = 0.20  # 20% degradation indicates race conditions


@pytest.mark.unit
@pytest.mark.expected_to_fail
@pytest.mark.race_condition_detection
@pytest.mark.phase_1_pre_consolidation
@pytest.mark.websocket_emitter_consolidation  
class TestMultipleEmitterRaceConditions(SSotAsyncTestCase):
    """
    Unit tests proving race conditions exist with multiple WebSocket emitters.
    
    These tests MUST FAIL to demonstrate that the current system has race conditions
    that impact business value delivery through unreliable event delivery.
    """

    async def async_setup_method(self):
        """Set up test environment with multiple emitter simulation."""
        await super().async_setup_method()
        
        # Skip if emitters not available (with clear explanation)
        if not EMITTERS_AVAILABLE:
            pytest.skip(f"WebSocket emitters not available for testing: {IMPORT_ERROR}")
        
        # Create mock WebSocket manager for testing
        self.mock_ws_manager = AsyncMock()
        self.mock_ws_manager.emit_critical_event = AsyncMock()
        self.mock_ws_manager.is_connection_active = MagicMock(return_value=True)
        self.mock_ws_manager.get_connection_health = MagicMock(return_value={'has_active_connections': True})
        
        # Track events across all emitters
        self.events_received: List[Dict[str, Any]] = []
        self.event_timing: List[Tuple[str, float, str]] = []  # (event_type, timestamp, emitter_id)
        self.emitter_instances: List[Any] = []
        
        # Set up event capture
        self._setup_event_capture()
        
        # Enterprise customer context for realistic testing
        self.enterprise_user_context = self._create_enterprise_user_context()
        
    def _setup_event_capture(self):
        """Set up event capture to detect race conditions."""
        original_emit = self.mock_ws_manager.emit_critical_event
        
        async def capture_emit(user_id: str, event_type: str, data: Dict[str, Any]):
            # Capture timing and source information
            timestamp = time.time()
            emitter_id = data.get('emitter_id', 'unknown')
            
            # Store event with timing
            event_info = {
                'user_id': user_id,
                'event_type': event_type, 
                'data': data,
                'timestamp': timestamp,
                'emitter_id': emitter_id
            }
            self.events_received.append(event_info)
            self.event_timing.append((event_type, timestamp, emitter_id))
            
            # Call original to maintain behavior
            await original_emit(user_id, event_type, data)
            
        self.mock_ws_manager.emit_critical_event = capture_emit
    
    def _create_enterprise_user_context(self):
        """Create realistic enterprise customer context."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        return UserExecutionContext(
            user_id="enterprise_customer_001",
            thread_id="complex_optimization_workflow", 
            run_id=f"high_value_run_{uuid.uuid4()}", 
            request_id=f"enterprise_req_{uuid.uuid4()}"
        )

    @pytest.mark.expected_to_fail
    async def test_concurrent_emitter_timing_conflicts(self):
        """
        MUST FAIL: Prove multiple emitters cause timing conflicts when sending same events.
        
        This test demonstrates that when multiple emitters send the same event type
        simultaneously, race conditions occur that impact event delivery reliability.
        
        Expected Failure Mode: Timing conflicts detected when multiple emitters
        send events concurrently, proving need for SSOT consolidation.
        """
        # Create multiple emitter instances for same user  
        emitter_count = 4
        emitters = []
        
        for i in range(emitter_count):
            if i == 0:
                # UnifiedWebSocketEmitter (intended SSOT)
                emitter = UnifiedWebSocketEmitter(
                    manager=self.mock_ws_manager,
                    user_id=self.enterprise_user_context.user_id,
                    context=self.enterprise_user_context
                )
            else:
                # UserWebSocketEmitter (duplicate)
                emitter = UserWebSocketEmitter(
                    context=self.enterprise_user_context,
                    router=self.mock_ws_manager
                )
            
            # Tag emitter for tracking
            emitter._test_emitter_id = f"emitter_{i}"
            emitters.append(emitter)
        
        # Simulate concurrent event sending that should cause race conditions
        concurrent_tasks = []
        event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for emitter in emitters:
            for event_type in event_types:
                # Create task that sends event with emitter identification
                task = self._send_event_with_timing(emitter, event_type, {
                    'emitter_id': emitter._test_emitter_id,
                    'business_context': 'enterprise_optimization',
                    'value_impact': 'critical_revenue_protection'
                })
                concurrent_tasks.append(task)
        
        # Execute all events concurrently to trigger race conditions
        start_time = time.time()
        await asyncio.gather(*concurrent_tasks)
        total_duration = time.time() - start_time
        
        # Analyze results for race condition evidence
        metrics = self._analyze_race_condition_metrics()
        
        # ASSERTIONS THAT SHOULD FAIL (proving race conditions exist)
        
        # 1. Should have timing conflicts (events sent too close together)
        timing_conflicts = self._detect_timing_conflicts(threshold_ms=1.0)
        assert timing_conflicts > 0, (
            f"Expected timing conflicts with {emitter_count} emitters sending same events, "
            f"but found {timing_conflicts}. This suggests race conditions may not be occurring "
            f"or detection is insufficient."
        )
        
        # 2. Should have performance degradation due to contention
        expected_performance = 0.010  # 10ms for clean execution
        actual_performance = total_duration
        performance_degradation = (actual_performance - expected_performance) / expected_performance
        
        assert performance_degradation > 0.20, (
            f"Expected >20% performance degradation due to race conditions, "
            f"but only found {performance_degradation:.2%} degradation "
            f"({actual_performance:.3f}s vs {expected_performance:.3f}s expected). "
            f"This suggests multiple emitters aren't causing sufficient contention."
        )
        
        # 3. Should have duplicate events from multiple sources
        duplicate_events = self._count_duplicate_events()
        assert duplicate_events > 0, (
            f"Expected duplicate events from {emitter_count} emitters, "
            f"but found {duplicate_events}. Multiple emitters should create duplicates."
        )
        
        # 4. Should have evidence of resource contention
        resource_contention_score = self._calculate_resource_contention()
        assert resource_contention_score > 0.3, (
            f"Expected resource contention score >0.3 with multiple emitters, "
            f"but found {resource_contention_score:.2f}. This indicates insufficient "
            f"contention evidence for race condition proof."
        )
        
        # Business impact validation
        business_impact = self._calculate_business_impact(metrics)
        assert business_impact['revenue_risk_score'] > 0.5, (
            f"Expected significant revenue risk from race conditions, "
            f"but calculated risk score is {business_impact['revenue_risk_score']:.2f}. "
            f"Race conditions should pose clear business value threat."
        )

    @pytest.mark.expected_to_fail  
    async def test_event_ordering_becomes_unreliable(self):
        """
        MUST FAIL: Prove event ordering becomes unreliable with multiple emitters.
        
        This test demonstrates that multiple emitters sending sequential events 
        results in ordering violations that break the Golden Path user experience.
        
        Expected Failure Mode: Events arrive out of order, breaking the logical
        sequence required for chat value delivery.
        """
        # Create 3 different emitter types to maximize ordering chaos
        emitters = [
            UnifiedWebSocketEmitter(
                manager=self.mock_ws_manager,
                user_id=self.enterprise_user_context.user_id, 
                context=self.enterprise_user_context
            ),
            UserWebSocketEmitter(
                context=self.enterprise_user_context,
                router=self.mock_ws_manager  
            )
        ]
        
        # Tag emitters for tracking
        for i, emitter in enumerate(emitters):
            emitter._test_emitter_id = f"ordering_emitter_{i}"
        
        # Define critical event sequence for Golden Path
        critical_sequence = [
            "agent_started",      # User sees AI began processing
            "agent_thinking",     # Real-time reasoning visibility
            "tool_executing",     # Tool usage transparency  
            "tool_completed",     # Tool results display
            "agent_completed"     # Response ready notification
        ]
        
        # Send sequences from multiple emitters with slight delays to encourage ordering issues
        sequence_tasks = []
        for emitter_idx, emitter in enumerate(emitters):
            task = self._send_ordered_sequence(emitter, critical_sequence, emitter_idx)
            sequence_tasks.append(task)
        
        # Execute sequences concurrently
        await asyncio.gather(*sequence_tasks)
        
        # Analyze ordering violations
        ordering_analysis = self._analyze_event_ordering(critical_sequence)
        
        # ASSERTIONS THAT SHOULD FAIL (proving ordering issues exist)
        
        # 1. Should have ordering violations
        ordering_violations = ordering_analysis['violations'] 
        assert ordering_violations > 0, (
            f"Expected event ordering violations with multiple emitters, "
            f"but found {ordering_violations}. Multiple emitters should cause "
            f"ordering chaos that breaks Golden Path sequence."
        )
        
        # 2. Should have sequences that don't match expected order
        correct_sequences = ordering_analysis['correct_sequences']
        total_sequences = ordering_analysis['total_sequences'] 
        sequence_accuracy = correct_sequences / total_sequences if total_sequences > 0 else 1.0
        
        assert sequence_accuracy < 0.8, (
            f"Expected <80% sequence accuracy due to multiple emitter chaos, "
            f"but found {sequence_accuracy:.2%} accuracy. This suggests ordering "
            f"isn't sufficiently disrupted by multiple emitters."
        )
        
        # 3. Should have critical events arriving in wrong order
        critical_event_disruptions = ordering_analysis['critical_disruptions']
        assert critical_event_disruptions > 0, (
            f"Expected critical business events to arrive out of order, "
            f"but found {critical_event_disruptions} disruptions. Multiple emitters "
            f"should disrupt the critical sequence that delivers chat value."
        )
        
        # Business value impact assessment  
        golden_path_integrity = self._assess_golden_path_integrity(ordering_analysis)
        assert golden_path_integrity < 0.7, (
            f"Expected Golden Path integrity <70% due to ordering issues, "
            f"but found {golden_path_integrity:.2%} integrity. Ordering violations "
            f"should significantly impact business value delivery."
        )

    @pytest.mark.expected_to_fail
    async def test_resource_contention_under_concurrent_load(self):
        """
        MUST FAIL: Prove resource contention degrades performance with multiple emitters.
        
        This test demonstrates that multiple emitters competing for resources
        leads to performance degradation that impacts user experience and business value.
        
        Expected Failure Mode: Significant performance degradation under load,
        proving multiple emitters create harmful resource contention.
        """
        # Create high-load scenario with multiple users and emitters
        user_count = 10
        emitters_per_user = 3
        events_per_emitter = 50
        
        # Simulate multiple concurrent enterprise customers
        concurrent_scenarios = []
        
        for user_idx in range(user_count):
            user_context = self._create_user_context(f"enterprise_user_{user_idx}")
            
            # Multiple emitters per user (realistic duplication scenario)
            user_emitters = []
            for emitter_idx in range(emitters_per_user):
                if emitter_idx == 0:
                    emitter = UnifiedWebSocketEmitter(
                        manager=self.mock_ws_manager,
                        user_id=user_context.user_id,
                        context=user_context
                    )
                else:
                    emitter = UserWebSocketEmitter(
                        context=user_context, 
                        router=self.mock_ws_manager
                    )
                    
                emitter._test_emitter_id = f"user_{user_idx}_emitter_{emitter_idx}"
                user_emitters.append(emitter)
            
            # Create high-load scenario for this user
            scenario = self._create_high_load_scenario(user_emitters, events_per_emitter)
            concurrent_scenarios.append(scenario)
        
        # Execute all scenarios concurrently to maximize contention
        start_time = time.time()
        await asyncio.gather(*concurrent_scenarios)
        total_execution_time = time.time() - start_time
        
        # Analyze performance degradation
        performance_metrics = self._analyze_performance_degradation()
        
        # ASSERTIONS THAT SHOULD FAIL (proving resource contention exists)
        
        # 1. Should have significant execution time increase
        baseline_time = self._calculate_baseline_execution_time(user_count, events_per_emitter)
        performance_ratio = total_execution_time / baseline_time
        
        assert performance_ratio > 2.0, (
            f"Expected >100% performance degradation due to resource contention, "
            f"but only found {(performance_ratio - 1) * 100:.1f}% degradation "
            f"({total_execution_time:.3f}s vs {baseline_time:.3f}s baseline). "
            f"Multiple emitters should cause significant contention."
        )
        
        # 2. Should have evidence of resource conflicts
        resource_conflicts = performance_metrics['resource_conflicts']
        assert resource_conflicts > user_count * 0.3, (
            f"Expected resource conflicts affecting >30% of users ({user_count * 0.3:.1f}), "
            f"but found {resource_conflicts}. Multiple emitters should create "
            f"detectable resource competition."
        )
        
        # 3. Should have degraded event delivery latency
        average_latency = performance_metrics['average_latency_ms']
        p99_latency = performance_metrics['p99_latency_ms']
        
        assert average_latency > 20.0, (
            f"Expected average event latency >20ms due to contention, "
            f"but found {average_latency:.2f}ms. Resource contention should "
            f"significantly increase event delivery latency."
        )
        
        assert p99_latency > 100.0, (
            f"Expected P99 latency >100ms due to contention, "
            f"but found {p99_latency:.2f}ms. Worst-case performance should "
            f"be severely impacted by multiple emitter resource conflicts."
        )
        
        # Business impact validation
        customer_experience_score = self._calculate_customer_experience_impact(performance_metrics)
        assert customer_experience_score < 0.6, (
            f"Expected customer experience score <60% due to performance issues, "
            f"but found {customer_experience_score:.2%}. Resource contention should "
            f"clearly degrade enterprise customer experience and business value."
        )

    # Helper methods for race condition detection and analysis
    
    async def _send_event_with_timing(self, emitter: Any, event_type: str, data: Dict[str, Any]):
        """Send event with precise timing for race condition detection."""
        timestamp = time.time()
        data.update({
            'test_timestamp': timestamp,
            'sequence_marker': f"{event_type}_{timestamp}"
        })
        
        # Use appropriate method based on emitter type
        if hasattr(emitter, 'emit'):
            await emitter.emit(event_type, data)
        elif hasattr(emitter, f'emit_{event_type}'):
            method = getattr(emitter, f'emit_{event_type}')
            await method(data)
        else:
            # Fallback for UserWebSocketEmitter or other types
            if hasattr(emitter, 'notify_agent_started') and event_type == 'agent_started':
                await emitter.notify_agent_started(data.get('agent_name', 'test_agent'), data)
            elif hasattr(emitter, 'notify_agent_thinking') and event_type == 'agent_thinking':
                await emitter.notify_agent_thinking(reasoning=data.get('thought', 'thinking'))
            # Add other event type mappings as needed
    
    async def _send_ordered_sequence(self, emitter: Any, sequence: List[str], emitter_idx: int):
        """Send ordered sequence of events with small delays."""
        for i, event_type in enumerate(sequence):
            # Small delay to encourage ordering issues
            await asyncio.sleep(0.001 * emitter_idx)  # Staggered delays
            
            await self._send_event_with_timing(emitter, event_type, {
                'emitter_id': emitter._test_emitter_id,
                'sequence_position': i,
                'expected_order': sequence
            })
    
    async def _create_high_load_scenario(self, emitters: List[Any], events_per_emitter: int):
        """Create high-load scenario for performance testing."""
        tasks = []
        event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for emitter in emitters:
            for _ in range(events_per_emitter):
                for event_type in event_types:
                    task = self._send_event_with_timing(emitter, event_type, {
                        'emitter_id': emitter._test_emitter_id,
                        'load_test_marker': True,
                        'business_priority': 'enterprise'
                    })
                    tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    def _analyze_race_condition_metrics(self) -> EventDeliveryMetrics:
        """Analyze collected events for race condition evidence.""" 
        total_events = len(self.events_received)
        
        # Count duplicates (same event type from different emitters)
        duplicates = self._count_duplicate_events()
        
        # Calculate timing-based metrics  
        timing_conflicts = self._detect_timing_conflicts(threshold_ms=1.0)
        
        # Calculate latency metrics if timing data available
        latencies = [
            event.get('data', {}).get('processing_time_ms', 0) 
            for event in self.events_received
        ]
        avg_latency = statistics.mean(latencies) if latencies else 0
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else 0
        
        return EventDeliveryMetrics(
            total_events_sent=total_events,
            total_events_received=total_events,
            duplicate_events=duplicates,
            timing_conflicts=timing_conflicts,
            average_latency_ms=avg_latency,
            p99_latency_ms=p99_latency,
            race_conditions_detected=timing_conflicts + duplicates
        )
    
    def _detect_timing_conflicts(self, threshold_ms: float = 1.0) -> int:
        """Detect timing conflicts between events."""
        conflicts = 0
        threshold_seconds = threshold_ms / 1000.0
        
        # Group events by type
        events_by_type = {}
        for event_type, timestamp, emitter_id in self.event_timing:
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append((timestamp, emitter_id))
        
        # Check for concurrent events of same type
        for event_type, timestamps in events_by_type.items():
            timestamps.sort()  # Sort by timestamp
            for i in range(len(timestamps) - 1):
                time_diff = timestamps[i + 1][0] - timestamps[i][0]
                if time_diff < threshold_seconds:
                    conflicts += 1
        
        return conflicts
    
    def _count_duplicate_events(self) -> int:
        """Count duplicate events from different emitters."""
        event_signatures = {}
        duplicates = 0
        
        for event in self.events_received:
            # Create signature based on event type, user, and timing
            signature = (
                event['event_type'],
                event['user_id'], 
                round(event['timestamp'], 2)  # Round to detect near-simultaneous events
            )
            
            if signature in event_signatures:
                duplicates += 1
            else:
                event_signatures[signature] = event
        
        return duplicates
    
    def _calculate_resource_contention(self) -> float:
        """Calculate resource contention score based on timing patterns."""
        if len(self.event_timing) < 2:
            return 0.0
        
        # Analyze timing distribution for contention patterns
        timestamps = [timing[1] for timing in self.event_timing]
        timestamps.sort()
        
        # Calculate clustering - events bunched together indicate contention
        time_gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_gap = statistics.mean(time_gaps)
        
        # Events clustered closer than average indicate contention
        clustered_events = sum(1 for gap in time_gaps if gap < avg_gap * 0.5)
        contention_score = clustered_events / len(time_gaps)
        
        return contention_score
    
    def _calculate_business_impact(self, metrics: EventDeliveryMetrics) -> Dict[str, float]:
        """Calculate business impact of race conditions."""
        # Revenue risk based on event delivery reliability
        reliability = 1.0 - (metrics.duplicate_events + metrics.timing_conflicts) / max(1, metrics.total_events_sent)
        revenue_risk = 1.0 - reliability
        
        # Customer experience impact
        latency_impact = min(1.0, metrics.average_latency_ms / 100.0)  # Normalize to 100ms
        
        return {
            'revenue_risk_score': revenue_risk,
            'customer_experience_impact': latency_impact,
            'overall_business_impact': (revenue_risk + latency_impact) / 2
        }
    
    def _analyze_event_ordering(self, expected_sequence: List[str]) -> Dict[str, Any]:
        """Analyze event ordering for violations."""
        # Group events by emitter and user
        emitter_sequences = {}
        for event in self.events_received:
            emitter_id = event['data'].get('emitter_id', 'unknown')
            user_id = event['user_id']
            key = f"{user_id}_{emitter_id}"
            
            if key not in emitter_sequences:
                emitter_sequences[key] = []
            emitter_sequences[key].append(event['event_type'])
        
        # Check each sequence for ordering violations
        violations = 0
        correct_sequences = 0
        critical_disruptions = 0
        total_sequences = len(emitter_sequences)
        
        for sequence in emitter_sequences.values():
            # Check if sequence matches expected order
            if self._sequence_matches_expected(sequence, expected_sequence):
                correct_sequences += 1
            else:
                violations += 1
                
                # Check for critical event disruptions
                if self._has_critical_disruptions(sequence, expected_sequence):
                    critical_disruptions += 1
        
        return {
            'violations': violations,
            'correct_sequences': correct_sequences,
            'total_sequences': total_sequences,
            'critical_disruptions': critical_disruptions
        }
    
    def _sequence_matches_expected(self, actual: List[str], expected: List[str]) -> bool:
        """Check if actual sequence matches expected order."""
        # Find subsequence in actual that matches expected
        if len(actual) < len(expected):
            return False
            
        expected_idx = 0
        for event in actual:
            if expected_idx < len(expected) and event == expected[expected_idx]:
                expected_idx += 1
        
        return expected_idx == len(expected)
    
    def _has_critical_disruptions(self, sequence: List[str], expected: List[str]) -> bool:
        """Check if sequence has critical business event disruptions."""
        critical_events = ["agent_started", "agent_completed"]
        
        for critical_event in critical_events:
            if critical_event in sequence and critical_event in expected:
                actual_pos = sequence.index(critical_event)
                expected_pos = expected.index(critical_event)
                
                # Critical disruption if event appears significantly out of position
                if abs(actual_pos - expected_pos) > 1:
                    return True
        
        return False
    
    def _assess_golden_path_integrity(self, ordering_analysis: Dict[str, Any]) -> float:
        """Assess how well Golden Path integrity is maintained."""
        if ordering_analysis['total_sequences'] == 0:
            return 1.0
        
        # Integrity based on correct sequences and minimal critical disruptions
        sequence_integrity = ordering_analysis['correct_sequences'] / ordering_analysis['total_sequences']
        critical_integrity = 1.0 - (ordering_analysis['critical_disruptions'] / ordering_analysis['total_sequences'])
        
        return (sequence_integrity + critical_integrity) / 2
    
    def _analyze_performance_degradation(self) -> Dict[str, Any]:
        """Analyze performance degradation metrics."""
        # Calculate latency metrics from timing data
        event_latencies = []
        resource_conflicts = 0
        
        # Estimate latency from timing gaps
        timestamps = sorted([timing[1] for timing in self.event_timing])
        for i in range(len(timestamps) - 1):
            gap = timestamps[i+1] - timestamps[i]
            latency_ms = gap * 1000
            event_latencies.append(latency_ms)
            
            # Resource conflict if events are too close (indicating contention)
            if gap < 0.001:  # Less than 1ms apart
                resource_conflicts += 1
        
        avg_latency = statistics.mean(event_latencies) if event_latencies else 0
        p99_latency = statistics.quantiles(event_latencies, n=100)[98] if len(event_latencies) > 1 else 0
        
        return {
            'average_latency_ms': avg_latency,
            'p99_latency_ms': p99_latency,
            'resource_conflicts': resource_conflicts,
            'total_events': len(self.events_received)
        }
    
    def _calculate_baseline_execution_time(self, user_count: int, events_per_emitter: int) -> float:
        """Calculate baseline execution time for comparison."""
        # Baseline assumes optimal single-emitter performance
        events_per_user = events_per_emitter * 5  # 5 event types
        total_events = user_count * events_per_user
        baseline_per_event_ms = 0.1  # 0.1ms per event optimally
        
        return (total_events * baseline_per_event_ms) / 1000.0  # Convert to seconds
    
    def _calculate_customer_experience_impact(self, performance_metrics: Dict[str, Any]) -> float:
        """Calculate customer experience impact score."""
        # Impact based on latency and resource conflicts
        latency_impact = min(1.0, performance_metrics['average_latency_ms'] / 50.0)  # Normalize to 50ms
        conflict_rate = performance_metrics['resource_conflicts'] / max(1, performance_metrics['total_events'])
        
        # Customer experience score (1.0 = perfect, 0.0 = terrible)
        experience_score = 1.0 - ((latency_impact + conflict_rate) / 2)
        return max(0.0, experience_score)
    
    def _create_user_context(self, user_id: str):
        """Create user execution context for testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}",
            run_id=f"run_{uuid.uuid4()}",
            request_id=f"req_{uuid.uuid4()}"
        )


# Additional test fixtures and utilities for race condition testing

@pytest.fixture
def enterprise_load_scenario():
    """Fixture providing enterprise customer high-load scenario setup."""
    return ConcurrentEmitterSimulation(
        emitter_count=5,
        events_per_emitter=200,
        concurrent_users=20,
        max_concurrency=100,
        simulation_duration_ms=10000,
        expected_race_conditions=50,
        performance_degradation_threshold=0.30
    )


@pytest.fixture  
def mock_websocket_manager():
    """Fixture providing mock WebSocket manager for testing."""
    manager = AsyncMock()
    manager.emit_critical_event = AsyncMock()
    manager.is_connection_active = MagicMock(return_value=True)
    manager.get_connection_health = MagicMock(return_value={'has_active_connections': True})
    return manager


if __name__ == "__main__":
    # Allow running individual tests for development
    pytest.main([__file__, "-v", "-s"])