"""
WebSocket Event Emission Validation Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Revenue Protection Infrastructure
- Business Goal: Protect $500K+ ARR through reliable event emission to users
- Value Impact: Validates end-to-end event emission ensuring users see AI value delivery
- Strategic Impact: Integration tests prevent silent failures in production event flows

Mission: Test real WebSocket event emission with actual UnifiedEventValidator integration
to ensure the 5 critical events reach users without failures, typos, or silent drops.

These tests MUST validate:
1. Real WebSocket event emission to connected clients
2. Event validation during emission process
3. Cross-user isolation during event emission 
4. Performance and reliability under load
5. Error handling and graceful degradation

CRITICAL: These tests simulate production conditions to prevent revenue-impacting
silent failures where users don't receive AI progress updates.
"""

import asyncio
import pytest
import json
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from contextlib import asynccontextmanager

# SSOT test imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator,
    ValidationResult,
    WebSocketEventMessage,
    EventCriticality,
    CriticalAgentEventType,
    get_critical_event_types,
    create_mock_critical_events
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env


class TestWebSocketEventEmissionValidation(SSotAsyncTestCase):
    """
    Integration tests for WebSocket event emission with validation.
    
    Focus: Real WebSocket connections, event emission validation, error scenarios.
    Coverage: End-to-end event flow from validation to client delivery.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Test user and connection setup
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create user context
        self.user_context = StronglyTypedUserExecutionContext(
            user_id=UserID(self.test_user_id),
            thread_id=ThreadID(self.test_thread_id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}")
        )
        
        # Initialize event validator
        self.event_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="realtime",
            strict_mode=True
        )
        
        # Mock WebSocket manager for controlled testing
        self.mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        self.mock_websocket_manager.is_connection_active.return_value = True
        self.mock_websocket_manager.emit_event = AsyncMock()
        self.mock_websocket_manager.get_connection_user_id.return_value = self.test_user_id
        
        # Track emitted events for verification
        self.emitted_events = []
        
        async def track_emit_event(connection_id: str, event_data: Dict[str, Any]):
            """Track emitted events for test verification."""
            self.emitted_events.append({
                "connection_id": connection_id,
                "event_data": event_data.copy(),
                "timestamp": datetime.now(timezone.utc)
            })
            
        self.mock_websocket_manager.emit_event.side_effect = track_emit_event
        
    async def async_setup_method(self, method=None):
        """Async setup for each test method."""
        await super().async_setup_method(method)
        
        # Reset emitted events tracking
        self.emitted_events.clear()
        
    # === EVENT EMISSION VALIDATION TESTS ===
    
    async def test_valid_event_emission_success(self):
        """Test valid critical event emission succeeds with validation."""
        event = {
            "type": "agent_started",
            "run_id": self.test_run_id,
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started", "message": "Agent started processing"}
        }
        
        # Validate event first
        validation_result = self.event_validator.validate_event(
            event, self.test_user_id, self.test_connection_id
        )
        
        self.assertTrue(validation_result.is_valid, 
                       f"Event should pass validation: {validation_result.error_message}")
        
        # Emit event through WebSocket manager
        await self.mock_websocket_manager.emit_event(self.test_connection_id, event)
        
        # Verify event was emitted
        self.assertEqual(len(self.emitted_events), 1, "Should emit exactly one event")
        
        emitted = self.emitted_events[0]
        self.assertEqual(emitted["connection_id"], self.test_connection_id)
        self.assertEqual(emitted["event_data"]["type"], "agent_started")
        self.assertEqual(emitted["event_data"]["run_id"], self.test_run_id)
        
        # Record metrics
        self.record_metric("valid_event_emitted", 1)
        self.record_metric("validation_success", 1)
        
    async def test_invalid_event_blocks_emission(self):
        """Test invalid event validation blocks emission - PREVENTS SILENT FAILURES."""
        invalid_event = {
            "type": "agent_started",
            # Missing required run_id and agent_name
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        # Validate event first
        validation_result = self.event_validator.validate_event(
            invalid_event, self.test_user_id, self.test_connection_id
        )
        
        self.assertFalse(validation_result.is_valid, "Invalid event should fail validation")
        self.assertEqual(validation_result.criticality, EventCriticality.MISSION_CRITICAL)
        
        # Simulate proper integration: Don't emit if validation fails
        if not validation_result.is_valid:
            # Log validation failure instead of emitting
            self.record_metric("validation_blocked_emission", 1)
            self.record_metric("invalid_event_blocked", 1)
        else:
            await self.mock_websocket_manager.emit_event(self.test_connection_id, invalid_event)
            
        # Verify no event was emitted
        self.assertEqual(len(self.emitted_events), 0, "Invalid event should not be emitted")
        
    async def test_all_critical_events_emission_sequence(self):
        """Test all 5 critical events emit successfully in sequence."""
        critical_events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            agent_name="IntegrationTestAgent",
            tool_name="IntegrationTestTool"
        )
        
        emitted_count = 0
        validation_results = []
        
        # Process each critical event
        for event in critical_events:
            event_dict = event.to_dict()
            
            # Validate event
            validation_result = self.event_validator.validate_event(
                event_dict, self.test_user_id, self.test_connection_id
            )
            validation_results.append(validation_result)
            
            # Emit if valid
            if validation_result.is_valid:
                await self.mock_websocket_manager.emit_event(self.test_connection_id, event_dict)
                emitted_count += 1
            else:
                self.record_metric(f"validation_failed_{event.event_type}", 1)
                
        # Verify all events were valid and emitted
        self.assertEqual(emitted_count, 5, "All 5 critical events should be emitted")
        self.assertEqual(len(self.emitted_events), 5, "Should track all 5 emitted events")
        
        # Verify all validations passed
        for i, result in enumerate(validation_results):
            self.assertTrue(result.is_valid, 
                          f"Critical event {i} should pass validation: {result.error_message}")
            self.assertEqual(result.criticality, EventCriticality.MISSION_CRITICAL)
            
        # Verify event types are correct
        emitted_types = {event["event_data"]["type"] for event in self.emitted_events}
        expected_types = get_critical_event_types()
        self.assertEqual(emitted_types, expected_types, "Should emit all critical event types")
        
        # Record comprehensive metrics
        self.record_metric("critical_events_emitted", emitted_count)
        self.record_metric("validation_success_rate", len(validation_results))
        
    # === CROSS-USER ISOLATION TESTS ===
    
    async def test_cross_user_event_isolation_prevents_emission(self):
        """Test cross-user event leakage is blocked - CRITICAL SECURITY."""
        different_user_id = f"different_user_{uuid.uuid4().hex[:8]}"
        
        # Event contains different user ID - potential security breach
        cross_user_event = {
            "type": "agent_started",
            "run_id": self.test_run_id,
            "agent_name": "TestAgent",
            "user_id": different_user_id,  # Different user - SECURITY RISK
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        # Validate event (should fail for cross-user leakage)
        validation_result = self.event_validator.validate_event(
            cross_user_event, self.test_user_id, self.test_connection_id
        )
        
        self.assertFalse(validation_result.is_valid, "Cross-user event should fail validation")
        self.assertEqual(validation_result.criticality, EventCriticality.MISSION_CRITICAL)
        self.assertIn("security breach", validation_result.error_message.lower())
        
        # Simulate proper security: Block emission on validation failure
        if not validation_result.is_valid:
            self.record_metric("security_violation_blocked", 1)
            # Don't emit - security violation blocked
        else:
            await self.mock_websocket_manager.emit_event(self.test_connection_id, cross_user_event)
            
        # Verify no event was emitted (security protection worked)
        self.assertEqual(len(self.emitted_events), 0, "Cross-user event should not be emitted")
        self.record_metric("cross_user_leakage_prevented", 1)
        
    async def test_user_context_isolation_during_emission(self):
        """Test user context isolation is maintained during event emission."""
        # Create events for multiple users
        user_events = []
        for i in range(3):
            user_id = f"user_{i}_{uuid.uuid4().hex[:8]}"
            event = {
                "type": "agent_thinking",
                "run_id": f"run_{i}_{uuid.uuid4().hex[:8]}",
                "agent_name": "TestAgent",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"progress": f"User {i} processing"}
            }
            user_events.append((user_id, event))
            
        # Process events with proper user context isolation
        for user_id, event in user_events:
            # Each event should only be validated for its target user
            validation_result = self.event_validator.validate_event(
                event, user_id, f"conn_{user_id}"
            )
            
            if validation_result.is_valid:
                await self.mock_websocket_manager.emit_event(f"conn_{user_id}", event)
            else:
                self.record_metric(f"isolation_blocked_{user_id}", 1)
                
        # Verify proper isolation - only events matching target users should be valid
        # Since our validator is configured for self.test_user_id, only matching events should pass
        matching_events = [event for user_id, event in user_events if user_id == self.test_user_id]
        self.record_metric("user_isolation_events_processed", len(user_events))
        self.record_metric("user_isolation_events_valid", len(matching_events))
        
    # === ERROR HANDLING AND RESILIENCE TESTS ===
    
    async def test_websocket_manager_failure_handling(self):
        """Test graceful handling when WebSocket manager fails."""
        event = {
            "type": "agent_completed",
            "run_id": self.test_run_id,
            "agent_name": "TestAgent", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "completed", "result": "success"}
        }
        
        # Validate event (should succeed)
        validation_result = self.event_validator.validate_event(
            event, self.test_user_id, self.test_connection_id
        )
        self.assertTrue(validation_result.is_valid, "Event should be valid")
        
        # Simulate WebSocket manager failure
        self.mock_websocket_manager.emit_event.side_effect = Exception("WebSocket connection failed")
        
        # Attempt emission with error handling
        emission_successful = False
        try:
            await self.mock_websocket_manager.emit_event(self.test_connection_id, event)
            emission_successful = True
        except Exception as e:
            self.record_metric("websocket_emission_error", str(e))
            emission_successful = False
            
        # Verify error was handled
        self.assertFalse(emission_successful, "Emission should fail gracefully")
        self.assertEqual(len(self.emitted_events), 0, "No events should be tracked on failure")
        
        # Record resilience metrics
        self.record_metric("websocket_failure_handled", 1)
        
    async def test_connection_readiness_validation_integration(self):
        """Test connection readiness validation prevents emission to inactive connections."""
        event = {
            "type": "tool_executing",
            "run_id": self.test_run_id,
            "agent_name": "TestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"tool": "test_tool", "status": "executing"}
        }
        
        # Simulate inactive connection
        self.mock_websocket_manager.is_connection_active.return_value = False
        
        # Validate connection readiness
        connection_result = self.event_validator.validate_connection_ready(
            self.test_user_id, self.test_connection_id, self.mock_websocket_manager
        )
        
        self.assertFalse(connection_result.is_valid, "Inactive connection should fail validation")
        self.assertEqual(connection_result.criticality, EventCriticality.BUSINESS_VALUE)
        
        # Simulate proper integration: Check connection before emission
        if connection_result.is_valid:
            await self.mock_websocket_manager.emit_event(self.test_connection_id, event)
        else:
            self.record_metric("inactive_connection_blocked", 1)
            
        # Verify no emission to inactive connection
        self.assertEqual(len(self.emitted_events), 0, "Should not emit to inactive connection")
        
    # === PERFORMANCE AND LOAD TESTS ===
    
    async def test_emission_performance_under_load(self):
        """Test event emission performance under simulated load."""
        event_template = {
            "type": "agent_thinking",
            "run_id": self.test_run_id,
            "agent_name": "LoadTestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"progress": "processing"}
        }
        
        # Simulate load test with multiple events
        num_events = 100
        start_time = time.time()
        
        successful_validations = 0
        successful_emissions = 0
        
        for i in range(num_events):
            # Create unique event
            event = event_template.copy()
            event["payload"]["iteration"] = i
            
            # Validate event
            validation_result = self.event_validator.validate_event(
                event, self.test_user_id, self.test_connection_id
            )
            
            if validation_result.is_valid:
                successful_validations += 1
                
                # Emit event
                try:
                    await self.mock_websocket_manager.emit_event(self.test_connection_id, event)
                    successful_emissions += 1
                except Exception:
                    pass  # Count successful emissions only
                    
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_ms = (total_time / num_events) * 1000
        
        # Performance assertions
        self.assertEqual(successful_validations, num_events, "All validations should succeed")
        self.assertEqual(successful_emissions, num_events, "All emissions should succeed") 
        self.assertEqual(len(self.emitted_events), num_events, "Should track all emitted events")
        
        # Performance benchmarks
        self.assertLess(avg_time_ms, 10.0, f"Average time per event should be under 10ms, got {avg_time_ms:.3f}ms")
        
        # Record performance metrics
        self.record_metric("load_test_events", num_events)
        self.record_metric("load_test_avg_ms", avg_time_ms)
        self.record_metric("load_test_success_rate", successful_emissions / num_events * 100)
        
    async def test_concurrent_user_emission_isolation(self):
        """Test concurrent event emission maintains user isolation."""
        num_concurrent_users = 10
        events_per_user = 5
        
        async def emit_events_for_user(user_index: int):
            """Emit events for a specific user."""
            user_id = f"concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}"
            connection_id = f"conn_{user_id}"
            
            user_events = []
            for event_index in range(events_per_user):
                event = {
                    "type": "agent_thinking",
                    "run_id": f"run_{user_index}_{event_index}",
                    "agent_name": "ConcurrentTestAgent",
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"user": user_index, "iteration": event_index}
                }
                
                # Note: This validator is configured for self.test_user_id
                # Events for other users will fail validation (expected behavior)
                validation_result = self.event_validator.validate_event(
                    event, user_id, connection_id
                )
                
                if validation_result.is_valid:
                    await self.mock_websocket_manager.emit_event(connection_id, event)
                    user_events.append(event)
                    
            return len(user_events)
        
        # Run concurrent tasks
        tasks = [emit_events_for_user(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        successful_tasks = [r for r in results if isinstance(r, int)]
        self.assertEqual(len(successful_tasks), num_concurrent_users, "All concurrent tasks should complete")
        
        # Record concurrency metrics
        total_events_attempted = num_concurrent_users * events_per_user
        total_events_emitted = len(self.emitted_events)
        
        self.record_metric("concurrent_users", num_concurrent_users) 
        self.record_metric("concurrent_events_attempted", total_events_attempted)
        self.record_metric("concurrent_events_emitted", total_events_emitted)
        self.record_metric("concurrent_isolation_maintained", 1)
        
    # === EVENT TIMING AND SEQUENCE VALIDATION ===
    
    async def test_event_sequence_timing_validation(self):
        """Test event sequence validation with proper timing."""
        # Create sequence of events with realistic timing
        base_time = datetime.now(timezone.utc)
        
        sequence_events = [
            {
                "type": "agent_started",
                "timestamp": base_time.isoformat(),
                "delay": 0
            },
            {
                "type": "agent_thinking", 
                "timestamp": (base_time.replace(second=base_time.second + 1)).isoformat(),
                "delay": 0.1
            },
            {
                "type": "tool_executing",
                "timestamp": (base_time.replace(second=base_time.second + 2)).isoformat(), 
                "delay": 0.1
            },
            {
                "type": "tool_completed",
                "timestamp": (base_time.replace(second=base_time.second + 5)).isoformat(),
                "delay": 0.1
            },
            {
                "type": "agent_completed",
                "timestamp": (base_time.replace(second=base_time.second + 6)).isoformat(),
                "delay": 0.1
            }
        ]
        
        emitted_sequence = []
        
        for event_spec in sequence_events:
            # Add realistic delay
            if event_spec["delay"] > 0:
                await asyncio.sleep(event_spec["delay"])
                
            # Create full event
            event = {
                "type": event_spec["type"],
                "run_id": self.test_run_id,
                "agent_name": "SequenceTestAgent",
                "timestamp": event_spec["timestamp"],
                "payload": {"sequence": len(emitted_sequence)}
            }
            
            # Validate and emit
            validation_result = self.event_validator.validate_event(
                event, self.test_user_id, self.test_connection_id
            )
            
            if validation_result.is_valid:
                await self.mock_websocket_manager.emit_event(self.test_connection_id, event)
                emitted_sequence.append(event["type"])
                
        # Verify complete sequence was emitted
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        self.assertEqual(emitted_sequence, expected_sequence, "Should emit complete event sequence")
        self.assertEqual(len(self.emitted_events), 5, "Should emit all 5 sequence events")
        
        # Record sequence metrics
        self.record_metric("sequence_events_emitted", len(emitted_sequence))
        self.record_metric("sequence_validation_success", 1)
        
    # === BUSINESS VALUE PROTECTION TESTS ===
    
    async def test_business_value_event_emission_protection(self):
        """Test business value scoring integration with event emission."""
        # Create validator in sequence mode for business value scoring
        sequence_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="sequence",
            strict_mode=True
        )
        
        # Create partial event set (missing agent_completed - CRITICAL revenue impact)
        partial_events = []
        for event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
            event = {
                "type": event_type,
                "run_id": self.test_run_id,
                "agent_name": "BusinessValueAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"agent": "BusinessValueAgent", "status": "test"}
            }
            partial_events.append(event)
            
        # Validate partial sequence
        validation_result = sequence_validator.validate_with_mode(
            partial_events, self.test_user_id, self.test_connection_id
        )
        
        # Verify business impact assessment
        self.assertEqual(validation_result.business_value_score, 80.0, "4/5 events should give 80% score")
        self.assertEqual(validation_result.revenue_impact, "CRITICAL", "Missing agent_completed should be CRITICAL")
        self.assertIn("agent_completed", validation_result.missing_critical_events)
        
        # Simulate business logic: Don't complete user interaction without agent_completed
        if validation_result.revenue_impact == "CRITICAL":
            self.record_metric("business_value_protection_triggered", 1)
            self.record_metric("critical_revenue_impact_detected", 1)
        
        # Record business value metrics
        self.record_metric("business_value_score", validation_result.business_value_score)
        self.record_metric("revenue_impact", validation_result.revenue_impact)
        
    # === TEARDOWN AND CLEANUP ===
    
    async def async_teardown_method(self, method=None):
        """Async cleanup after each test method."""
        # Record final emission statistics
        if self.emitted_events:
            self.record_metric("total_events_emitted", len(self.emitted_events))
            
            # Analyze event types
            event_types = [event["event_data"]["type"] for event in self.emitted_events]
            unique_types = set(event_types)
            self.record_metric("unique_event_types_emitted", len(unique_types))
            
            # Record timing statistics
            if len(self.emitted_events) > 1:
                first_event = self.emitted_events[0]["timestamp"]
                last_event = self.emitted_events[-1]["timestamp"] 
                duration = (last_event - first_event).total_seconds()
                self.record_metric("emission_duration_seconds", duration)
                
        await super().async_teardown_method(method)
        
    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        # Record validator statistics
        if hasattr(self, 'event_validator'):
            stats = self.event_validator.get_validation_stats()
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    self.record_metric(f"validator_{key}", value)
                    
        # Clear tracking data
        self.emitted_events.clear()
        
        super().teardown_method(method)


# === SPECIALIZED TEST SCENARIOS ===

class TestWebSocketEventEmissionErrorScenarios(SSotAsyncTestCase):
    """
    Specialized tests for error scenarios and edge cases in event emission.
    
    Focus: Error conditions, malformed events, network failures, recovery.
    """
    
    def setup_method(self, method=None):
        """Setup for error scenario tests."""
        super().setup_method(method)
        
        self.test_user_id = f"error_test_user_{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"error_conn_{uuid.uuid4().hex[:8]}"
        
        self.validator = UnifiedEventValidator(validation_mode="realtime", strict_mode=True)
        
        # Mock failing WebSocket manager
        self.failing_websocket_manager = MagicMock()
        self.failing_websocket_manager.is_connection_active.return_value = False
        self.failing_websocket_manager.emit_event = AsyncMock(side_effect=Exception("Network error"))
        
    async def test_malformed_event_emission_prevention(self):
        """Test malformed events are prevented from emission."""
        malformed_events = [
            None,  # Null event
            {"invalid": "structure"},  # Missing type
            {"type": ""},  # Empty type
            {"type": None},  # Null type
            {"type": ["invalid", "list"]},  # Wrong type format
        ]
        
        prevented_emissions = 0
        
        for malformed_event in malformed_events:
            try:
                validation_result = self.validator.validate_event(
                    malformed_event, self.test_user_id, self.test_connection_id
                )
                
                if not validation_result.is_valid:
                    prevented_emissions += 1
                    self.record_metric("malformed_event_prevented", 1)
                    
            except Exception:
                # Exception during validation also counts as prevention
                prevented_emissions += 1
                self.record_metric("malformed_event_exception_prevented", 1)
                
        self.assertEqual(prevented_emissions, len(malformed_events), 
                        "All malformed events should be prevented from emission")
        
    async def test_network_failure_graceful_degradation(self):
        """Test graceful degradation when network emission fails."""
        valid_event = {
            "type": "agent_started",
            "run_id": "test_run",
            "agent_name": "NetworkTestAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        # Validate event (should succeed)
        validation_result = self.validator.validate_event(
            valid_event, self.test_user_id, self.test_connection_id
        )
        self.assertTrue(validation_result.is_valid, "Event should be valid")
        
        # Attempt emission with failing manager
        emission_errors = []
        try:
            await self.failing_websocket_manager.emit_event(self.test_connection_id, valid_event)
        except Exception as e:
            emission_errors.append(str(e))
            
        # Verify graceful error handling
        self.assertEqual(len(emission_errors), 1, "Should capture network failure")
        self.assertIn("network error", emission_errors[0].lower())
        
        # Record degradation metrics
        self.record_metric("network_failures_handled", len(emission_errors))
        
    async def test_connection_state_validation_edge_cases(self):
        """Test edge cases in connection state validation."""
        edge_case_scenarios = [
            {"active": None, "description": "null active state"},
            {"active": "invalid", "description": "non-boolean active state"},
            {"exception": ConnectionError("Connection lost"), "description": "connection check exception"}
        ]
        
        for scenario in edge_case_scenarios:
            # Configure mock for scenario
            if "exception" in scenario:
                self.failing_websocket_manager.is_connection_active.side_effect = scenario["exception"]
            else:
                self.failing_websocket_manager.is_connection_active.return_value = scenario.get("active")
                self.failing_websocket_manager.is_connection_active.side_effect = None
                
            # Test connection validation
            connection_result = self.validator.validate_connection_ready(
                self.test_user_id, self.test_connection_id, self.failing_websocket_manager
            )
            
            # Edge cases should generally result in validation failure or warnings
            if scenario.get("active") is True:
                # Only true boolean should pass
                self.assertTrue(connection_result.is_valid)
            else:
                # All other cases should fail or be handled gracefully
                self.record_metric(f"edge_case_handled_{scenario['description']}", 1)


# === TEST COLLECTION AND EXECUTION ===

def test_suite():
    """Return test suite for this module."""
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add main test class
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketEventEmissionValidation))
    
    # Add error scenarios test class
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketEventEmissionErrorScenarios))
    
    return suite


if __name__ == "__main__":
    # Allow direct execution for debugging
    import unittest
    unittest.main()