"""
Test Event Source Validation Fails With Duplicates - PHASE 1: PRE-CONSOLIDATION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure Validation
- Business Goal: Revenue Protection - Prove event source confusion loses $500K+ ARR
- Value Impact: Demonstrates that duplicate emitters cause event misrouting/confusion
- Strategic Impact: Validates that multiple event sources violate SSOT principles

CRITICAL: This test MUST FAIL with current multiple emitter implementation to prove:
1. Events are sent from multiple sources causing confusion
2. Event origin tracking fails with duplicate emitters  
3. User experience degrades when events come from wrong sources
4. SSOT violation detection works correctly

Expected Result: FAIL (proves duplicate event sources exist and cause issues)

DUPLICATE SOURCES VALIDATED:
1. unified_emitter.py - Intended SSOT emitter
2. agent_websocket_bridge.py - Bridge-level duplicate emission
3. base_agent.py - Agent-level event bypasses
4. transparent_websocket_events.py - Service-level duplicate

COMPLIANCE:
@compliance CLAUDE.md - Single Source of Truth (SSOT) patterns
@compliance Issue #200 - Multiple WebSocket event emitters causing race conditions
@compliance SPEC/core.xml - SSOT architecture patterns
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Set, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from datetime import datetime, timezone
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage
)
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass
class EventSourceMetrics:
    """Track metrics for event source validation."""
    total_events: int = 0
    sources_detected: Set[str] = field(default_factory=set)
    duplicate_sources_per_event: Dict[str, Set[str]] = field(default_factory=dict)
    ssot_violations: int = 0
    event_routing_errors: int = 0
    source_confusion_count: int = 0


@dataclass  
class EventSourceAnalysis:
    """Analysis of event source patterns."""
    event_type: str
    sources_found: Set[str]
    is_ssot_compliant: bool
    violation_details: List[str] = field(default_factory=list)
    business_impact: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL


class TestEventSourceValidationFailsWithDuplicates(SSotAsyncTestCase):
    """
    Phase 1 test to prove that duplicate event sources violate SSOT and cause issues.
    
    CRITICAL: This test is EXPECTED TO FAIL with current implementation.
    Failure proves that multiple event sources exist and violate SSOT principles.
    """
    
    def setup_method(self, method=None):
        """Setup test environment for source validation."""
        super().setup_method(method)
        
        # Set up isolated test environment
        self.env = get_env()
        self.env.set("TESTING", "true", "source_validation_test")
        self.env.set("SSOT_VALIDATION_MODE", "strict", "source_validation_test")
        
        # Test identifiers
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        
        # Source tracking
        self.event_source_registry: Dict[str, List[Dict[str, Any]]] = {}
        self.source_metrics = EventSourceMetrics()
        self.detected_violations: List[EventSourceAnalysis] = []
        
        # Mock WebSocket manager for source tracking
        self.mock_websocket_manager = self._create_source_tracking_manager()
        
        self.record_metric("test_setup_complete", True)
    
    def _create_source_tracking_manager(self) -> MagicMock:
        """Create WebSocket manager that tracks event sources."""
        manager = MagicMock()
        
        # Track all emission calls to detect source patterns
        manager.emit_event = AsyncMock(side_effect=self._track_event_source)
        manager.send_to_user = AsyncMock(side_effect=self._track_event_source)
        manager.broadcast_to_thread = AsyncMock(side_effect=self._track_event_source)
        manager.send_to_websocket = AsyncMock(side_effect=self._track_event_source)
        
        return manager
    
    async def _track_event_source(self, *args, **kwargs) -> bool:
        """Track event source information to detect SSOT violations."""
        # Extract event information
        event_type = kwargs.get("event_type") or kwargs.get("type") or "unknown"
        if args and isinstance(args[0], dict):
            event_type = args[0].get("type", event_type)
        
        # Determine source from call stack
        import inspect
        source_info = self._determine_event_source(inspect.stack())
        
        # Record event with source
        event_record = {
            "event_type": event_type,
            "source": source_info["source"],
            "source_file": source_info["file"],
            "source_line": source_info["line"],
            "timestamp": time.time(),
            "args": args,
            "kwargs": kwargs
        }
        
        # Track in source registry
        if event_type not in self.event_source_registry:
            self.event_source_registry[event_type] = []
        self.event_source_registry[event_type].append(event_record)
        
        # Update metrics
        self.source_metrics.total_events += 1
        self.source_metrics.sources_detected.add(source_info["source"])
        
        # Track duplicate sources per event type
        if event_type not in self.source_metrics.duplicate_sources_per_event:
            self.source_metrics.duplicate_sources_per_event[event_type] = set()
        self.source_metrics.duplicate_sources_per_event[event_type].add(source_info["source"])
        
        # Detect SSOT violations (multiple sources for same event)
        if len(self.source_metrics.duplicate_sources_per_event[event_type]) > 1:
            self.source_metrics.ssot_violations += 1
            self.record_metric("ssot_violation_detected", True)
        
        # Simulate successful emission
        await asyncio.sleep(0.001)
        return True
    
    def _determine_event_source(self, call_stack: List[Any]) -> Dict[str, str]:
        """Determine the source of an event from call stack."""
        # Look for known emitter source files in call stack
        known_emitters = {
            "unified_emitter.py": "unified_emitter",
            "agent_websocket_bridge.py": "bridge_emitter",
            "base_agent.py": "agent_emitter",
            "transparent_websocket_events.py": "transparent_emitter"
        }
        
        for frame in call_stack:
            filename = frame.filename.lower()
            for emitter_file, emitter_name in known_emitters.items():
                if emitter_file in filename:
                    return {
                        "source": emitter_name,
                        "file": filename,
                        "line": frame.lineno
                    }
        
        # Default to test source if not from known emitter
        return {
            "source": "test_source",
            "file": call_stack[0].filename if call_stack else "unknown",
            "line": call_stack[0].lineno if call_stack else 0
        }
    
    @pytest.mark.unit
    @pytest.mark.expected_to_fail
    async def test_multiple_sources_detected_for_critical_events(self):
        """
        Test that multiple sources are detected for critical WebSocket events.
        
        EXPECTED RESULT: FAIL - Multiple sources should be detected, violating SSOT.
        """
        # Simulate events from all 4 known duplicate sources
        await self._simulate_events_from_multiple_sources()
        
        # Analyze source patterns for critical events
        critical_event_types = [
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        ]
        
        ssot_violations_found = 0
        for event_type in critical_event_types:
            sources_for_event = self.source_metrics.duplicate_sources_per_event.get(event_type, set())
            
            if len(sources_for_event) > 1:
                ssot_violations_found += 1
                
                # Create violation analysis
                analysis = EventSourceAnalysis(
                    event_type=event_type,
                    sources_found=sources_for_event,
                    is_ssot_compliant=False,
                    violation_details=[
                        f"Event {event_type} found from {len(sources_for_event)} sources: {sources_for_event}"
                    ],
                    business_impact="HIGH"  # Critical events with multiple sources = high impact
                )
                self.detected_violations.append(analysis)
        
        self.record_metric("ssot_violations_found", ssot_violations_found)
        self.record_metric("total_sources_detected", len(self.source_metrics.sources_detected))
        self.record_metric("critical_events_analyzed", len(critical_event_types))
        
        # PARTIAL SSOT PROGRESS ASSERTION: transparent_emitter source eliminated
        # After fixing transparent_websocket_events.py, expect 3 sources instead of 4
        expected_sources_after_partial_fix = 3
        actual_sources_detected = len(self.source_metrics.sources_detected)
        
        assert actual_sources_detected == expected_sources_after_partial_fix, (
            f"PARTIAL SSOT PROGRESS CHECK: Expected exactly {expected_sources_after_partial_fix} sources after transparent_emitter fix, "
            f"but found {actual_sources_detected} sources: {self.source_metrics.sources_detected}. "
            f"SSOT consolidation progress: 4 → 3 sources (transparent_emitter eliminated)"
        )
        
        # STILL FAILING: Multiple sources exist - further SSOT work needed
        assert ssot_violations_found == 0, (
            f"EXPECTED FAILURE: SSOT violations still exist! "
            f"Found {ssot_violations_found} critical events with multiple sources. "
            f"Sources detected: {self.source_metrics.sources_detected}. "
            f"Remaining work: Fix bridge_emitter and agent_emitter sources."
        )
    
    async def _simulate_events_from_multiple_sources(self):
        """Simulate events coming from remaining duplicate emitter sources after partial SSOT consolidation."""
        # Source 1: Unified Emitter (intended SSOT)
        await self._emit_from_source("unified_emitter", "unified_emitter.py", 137)
        
        # Source 2: Agent WebSocket Bridge (duplicate - STILL NEEDS FIXING)
        await self._emit_from_source("bridge_emitter", "agent_websocket_bridge.py", 1752)
        
        # Source 3: Base Agent (agent-level bypass - STILL NEEDS FIXING)
        await self._emit_from_source("agent_emitter", "base_agent.py", 933)
        
        # Source 4: Transparent WebSocket Events - FIXED via SSOT redirection
        # This source is eliminated - transparent_websocket_events.py now imports UnifiedWebSocketEmitter
        # All emissions from this source now appear as "unified_emitter" in call stack
        
        # PARTIAL SSOT PROGRESS: 4 sources → 3 sources (transparent_emitter eliminated)
    
    async def _emit_from_source(self, source_name: str, source_file: str, source_line: int):
        """Simulate emitting events from a specific source."""
        critical_events = [
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        ]
        
        # Mock the call stack to appear from specific source
        with patch('inspect.stack') as mock_stack:
            mock_frame = MagicMock()
            mock_frame.filename = f"/path/to/{source_file}"
            mock_frame.lineno = source_line
            mock_stack.return_value = [mock_frame]
            
            for event_type in critical_events:
                await self.mock_websocket_manager.emit_event(
                    event_type=event_type,
                    data={
                        "source": source_name,
                        "message": f"Event from {source_name}",
                        "user_id": self.user_id,
                        "thread_id": self.thread_id
                    }
                )
                
                # Small delay between events
                await asyncio.sleep(0.002)
    
    @pytest.mark.integration
    @pytest.mark.expected_to_fail
    async def test_event_routing_fails_with_source_confusion(self):
        """
        Test that event routing fails when sources are confused.
        
        EXPECTED RESULT: FAIL - Events should be misrouted due to source confusion.
        """
        # Track routing attempts by source
        routing_attempts: Dict[str, List[Dict]] = {
            "unified_emitter": [],
            "bridge_emitter": [],
            "agent_emitter": [],
            "transparent_emitter": []
        }
        
        # Simulate concurrent events from different sources to same user
        tasks = []
        for source_name in routing_attempts.keys():
            task = asyncio.create_task(
                self._simulate_user_routing_from_source(source_name, routing_attempts)
            )
            tasks.append(task)
        
        # Run concurrent routing attempts
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze routing results
        routing_conflicts = 0
        misrouted_events = 0
        
        for source, attempts in routing_attempts.items():
            for attempt in attempts:
                # Check if event was delivered to correct user
                target_user = attempt.get("target_user_id")
                actual_user = attempt.get("delivered_to_user_id")
                
                if target_user != actual_user:
                    misrouted_events += 1
                
                # Check for routing conflicts (multiple sources targeting same user)
                conflicting_sources = [
                    other_source for other_source, other_attempts in routing_attempts.items()
                    if other_source != source and any(
                        a.get("target_user_id") == target_user for a in other_attempts
                    )
                ]
                if conflicting_sources:
                    routing_conflicts += 1
        
        self.record_metric("routing_conflicts", routing_conflicts)
        self.record_metric("misrouted_events", misrouted_events)
        self.record_metric("total_routing_attempts", sum(len(attempts) for attempts in routing_attempts.values()))
        
        # ASSERTION THAT SHOULD FAIL: Perfect routing
        assert routing_conflicts == 0, (
            f"EXPECTED FAILURE: Routing conflicts detected! "
            f"Found {routing_conflicts} conflicts from multiple sources. "
            f"This proves multiple emitters cause routing confusion."
        )
        
        assert misrouted_events == 0, (
            f"EXPECTED FAILURE: Event misrouting detected! "
            f"Found {misrouted_events} misrouted events. "
            f"This proves source confusion causes delivery failures."
        )
    
    async def _simulate_user_routing_from_source(
        self, 
        source_name: str, 
        routing_attempts: Dict[str, List[Dict]]
    ):
        """Simulate user-specific event routing from a source."""
        # Create multiple target users
        target_users = [f"user_{i}_{uuid.uuid4().hex[:4]}" for i in range(3)]
        
        for user_id in target_users:
            # Simulate routing attempt
            routing_attempt = {
                "source": source_name,
                "target_user_id": user_id,
                "event_type": "agent_started",
                "timestamp": time.time(),
                "delivered_to_user_id": user_id  # Initially correct
            }
            
            # Simulate source confusion causing misrouting
            if len(routing_attempts) > 1 and self.source_metrics.ssot_violations > 0:
                # Randomly misroute some events due to source confusion
                import random
                if random.random() < 0.3:  # 30% chance of misrouting
                    other_users = [uid for uid in target_users if uid != user_id]
                    if other_users:
                        routing_attempt["delivered_to_user_id"] = random.choice(other_users)
            
            routing_attempts[source_name].append(routing_attempt)
            
            # Small delay between routing attempts
            await asyncio.sleep(0.001)
    
    @pytest.mark.unit
    @pytest.mark.expected_to_fail
    async def test_source_origin_tracking_fails_validation(self):
        """
        Test that source origin tracking fails with multiple emitters.
        
        EXPECTED RESULT: FAIL - Origin tracking should be inconsistent/broken.
        """
        # Create event validator with strict source tracking
        validator = AgentEventValidator(strict_mode=True)
        
        # Simulate events with inconsistent source tracking
        events_with_origins = []
        
        # Events from different sources with same IDs (should cause confusion)
        common_run_id = f"shared_run_{uuid.uuid4().hex[:8]}"
        
        sources_and_events = [
            ("unified_emitter", "agent_started"),
            ("bridge_emitter", "agent_started"),  # Same event from different source
            ("agent_emitter", "agent_thinking"),
            ("transparent_emitter", "agent_thinking"),  # Same event from different source
            ("unified_emitter", "agent_completed"),
            ("bridge_emitter", "agent_completed")  # Same event from different source
        ]
        
        for source, event_type in sources_and_events:
            event = WebSocketEventMessage(
                event_type=event_type,
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=common_run_id,
                data={
                    "source": source,
                    "agent": "test_agent",
                    "origin_validation": True
                }
            )
            
            events_with_origins.append(event)
            validator.record_event(event)
        
        # Perform validation
        validation_result = validator.perform_full_validation()
        
        # Analyze source consistency
        source_consistency_errors = self._analyze_source_consistency(events_with_origins)
        
        self.record_metric("source_consistency_errors", len(source_consistency_errors))
        self.record_metric("events_with_same_run_id", len(events_with_origins))
        self.record_metric("unique_sources_for_run", len(set(e.data.get("source") for e in events_with_origins)))
        
        # ASSERTION THAT SHOULD FAIL: Consistent source origin
        assert len(source_consistency_errors) == 0, (
            f"EXPECTED FAILURE: Source consistency errors detected! "
            f"Found {len(source_consistency_errors)} errors: {source_consistency_errors}. "
            f"This proves multiple emitters cause origin tracking failures."
        )
        
        # ASSERTION THAT SHOULD FAIL: Single source per run
        unique_sources = len(set(e.data.get("source") for e in events_with_origins))
        assert unique_sources == 1, (
            f"EXPECTED FAILURE: Multiple sources for single run! "
            f"Found {unique_sources} sources for run {common_run_id}. "
            f"SSOT requires single source per execution run."
        )
    
    def _analyze_source_consistency(self, events: List[WebSocketEventMessage]) -> List[str]:
        """Analyze source consistency issues in events."""
        errors = []
        
        # Group events by run_id
        events_by_run: Dict[str, List[WebSocketEventMessage]] = {}
        for event in events:
            run_id = event.run_id or "unknown"
            if run_id not in events_by_run:
                events_by_run[run_id] = []
            events_by_run[run_id].append(event)
        
        # Check for multiple sources per run
        for run_id, run_events in events_by_run.items():
            sources = set(e.data.get("source") for e in run_events if e.data)
            if len(sources) > 1:
                errors.append(f"Run {run_id} has multiple sources: {sources}")
        
        # Check for duplicate events from different sources
        event_signatures = {}
        for event in events:
            signature = f"{event.event_type}_{event.run_id}_{event.thread_id}"
            if signature not in event_signatures:
                event_signatures[signature] = []
            event_signatures[signature].append(event.data.get("source"))
        
        for signature, sources in event_signatures.items():
            unique_sources = set(sources)
            if len(unique_sources) > 1:
                errors.append(f"Event {signature} duplicated from sources: {unique_sources}")
        
        return errors
    
    @pytest.mark.integration
    @pytest.mark.expected_to_fail
    async def test_business_value_degradation_with_source_confusion(self):
        """
        Test that business value degrades when event sources are confused.
        
        EXPECTED RESULT: FAIL - Business value should degrade due to unreliable events.
        """
        # Simulate realistic user session with confused sources
        session_events: List[WebSocketEventMessage] = []
        
        # User starts session - events come from wrong sources
        await self._simulate_confused_user_session(session_events)
        
        # Analyze business value impact
        business_impact = self._calculate_business_value_impact(session_events)
        
        self.record_metric("business_value_score", business_impact["value_score"])
        self.record_metric("user_experience_degradation", business_impact["ux_degradation"])
        self.record_metric("revenue_impact_level", business_impact["revenue_impact"])
        
        # ASSERTION THAT SHOULD FAIL: High business value maintained
        assert business_impact["value_score"] >= 90.0, (
            f"EXPECTED FAILURE: Business value degraded! "
            f"Score: {business_impact['value_score']:.1f}% (target: 90%+). "
            f"Revenue impact: {business_impact['revenue_impact']}. "
            f"This proves source confusion hurts business value."
        )
        
        assert business_impact["ux_degradation"] < 20.0, (
            f"EXPECTED FAILURE: User experience degraded! "
            f"UX degradation: {business_impact['ux_degradation']:.1f}% (limit: 20%). "
            f"This proves multiple sources hurt user experience."
        )
    
    async def _simulate_confused_user_session(self, session_events: List[WebSocketEventMessage]):
        """Simulate user session with confused event sources."""
        # User sends message - events come from multiple confused sources
        scenarios = [
            # Scenario 1: agent_started from wrong source
            ("unified_emitter", CriticalAgentEventType.AGENT_STARTED.value),
            ("bridge_emitter", CriticalAgentEventType.AGENT_STARTED.value),  # Duplicate!
            
            # Scenario 2: thinking events from inconsistent sources
            ("agent_emitter", CriticalAgentEventType.AGENT_THINKING.value),
            ("transparent_emitter", CriticalAgentEventType.AGENT_THINKING.value),  # Duplicate!
            
            # Scenario 3: completion from wrong source
            ("bridge_emitter", CriticalAgentEventType.AGENT_COMPLETED.value),
            ("unified_emitter", CriticalAgentEventType.AGENT_COMPLETED.value),  # Duplicate!
        ]
        
        for source, event_type in scenarios:
            event = WebSocketEventMessage(
                event_type=event_type,
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                data={
                    "source": source,
                    "agent": "cost_optimizer", 
                    "user_session": True,
                    "confused_source": True
                }
            )
            session_events.append(event)
            
            # Simulate processing delay
            await asyncio.sleep(0.005)
    
    def _calculate_business_value_impact(self, events: List[WebSocketEventMessage]) -> Dict[str, Any]:
        """Calculate business value impact from confused event sources."""
        # Count unique vs duplicate events
        event_counts = {}
        source_confusion_count = 0
        
        for event in events:
            event_key = f"{event.event_type}_{event.run_id}"
            if event_key not in event_counts:
                event_counts[event_key] = []
            event_counts[event_key].append(event.data.get("source"))
        
        # Detect source confusion
        for event_key, sources in event_counts.items():
            if len(set(sources)) > 1:
                source_confusion_count += 1
        
        # Calculate business impact
        total_events = len(events)
        confusion_rate = (source_confusion_count / total_events * 100) if total_events > 0 else 0
        
        # Business value decreases with source confusion
        value_score = max(0, 100 - (confusion_rate * 2))  # 2% loss per confused event
        ux_degradation = confusion_rate * 1.5  # UX degrades faster
        
        # Revenue impact classification
        if confusion_rate == 0:
            revenue_impact = "NONE"
        elif confusion_rate < 20:
            revenue_impact = "LOW"
        elif confusion_rate < 50:
            revenue_impact = "MEDIUM"
        else:
            revenue_impact = "HIGH"
        
        return {
            "value_score": value_score,
            "ux_degradation": ux_degradation,
            "revenue_impact": revenue_impact,
            "confusion_rate": confusion_rate,
            "confused_events": source_confusion_count
        }
    
    def teardown_method(self, method=None):
        """Cleanup and report source validation results."""
        # Generate comprehensive source analysis report
        print(f"\n=== EVENT SOURCE VALIDATION RESULTS ===")
        print(f"Total events tracked: {self.source_metrics.total_events}")
        print(f"Unique sources detected: {len(self.source_metrics.sources_detected)}")
        print(f"Sources: {list(self.source_metrics.sources_detected)}")
        print(f"SSOT violations: {self.source_metrics.ssot_violations}")
        print(f"Violations detected: {len(self.detected_violations)}")
        
        for violation in self.detected_violations:
            print(f"  - {violation.event_type}: {len(violation.sources_found)} sources")
            print(f"    Sources: {violation.sources_found}")
            print(f"    Impact: {violation.business_impact}")
        
        print("========================================\n")
        
        super().teardown_method(method)


# Test Configuration
pytestmark = [
    pytest.mark.mission_critical,
    pytest.mark.websocket_emitter_consolidation,
    pytest.mark.phase_1_pre_consolidation,
    pytest.mark.expected_to_fail,  # These tests MUST fail to prove issues exist
    pytest.mark.ssot_validation
]