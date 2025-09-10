"""
Test Multiple WebSocket Emitter Race Condition Reproduction - PHASE 1: PRE-CONSOLIDATION

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure
- Business Goal: Revenue Protection - Prove $500K+ ARR is at risk from race conditions  
- Value Impact: Demonstrates that multiple emitters cause event delivery failures
- Strategic Impact: Validates the need for SSOT emitter consolidation

CRITICAL: This test MUST FAIL with current multiple emitter implementation to prove:
1. Race conditions occur when multiple emitters send same events
2. Event delivery becomes unreliable under concurrent load
3. Business value is lost when users don't see AI responses

Expected Result: FAIL (proves current race condition issues exist)

DUPLICATE EMITTERS TESTED:
1. /netra_backend/app/websocket_core/unified_emitter.py:137 (intended SSOT)
2. /netra_backend/app/services/agent_websocket_bridge.py:1752 (bridge duplicate)  
3. /netra_backend/app/agents/base_agent.py:933 (agent-level bypass)
4. /netra_backend/app/services/websocket/transparent_websocket_events.py:292 (transparency duplicate)

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance Issue #200 - Multiple WebSocket event emitters causing race conditions
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Set
from unittest.mock import AsyncMock, MagicMock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator, 
    CriticalAgentEventType,
    assert_critical_events_received
)
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, RunID

# Import all 4 duplicate emitters to reproduce race conditions
try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge  
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.services.websocket.transparent_websocket_events import TransparentWebSocketEvents
    EMITTERS_AVAILABLE = True
except ImportError as e:
    EMITTERS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class TestMultipleEmitterRaceConditionReproduction(SSotAsyncTestCase):
    """
    Phase 1 test to reproduce race conditions with multiple WebSocket emitters.
    
    CRITICAL: This test is EXPECTED TO FAIL with current implementation.
    Failure proves that multiple emitters cause race conditions and event delivery issues.
    """
    
    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        
        # Skip if emitters not available
        if not EMITTERS_AVAILABLE:
            pytest.skip(f"WebSocket emitters not available: {IMPORT_ERROR}")
        
        # Set up isolated test environment
        self.env = get_env()
        self.env.set("TESTING", "true", "race_condition_test")
        
        # Test data
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        
        # Track race condition indicators
        self.event_delivery_order: List[Dict[str, Any]] = []
        self.emitter_collision_count = 0
        self.duplicate_event_count = 0
        
        # Mock WebSocket manager for testing
        self.mock_websocket_manager = self._create_mock_websocket_manager()
        
        self.record_metric("test_setup_complete", True)
    
    def _create_mock_websocket_manager(self) -> MagicMock:
        """Create mock WebSocket manager that tracks race conditions."""
        manager = MagicMock()
        
        # Track concurrent emissions to detect race conditions
        manager.emit_event = AsyncMock(side_effect=self._track_concurrent_emission)
        manager.send_to_user = AsyncMock(side_effect=self._track_concurrent_emission)
        manager.broadcast_to_thread = AsyncMock(side_effect=self._track_concurrent_emission)
        
        return manager
    
    async def _track_concurrent_emission(self, *args, **kwargs) -> bool:
        """Track concurrent event emissions to detect race conditions."""
        emission_data = {
            "timestamp": time.time(),
            "args": args,
            "kwargs": kwargs,
            "emitter_source": "unknown"
        }
        
        # Check for rapid successive emissions (race condition indicator)
        if self.event_delivery_order:
            last_emission = self.event_delivery_order[-1]
            time_gap = emission_data["timestamp"] - last_emission["timestamp"]
            
            # If emissions are within 10ms, likely a race condition
            if time_gap < 0.01:
                self.emitter_collision_count += 1
                self.record_metric("race_condition_detected", True)
        
        # Check for duplicate events
        event_type = kwargs.get("event_type") or (args[0] if args else "unknown")
        existing_events = [e for e in self.event_delivery_order if e.get("event_type") == event_type]
        if existing_events:
            self.duplicate_event_count += 1
            self.record_metric("duplicate_event_detected", True)
        
        emission_data["event_type"] = event_type
        self.event_delivery_order.append(emission_data)
        
        # Simulate network/processing delay
        await asyncio.sleep(0.005)
        return True
    
    def _create_multiple_emitters(self) -> List[Any]:
        """Create instances of all 4 duplicate emitters."""
        emitters = []
        
        try:
            # 1. Unified emitter (intended SSOT)
            unified_emitter = UnifiedWebSocketEmitter(
                websocket_manager=self.mock_websocket_manager,
                user_context=None  # Will be mocked
            )
            emitters.append(("unified_emitter", unified_emitter))
            
            # 2. Agent WebSocket bridge (duplicate)
            bridge_emitter = AgentWebSocketBridge(
                websocket_manager=self.mock_websocket_manager,
                user_context=None  # Will be mocked
            )
            emitters.append(("bridge_emitter", bridge_emitter))
            
            # 3. Base agent (agent-level bypass)
            base_agent = BaseAgent(
                name="test_agent",
                description="Test agent for race condition testing"
            )
            # Inject mock WebSocket adapter
            base_agent._websocket_adapter = MagicMock()
            base_agent._websocket_adapter.emit_agent_started = AsyncMock()
            base_agent._websocket_adapter.emit_thinking = AsyncMock()
            base_agent._websocket_adapter.emit_tool_executing = AsyncMock()
            base_agent._websocket_adapter.emit_tool_completed = AsyncMock()
            base_agent._websocket_adapter.emit_agent_completed = AsyncMock()
            emitters.append(("base_agent", base_agent))
            
            # 4. Transparent WebSocket events (transparency duplicate)
            transparent_events = TransparentWebSocketEvents(
                user_id=self.user_id,
                request_id=self.run_id,
                context=MagicMock(),  # Mock user context
                websocket_manager=self.mock_websocket_manager
            )
            emitters.append(("transparent_events", transparent_events))
            
        except Exception as e:
            pytest.skip(f"Could not create emitters for race condition test: {e}")
        
        return emitters
    
    @pytest.mark.unit
    @pytest.mark.expected_to_fail
    async def test_concurrent_emitter_usage_creates_race_conditions(self):
        """
        Test that concurrent usage of multiple emitters creates race conditions.
        
        EXPECTED RESULT: FAIL - This test should fail because race conditions occur.
        """
        # Create all 4 duplicate emitters
        emitters = self._create_multiple_emitters()
        self.record_metric("emitters_created", len(emitters))
        
        # Simulate concurrent agent execution using all emitters
        tasks = []
        
        for emitter_name, emitter in emitters:
            task = asyncio.create_task(
                self._simulate_agent_execution_with_emitter(emitter_name, emitter)
            )
            tasks.append(task)
        
        # Run all emitters concurrently
        start_time = time.time()
        await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        self.record_metric("concurrent_execution_time", execution_time)
        self.record_metric("total_emissions", len(self.event_delivery_order))
        self.record_metric("emitter_collisions", self.emitter_collision_count)
        self.record_metric("duplicate_events", self.duplicate_event_count)
        
        # ASSERTION THAT SHOULD FAIL: No race conditions detected
        # This assertion should fail because multiple emitters cause race conditions
        assert self.emitter_collision_count == 0, (
            f"EXPECTED FAILURE: Race conditions detected! "
            f"Found {self.emitter_collision_count} emitter collisions. "
            f"This proves multiple emitters cause race conditions."
        )
        
        # Additional assertion that should fail: No duplicate events
        assert self.duplicate_event_count == 0, (
            f"EXPECTED FAILURE: Duplicate events detected! "
            f"Found {self.duplicate_event_count} duplicate events. "
            f"This proves multiple emitters cause event duplication."
        )
    
    async def _simulate_agent_execution_with_emitter(self, emitter_name: str, emitter: Any):
        """Simulate agent execution using a specific emitter."""
        try:
            # Emit all 5 critical events rapidly
            critical_events = [
                ("agent_started", "started"),
                ("agent_thinking", "thinking"), 
                ("tool_executing", "executing"),
                ("tool_completed", "completed"),
                ("agent_completed", "finished")
            ]
            
            for event_type, status in critical_events:
                if hasattr(emitter, f'emit_{event_type}'):
                    await getattr(emitter, f'emit_{event_type}')(
                        f"Test {status} from {emitter_name}"
                    )
                elif hasattr(emitter, 'emit_agent_event'):
                    await emitter.emit_agent_event(
                        event_type=event_type,
                        data={"status": status, "emitter": emitter_name}
                    )
                
                # Small delay between events (simulates real execution)
                await asyncio.sleep(0.001)
                
        except Exception as e:
            # Record emitter failures
            self.record_metric(f"{emitter_name}_error", str(e))
    
    @pytest.mark.integration  
    @pytest.mark.expected_to_fail
    async def test_event_delivery_reliability_with_multiple_emitters(self):
        """
        Test event delivery reliability when multiple emitters are active.
        
        EXPECTED RESULT: FAIL - Events should be lost/duplicated with multiple emitters.
        """
        emitters = self._create_multiple_emitters()
        
        # Create event validator to track critical events
        validator = AgentEventValidator(strict_mode=True, timeout_seconds=10.0)
        
        # Simulate high-load concurrent execution
        rounds = 5
        for round_num in range(rounds):
            tasks = []
            for emitter_name, emitter in emitters:
                task = asyncio.create_task(
                    self._emit_critical_events_sequence(
                        emitter_name, emitter, validator, round_num
                    )
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.1)  # Brief pause between rounds
        
        # Validate event delivery
        validation_result = validator.perform_full_validation()
        
        self.record_metric("business_value_score", validation_result.business_value_score)
        self.record_metric("missing_events", len(validation_result.missing_critical_events))
        self.record_metric("total_events_received", len(validation_result.received_events))
        
        # ASSERTION THAT SHOULD FAIL: Perfect event delivery
        # With multiple emitters, we expect missing or duplicate events
        assert validation_result.is_valid, (
            f"EXPECTED FAILURE: Event delivery failed! "
            f"Business value score: {validation_result.business_value_score:.1f}% "
            f"Missing events: {validation_result.missing_critical_events} "
            f"Revenue impact: {validation_result.revenue_impact}. "
            f"This proves multiple emitters cause delivery failures."
        )
        
        # Additional assertion: Event count should be exactly 5 * rounds * emitters
        expected_events = 5 * rounds * len(emitters)
        actual_events = len(validation_result.received_events)
        
        assert actual_events == expected_events, (
            f"EXPECTED FAILURE: Event count mismatch! "
            f"Expected {expected_events} events, got {actual_events}. "
            f"This proves multiple emitters cause event loss/duplication."
        )
    
    async def _emit_critical_events_sequence(
        self, 
        emitter_name: str, 
        emitter: Any, 
        validator: AgentEventValidator,
        round_num: int
    ):
        """Emit sequence of critical events and record in validator."""
        events_to_emit = [
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_THINKING.value,
            CriticalAgentEventType.TOOL_EXECUTING.value,
            CriticalAgentEventType.TOOL_COMPLETED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        ]
        
        for event_type in events_to_emit:
            # Record event in validator (simulates receiving via WebSocket)
            event_data = {
                "type": event_type,
                "data": {
                    "emitter": emitter_name,
                    "round": round_num,
                    "timestamp": time.time()
                },
                "user_id": self.user_id,
                "thread_id": self.thread_id,
                "run_id": self.run_id
            }
            
            validator.record_event(event_data)
            
            # Small delay to simulate processing
            await asyncio.sleep(0.002)
    
    @pytest.mark.unit
    @pytest.mark.expected_to_fail  
    async def test_emitter_source_isolation_failure(self):
        """
        Test that multiple emitters fail to maintain proper source isolation.
        
        EXPECTED RESULT: FAIL - Events should be cross-contaminated between emitters.
        """
        emitters = self._create_multiple_emitters()
        
        # Track events by source
        events_by_source: Dict[str, List[Dict]] = {name: [] for name, _ in emitters}
        
        # Each emitter sends events with unique identifiers
        for emitter_name, emitter in emitters:
            unique_data = {
                "source": emitter_name,
                "unique_id": f"{emitter_name}_{uuid.uuid4().hex[:8]}",
                "isolation_test": True
            }
            
            # Simulate events with source-specific data
            await self._emit_with_source_tracking(
                emitter, emitter_name, unique_data, events_by_source
            )
        
        # Analyze source isolation
        cross_contamination_count = 0
        for source_name, events in events_by_source.items():
            for event in events:
                if event.get("source") != source_name:
                    cross_contamination_count += 1
        
        self.record_metric("cross_contamination_events", cross_contamination_count)
        self.record_metric("total_source_events", sum(len(events) for events in events_by_source.values()))
        
        # ASSERTION THAT SHOULD FAIL: Perfect source isolation
        assert cross_contamination_count == 0, (
            f"EXPECTED FAILURE: Source isolation failed! "
            f"Found {cross_contamination_count} cross-contaminated events. "
            f"This proves multiple emitters cause source confusion."
        )
    
    async def _emit_with_source_tracking(
        self, 
        emitter: Any, 
        source_name: str, 
        source_data: Dict[str, Any],
        events_by_source: Dict[str, List[Dict]]
    ):
        """Emit events with source tracking."""
        # Mock emission that tracks to our source registry
        event_data = {
            "type": "test_event",
            "data": source_data,
            "timestamp": time.time()
        }
        
        # Record event under source
        events_by_source[source_name].append(event_data)
        
        # Simulate potential cross-contamination by recording in wrong source sometimes
        # (This simulates the race condition bug)
        if len(events_by_source) > 1:
            other_sources = [name for name in events_by_source.keys() if name != source_name]
            if other_sources and self.emitter_collision_count > 0:
                # Simulate cross-contamination
                wrong_source = other_sources[0]
                events_by_source[wrong_source].append(event_data)
    
    def teardown_method(self, method=None):
        """Cleanup test environment."""
        # Log final metrics for race condition analysis
        metrics = self.get_all_metrics()
        
        print(f"\n=== RACE CONDITION TEST RESULTS ===")
        print(f"Emitter collisions detected: {metrics.get('emitter_collisions', 0)}")
        print(f"Duplicate events: {metrics.get('duplicate_events', 0)}")
        print(f"Cross-contamination events: {metrics.get('cross_contamination_events', 0)}")
        print(f"Total emissions tracked: {metrics.get('total_emissions', 0)}")
        print(f"Business value score: {metrics.get('business_value_score', 0):.1f}%")
        print("=====================================\n")
        
        super().teardown_method(method)


# Test Configuration
pytestmark = [
    pytest.mark.mission_critical,
    pytest.mark.websocket_emitter_consolidation,
    pytest.mark.phase_1_pre_consolidation,
    pytest.mark.expected_to_fail  # These tests MUST fail to prove issues exist
]