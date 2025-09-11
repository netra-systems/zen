"""
WebSocket Event Typo Prevention - Mission Critical Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - $500K+ ARR Revenue Protection
- Business Goal: Prevent silent failures that block revenue-generating chat interactions  
- Value Impact: Bulletproof typo detection for 5 critical events delivering 90% of platform value
- Strategic Impact: MISSION CRITICAL - These tests protect the primary revenue stream

Mission: Prevent typos in critical WebSocket event names that would cause silent failures,
blocking users from seeing AI value delivery and resulting in immediate revenue loss.

CRITICAL: These tests are based on real production failures identified in 
CRITICAL_BRITTLE_POINTS_AUDIT_20250110 where event name typos caused:
- Users not seeing agent progress
- Silent agent execution failures  
- Complete chat functionality breakdown
- Immediate customer churn and revenue loss

These tests MUST catch:
1. ALL possible typos in the 5 critical event names
2. Silent failure scenarios where typos cause events to be dropped
3. Performance degradation from incorrect event handling
4. Cross-user contamination when events are misrouted due to typos

REVENUE PROTECTION: Each test failure represents a potential revenue loss incident.
"""

import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from dataclasses import dataclass

# SSOT test imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.event_validator import (
    UnifiedEventValidator,
    ValidationResult, 
    WebSocketEventMessage,
    EventCriticality,
    CriticalAgentEventType,
    get_critical_event_types,
    create_mock_critical_events,
    assert_critical_events_received
)
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID


@dataclass
class TypoTestCase:
    """Test case for typo detection."""
    correct_event: str
    typo_variations: List[str]
    expected_behavior: str  # "block" or "warn" or "pass"
    business_impact: str
    revenue_risk: str


class TestWebSocketEventTypoPrevention(SSotAsyncTestCase):
    """
    Mission Critical Tests for WebSocket Event Typo Prevention.
    
    These tests protect $500K+ ARR by ensuring event name typos are detected
    and handled appropriately to prevent revenue-impacting silent failures.
    
    Focus: Comprehensive typo detection, business impact assessment, performance.
    Coverage: All critical event typos, edge cases, failure scenarios.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method with revenue protection context."""
        super().setup_method(method)
        
        # Business context setup
        self.test_user_id = f"revenue_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"revenue_thread_{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"revenue_conn_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"revenue_run_{uuid.uuid4().hex[:8]}"
        
        # Create user context for revenue-generating interaction
        self.user_context = StronglyTypedUserExecutionContext(
            user_id=UserID(self.test_user_id),
            thread_id=ThreadID(self.test_thread_id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}")
        )
        
        # Initialize strict validator for revenue protection
        self.revenue_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="realtime",
            strict_mode=True  # CRITICAL: Strict mode for revenue protection
        )
        
        # Define comprehensive typo test cases based on production failures
        self.typo_test_cases = [
            TypoTestCase(
                correct_event="agent_started",
                typo_variations=[
                    "agnt_started",     # Missing 'e' - COMMON PRODUCTION TYPO
                    "agent_stared",     # Missing 't' - KEYBOARD SLIP  
                    "agent_start",      # Missing 'ed' - INCOMPLETE TYPING
                    "agentstarted",     # Missing underscore - STYLE INCONSISTENCY
                    "Agent_Started",    # Wrong capitalization - CASE SENSITIVITY
                    "agent_starting",   # Wrong tense - LOGIC CONFUSION
                    "agent_statred",    # Transposed letters - TYPING ERROR
                    "agent_startd",     # Missing vowel - FAST TYPING
                    "aget_started",     # Missing 'n' - KEYBOARD MISS
                    "agent_sarted"      # Missing 't' in middle - PRODUCTION CASE
                ],
                expected_behavior="block",
                business_impact="Users don't see AI agent initialization - appears broken",
                revenue_risk="HIGH - First impression failure leads to immediate churn"
            ),
            TypoTestCase(
                correct_event="agent_thinking",
                typo_variations=[
                    "agent_thinkng",    # Missing 'i' - COMMON PRODUCTION TYPO
                    "agent_thinkiing",  # Doubled 'i' - OVERTYPE ERROR
                    "agentthinking",    # Missing underscore - STYLE MISTAKE
                    "agent_thinkign",   # Transposed letters - TYPING SPEED ERROR
                    "agent_thinkin",    # Missing 'g' - INCOMPLETE
                    "agent_thinkingg",  # Extra 'g' - OVERTYPE  
                    "agent_thining",    # Missing 'k' - KEYBOARD SKIP
                    "agent_hinking",    # Wrong first letter - ADJACENT KEY
                    "agnet_thinking",   # Transposed in 'agent' - SPEED TYPO
                    "agent_thkning"     # Missing vowel - CONSONANT CLUSTER
                ],
                expected_behavior="block",
                business_impact="Users don't see AI reasoning progress - appears stalled", 
                revenue_risk="CRITICAL - Users assume AI is broken and abandon session"
            ),
            TypoTestCase(
                correct_event="tool_executing",
                typo_variations=[
                    "tool_executng",    # Missing 'i' - FREQUENT PRODUCTION ERROR
                    "toolexecuting",    # Missing underscore - CONCATENATION
                    "tool_execute",     # Missing 'ing' - WRONG FORM
                    "tool_executeing",  # Extra 'e' - DOUBLE TYPING
                    "tool_exeucting",   # Transposed letters - SPEED ERROR
                    "tool_executingg",  # Extra 'g' - OVERTYPE
                    "tol_executing",    # Missing 'o' - KEYBOARD MISS
                    "tool_executnig",   # Transposed ending - COMMON PATTERN
                    "too_executing",    # Wrong letter - ADJACENT KEY
                    "tool_execuing"     # Missing 't' - CONSONANT SKIP
                ],
                expected_behavior="block", 
                business_impact="Users don't see tool usage - AI appears inactive",
                revenue_risk="HIGH - Tool transparency critical for user trust"
            ),
            TypoTestCase(
                correct_event="tool_completed",
                typo_variations=[
                    "tool_completd",    # Missing 'e' - COMMON OMISSION
                    "toolcompleted",    # Missing underscore - CONCATENATION ERROR
                    "tool_complete",    # Missing 'd' - WRONG TENSE
                    "tool_completeed",  # Extra 'e' - DOUBLE TYPE
                    "tool_complted",    # Missing 'e' in middle - SPEED ERROR
                    "tool_compelted",   # Transposed letters - TYPING MISTAKE
                    "tol_completed",    # Missing 'o' - KEYBOARD SKIP
                    "tool_compleetd",   # Multiple errors - FAST TYPING
                    "tool_comleted",    # Missing 'p' - CONSONANT CLUSTER
                    "tool_completde"    # Transposed ending - PATTERN ERROR
                ],
                expected_behavior="block",
                business_impact="Users don't see tool results - AI appears to fail",
                revenue_risk="CRITICAL - Tool completion signals value delivery"
            ),
            TypoTestCase(
                correct_event="agent_completed",
                typo_variations=[
                    "agent_completd",   # Missing 'e' - CONSISTENT WITH TOOL_COMPLETED
                    "agentcompleted",   # Missing underscore - CONCATENATION  
                    "agent_complete",   # Missing 'd' - TENSE CONFUSION
                    "agent_completeed", # Extra 'e' - OVERTYPE ERROR
                    "agent_complted",   # Missing 'e' in middle - SPEED TYPO
                    "agent_compelted",  # Transposed letters - MUSCLE MEMORY
                    "agnet_completed",  # Transposed in 'agent' - PREFIX ERROR
                    "agent_compleetd",  # Multiple vowel errors - FAST TYPING
                    "agent_comleted",   # Missing 'p' - CONSONANT SKIP  
                    "agent_completde"   # Transposed ending - SUFFIX PATTERN
                ],
                expected_behavior="block",
                business_impact="Users never know AI finished - session appears hung",
                revenue_risk="CRITICAL - agent_completed is the revenue completion signal"
            )
        ]
        
        # Revenue impact tracking
        self.revenue_incidents_prevented = 0
        self.typos_detected = 0
        self.silent_failures_prevented = 0
        
    # === COMPREHENSIVE TYPO DETECTION TESTS ===
    
    def test_all_critical_event_typos_detected(self):
        """Test ALL typo variations for ALL critical events are detected - COMPREHENSIVE PROTECTION."""
        total_typos_tested = 0
        total_typos_detected = 0
        
        for test_case in self.typo_test_cases:
            for typo in test_case.typo_variations:
                total_typos_tested += 1
                
                # Create event with typo
                typo_event = {
                    "type": typo,  # TYPO EVENT NAME
                    "run_id": self.test_run_id,
                    "agent_name": "TypoTestAgent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"status": "test", "typo_test": True}
                }
                
                # Validate event - typo should NOT be classified as mission critical
                validation_result = self.revenue_validator.validate_event(
                    typo_event, self.test_user_id, self.test_connection_id
                )
                
                # Log each typo for audit trail
                self.record_metric(f"typo_test_{test_case.correct_event}_{typo}", "detected" if validation_result.is_valid else "blocked")
                
                # CRITICAL ASSERTION: Typo should not be treated as mission critical event
                if validation_result.is_valid:
                    # If event is valid, it should NOT be mission critical (typo detected)
                    if validation_result.criticality != EventCriticality.MISSION_CRITICAL:
                        total_typos_detected += 1
                        self.typos_detected += 1
                        self.record_metric(f"typo_detected_{test_case.correct_event}", typo)
                        
                        # Verify business value score reflects missing critical event
                        self.assertLess(validation_result.business_value_score, 100.0,
                                       f"Typo '{typo}' should reduce business value score")
                    else:
                        # CRITICAL FAILURE: Typo was treated as mission critical (revenue risk)
                        self.record_metric(f"REVENUE_RISK_typo_missed_{test_case.correct_event}", typo)
                        assert False, f"REVENUE RISK: Typo '{typo}' for '{test_case.correct_event}' was treated as mission critical!"
                else:
                    # Event validation failed completely - also counts as typo detection
                    total_typos_detected += 1
                    self.typos_detected += 1
                    
        # MISSION CRITICAL ASSERTION: All typos must be detected
        detection_rate = (total_typos_detected / total_typos_tested) * 100 if total_typos_tested > 0 else 0
        
        self.assertEqual(total_typos_detected, total_typos_tested,
                        f"ALL typos must be detected! Detected {total_typos_detected}/{total_typos_tested} ({detection_rate:.1f}%)")
        
        # Record comprehensive metrics
        self.record_metric("total_typos_tested", total_typos_tested)
        self.record_metric("typo_detection_rate", detection_rate)
        self.record_metric("revenue_protection_effective", detection_rate == 100.0)
        
    def test_typo_vs_correct_event_classification(self):
        """Test typos vs correct events have different classification - BEHAVIORAL VERIFICATION."""
        classification_tests = []
        
        for test_case in self.typo_test_cases:
            # Test correct event
            correct_event = {
                "type": test_case.correct_event,
                "run_id": self.test_run_id,
                "agent_name": "CorrectTestAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "correct_test"}
            }
            
            correct_result = self.revenue_validator.validate_event(
                correct_event, self.test_user_id, self.test_connection_id
            )
            
            # Test first typo from each category
            typo_event = {
                "type": test_case.typo_variations[0],  # First typo
                "run_id": self.test_run_id,
                "agent_name": "TypoTestAgent", 
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"status": "typo_test"}
            }
            
            typo_result = self.revenue_validator.validate_event(
                typo_event, self.test_user_id, self.test_connection_id
            )
            
            # Record classification test
            classification_tests.append({
                "correct_event": test_case.correct_event,
                "typo": test_case.typo_variations[0],
                "correct_critical": correct_result.criticality == EventCriticality.MISSION_CRITICAL,
                "typo_critical": typo_result.criticality == EventCriticality.MISSION_CRITICAL if typo_result.is_valid else False,
                "correct_business_score": correct_result.business_value_score,
                "typo_business_score": typo_result.business_value_score if typo_result.is_valid else 0.0
            })
            
            # CRITICAL ASSERTIONS: Correct vs Typo Classification
            if correct_result.is_valid and typo_result.is_valid:
                # Both valid - but should have different criticality
                self.assertTrue(correct_result.criticality == EventCriticality.MISSION_CRITICAL,
                               f"Correct event '{test_case.correct_event}' should be mission critical")
                
                self.assertFalse(typo_result.criticality == EventCriticality.MISSION_CRITICAL,
                                f"Typo '{test_case.typo_variations[0]}' should NOT be mission critical")
                
                # Business value should be different
                self.assertGreater(correct_result.business_value_score, typo_result.business_value_score,
                                  f"Correct event should have higher business value than typo")
                                  
        # Record classification metrics
        self.record_metric("classification_tests_performed", len(classification_tests))
        
        correct_classified = sum(1 for test in classification_tests if test["correct_critical"])
        typo_misclassified = sum(1 for test in classification_tests if test["typo_critical"])
        
        self.record_metric("correct_events_classified_critical", correct_classified)
        self.record_metric("typos_misclassified_critical", typo_misclassified)
        
        # MISSION CRITICAL: No typos should be misclassified as critical
        self.assertEqual(typo_misclassified, 0, "No typos should be misclassified as mission critical")
        
    # === SILENT FAILURE PREVENTION TESTS ===
    
    def test_typo_events_prevent_silent_business_value_loss(self):
        """Test typo events don't silently contribute to business value - REVENUE PROTECTION."""
        # Create complete set of correct events
        correct_events = create_mock_critical_events(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            agent_name="BusinessValueAgent"
        )
        
        # Create set with one typo (agent_completed -> agent_completd)
        typo_events = []
        for event in correct_events:
            event_dict = event.to_dict()
            if event_dict["type"] == "agent_completed":
                event_dict["type"] = "agent_completd"  # TYPO
            typo_events.append(event_dict)
            
        # Test with sequence validator for business value scoring
        sequence_validator = UnifiedEventValidator(
            user_context=self.user_context,
            validation_mode="sequence",
            strict_mode=True
        )
        
        # Validate correct event set
        correct_result = sequence_validator.validate_with_mode(
            [event.to_dict() for event in correct_events], 
            self.test_user_id, 
            self.test_connection_id
        )
        
        # Validate typo event set
        sequence_validator.reset_stats()  # Reset for clean test
        typo_result = sequence_validator.validate_with_mode(
            typo_events,
            self.test_user_id,
            self.test_connection_id
        )
        
        # CRITICAL BUSINESS VALUE ASSERTIONS
        self.assertEqual(correct_result.business_value_score, 100.0, 
                        "Correct events should give 100% business value")
        self.assertEqual(correct_result.revenue_impact, "NONE",
                        "Correct events should have no revenue impact")
        
        # Typo set should have reduced business value
        self.assertLess(typo_result.business_value_score, correct_result.business_value_score,
                       "Typo events should reduce business value score")
        
        # agent_completed typo should cause CRITICAL revenue impact
        if "agent_completd" in [event["type"] for event in typo_events]:
            self.assertIn("CRITICAL", typo_result.revenue_impact,
                         "Missing correct agent_completed due to typo should be CRITICAL impact")
            
        # Record revenue protection metrics
        business_value_loss = correct_result.business_value_score - typo_result.business_value_score
        self.record_metric("business_value_loss_prevented", business_value_loss)
        self.record_metric("revenue_impact_escalation", typo_result.revenue_impact)
        self.silent_failures_prevented += 1
        
    def test_typo_events_excluded_from_critical_event_count(self):
        """Test typo events are not counted toward critical event requirements - COUNTING PROTECTION."""
        critical_event_types = get_critical_event_types()
        
        for correct_event_type in critical_event_types:
            # Find typos for this event type
            test_case = next((tc for tc in self.typo_test_cases if tc.correct_event == correct_event_type), None)
            if not test_case:
                continue
                
            # Create mixed set: 4 correct events + 1 typo (instead of 5 correct)
            mixed_events = []
            
            # Add 4 correct critical events (excluding the one we'll replace with typo)
            for event_type in critical_event_types:
                if event_type != correct_event_type:
                    event = {
                        "type": event_type,
                        "run_id": self.test_run_id,
                        "agent_name": "MixedTestAgent",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {"agent": "MixedTestAgent", "status": "correct"}
                    }
                    mixed_events.append(event)
                    
            # Add typo event instead of correct event
            typo_event = {
                "type": test_case.typo_variations[0],  # First typo
                "run_id": self.test_run_id,
                "agent_name": "MixedTestAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"agent": "MixedTestAgent", "status": "typo"}
            }
            mixed_events.append(typo_event)
            
            # Validate mixed set with sequence validator
            sequence_validator = UnifiedEventValidator(
                validation_mode="sequence",
                strict_mode=True
            )
            
            mixed_result = sequence_validator.validate_with_mode(
                mixed_events, self.test_user_id, self.test_connection_id
            )
            
            # CRITICAL ASSERTION: Should only count 4 critical events, not 5
            expected_score = 80.0  # 4 out of 5 critical events
            self.assertEqual(mixed_result.business_value_score, expected_score,
                           f"Mixed set with typo '{test_case.typo_variations[0]}' should score {expected_score}%, not 100%")
            
            # Should show missing critical event
            self.assertIn(correct_event_type, mixed_result.missing_critical_events,
                         f"Typo replacement should show '{correct_event_type}' as missing")
                         
            # Record counting protection
            self.record_metric(f"counting_protection_{correct_event_type}", "effective")
            break  # Test one case for performance
            
    # === PERFORMANCE IMPACT TESTS ===
    
    def test_typo_validation_performance_impact(self):
        """Test typo validation doesn't significantly impact performance - SLA PROTECTION."""
        # Performance baseline with correct events
        correct_event = {
            "type": "agent_started",
            "run_id": self.test_run_id,
            "agent_name": "PerformanceAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        # Warm up
        for _ in range(10):
            self.revenue_validator.validate_event(correct_event, self.test_user_id, self.test_connection_id)
            
        # Baseline performance test
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.revenue_validator.validate_event(correct_event, self.test_user_id, self.test_connection_id)
            self.assertTrue(result.is_valid)
            
        baseline_time = time.time() - start_time
        baseline_avg_ms = (baseline_time / iterations) * 1000
        
        # Typo performance test
        typo_event = {
            "type": "agnt_started",  # Typo
            "run_id": self.test_run_id,
            "agent_name": "PerformanceAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started"}
        }
        
        start_time = time.time()
        
        for _ in range(iterations):
            result = self.revenue_validator.validate_event(typo_event, self.test_user_id, self.test_connection_id)
            # Typo events may be valid but not mission critical
            
        typo_time = time.time() - start_time  
        typo_avg_ms = (typo_time / iterations) * 1000
        
        # Performance impact analysis
        performance_impact = ((typo_avg_ms - baseline_avg_ms) / baseline_avg_ms) * 100
        
        # PERFORMANCE ASSERTIONS
        self.assertLess(baseline_avg_ms, 1.0, f"Baseline validation should be under 1ms, got {baseline_avg_ms:.3f}ms")
        self.assertLess(typo_avg_ms, 2.0, f"Typo validation should be under 2ms, got {typo_avg_ms:.3f}ms") 
        self.assertLess(performance_impact, 100.0, f"Typo validation overhead should be under 100%, got {performance_impact:.1f}%")
        
        # Record performance metrics
        self.record_metric("baseline_validation_ms", baseline_avg_ms)
        self.record_metric("typo_validation_ms", typo_avg_ms)
        self.record_metric("performance_impact_percent", performance_impact)
        
    # === CROSS-USER CONTAMINATION PREVENTION ===
    
    def test_typo_events_prevent_cross_user_contamination(self):
        """Test typos don't cause cross-user event contamination - SECURITY PROTECTION."""
        # Create two different users
        user_a_id = f"user_a_{uuid.uuid4().hex[:8]}"
        user_b_id = f"user_b_{uuid.uuid4().hex[:8]}"
        
        # Create event with typo that might cause misrouting
        typo_event_for_user_a = {
            "type": "agnt_started",  # Typo that might bypass user validation
            "run_id": self.test_run_id,
            "agent_name": "ContaminationTestAgent",
            "user_id": user_b_id,  # Event claims to be for user B
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started", "contamination_test": True}
        }
        
        # Validate for user A (should fail due to user mismatch + typo)
        validation_result = self.revenue_validator.validate_event(
            typo_event_for_user_a, user_a_id, f"conn_{user_a_id}"
        )
        
        # CRITICAL SECURITY ASSERTION: Should fail validation
        self.assertFalse(validation_result.is_valid,
                        "Typo event with cross-user contamination should FAIL validation")
        
        if not validation_result.is_valid:
            self.assertIn("cross-user", validation_result.error_message.lower())
            self.assertEqual(validation_result.criticality, EventCriticality.MISSION_CRITICAL)
            
        # Record security protection
        self.record_metric("cross_user_contamination_prevented", 1)
        
    # === PRODUCTION SCENARIO SIMULATION ===
    
    def test_production_typo_scenarios_comprehensive(self):
        """Test realistic production typo scenarios - REAL WORLD PROTECTION."""
        production_scenarios = [
            {
                "scenario": "Developer fast typing in production deployment",
                "events": [
                    {"type": "agent_started", "status": "correct"},
                    {"type": "agent_thinkng", "status": "typo_missing_i"},  # Fast typing typo
                    {"type": "tool_executing", "status": "correct"},
                    {"type": "tool_completd", "status": "typo_missing_e"},  # Common omission
                    {"type": "agent_completed", "status": "correct"}
                ],
                "expected_critical_count": 3,  # 3 correct, 2 typos
                "expected_business_score": 60.0  # 3/5 = 60%
            },
            {
                "scenario": "Copy-paste error with concatenation",
                "events": [
                    {"type": "agentstarted", "status": "concatenation_typo"},  # Missing underscore
                    {"type": "agent_thinking", "status": "correct"},
                    {"type": "toolexecuting", "status": "concatenation_typo"},  # Missing underscore  
                    {"type": "tool_completed", "status": "correct"},
                    {"type": "agentcompleted", "status": "concatenation_typo"}  # Missing underscore
                ],
                "expected_critical_count": 2,  # Only 2 correct
                "expected_business_score": 40.0  # 2/5 = 40%
            },
            {
                "scenario": "Keyboard layout confusion (QWERTY adjacent keys)",
                "events": [
                    {"type": "agent_started", "status": "correct"},
                    {"type": "agent_thinking", "status": "correct"}, 
                    {"type": "tiol_executing", "status": "adjacent_key_typo"},  # 'o' instead of 'o'
                    {"type": "tool_completed", "status": "correct"},
                    {"type": "agent_completed", "status": "correct"}
                ],
                "expected_critical_count": 4,  # 4 correct, 1 typo
                "expected_business_score": 80.0  # 4/5 = 80%
            }
        ]
        
        scenarios_protected = 0
        
        for scenario in production_scenarios:
            # Create event sequence
            events = []
            for event_spec in scenario["events"]:
                event = {
                    "type": event_spec["type"],
                    "run_id": f"scenario_{scenarios_protected}",
                    "agent_name": "ProductionScenarioAgent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {"scenario": scenario["scenario"], "status": event_spec["status"]}
                }
                events.append(event)
                
            # Validate scenario with sequence validator
            sequence_validator = UnifiedEventValidator(
                validation_mode="sequence",
                strict_mode=True
            )
            
            result = sequence_validator.validate_with_mode(
                events, self.test_user_id, self.test_connection_id
            )
            
            # Verify expected business impact
            self.assertEqual(result.business_value_score, scenario["expected_business_score"],
                           f"Scenario '{scenario['scenario']}' should have {scenario['expected_business_score']}% business value")
            
            # Record scenario protection
            self.record_metric(f"production_scenario_protected", scenario["scenario"])
            scenarios_protected += 1
            
        # MISSION CRITICAL: All production scenarios should be properly handled
        self.assertEqual(scenarios_protected, len(production_scenarios), 
                        "All production scenarios should be protected")
        
    # === COMPREHENSIVE REPORTING AND METRICS ===
    
    def test_typo_detection_comprehensive_report(self):
        """Generate comprehensive typo detection report - AUDIT TRAIL."""
        report = {
            "test_execution": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_context": self.test_user_id,
                "validator_mode": "realtime_strict"
            },
            "typo_coverage": {},
            "detection_results": {},
            "business_impact_analysis": {},
            "performance_metrics": {},
            "revenue_protection_summary": {}
        }
        
        total_typos_tested = 0
        total_typos_detected = 0
        
        # Test all typo cases and generate detailed report
        for test_case in self.typo_test_cases:
            event_report = {
                "correct_event": test_case.correct_event,
                "typo_count": len(test_case.typo_variations),
                "detected_typos": [],
                "missed_typos": [],
                "business_risk": test_case.revenue_risk
            }
            
            for typo in test_case.typo_variations:
                total_typos_tested += 1
                
                # Test typo detection
                typo_event = {
                    "type": typo,
                    "run_id": f"report_{total_typos_tested}",
                    "agent_name": "ReportAgent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"report_test": True}
                }
                
                result = self.revenue_validator.validate_event(
                    typo_event, self.test_user_id, self.test_connection_id
                )
                
                if result.is_valid and result.criticality != EventCriticality.MISSION_CRITICAL:
                    # Typo detected (not classified as mission critical)
                    total_typos_detected += 1
                    event_report["detected_typos"].append({
                        "typo": typo,
                        "classification": result.criticality.value,
                        "business_score": result.business_value_score
                    })
                elif not result.is_valid:
                    # Typo caused validation failure (also detected)
                    total_typos_detected += 1
                    event_report["detected_typos"].append({
                        "typo": typo,
                        "classification": "validation_failed",
                        "error": result.error_message
                    })
                else:
                    # CRITICAL: Typo was missed (treated as mission critical)
                    event_report["missed_typos"].append({
                        "typo": typo,
                        "classification": result.criticality.value,
                        "business_score": result.business_value_score,
                        "REVENUE_RISK": "HIGH"
                    })
                    
            report["typo_coverage"][test_case.correct_event] = event_report
            
        # Calculate overall metrics
        detection_rate = (total_typos_detected / total_typos_tested) * 100 if total_typos_tested > 0 else 0
        
        report["detection_results"] = {
            "total_typos_tested": total_typos_tested,
            "total_typos_detected": total_typos_detected,
            "detection_rate_percent": detection_rate,
            "missed_typos_count": total_typos_tested - total_typos_detected
        }
        
        report["revenue_protection_summary"] = {
            "revenue_incidents_prevented": self.revenue_incidents_prevented,
            "silent_failures_prevented": self.silent_failures_prevented,
            "detection_effective": detection_rate >= 95.0,
            "mission_status": "PROTECTED" if detection_rate == 100.0 else "AT_RISK"
        }
        
        # Record comprehensive report
        self.record_metric("comprehensive_report", json.dumps(report, indent=2))
        
        # MISSION CRITICAL ASSERTION: 100% detection required for revenue protection
        self.assertEqual(detection_rate, 100.0, 
                        f"MISSION CRITICAL: 100% typo detection required for revenue protection. Got {detection_rate:.1f}%")
                        
        return report
        
    # === TEARDOWN AND FINAL METRICS ===
    
    def teardown_method(self, method=None):
        """Record final revenue protection metrics."""
        # Calculate final protection metrics
        if hasattr(self, 'revenue_validator'):
            stats = self.revenue_validator.get_validation_stats()
            
            # Calculate revenue protection effectiveness
            total_validations = stats.get("total_validations", 0)
            failed_validations = stats.get("failed_validations", 0)
            success_rate = ((total_validations - failed_validations) / total_validations * 100) if total_validations > 0 else 0
            
            self.record_metric("final_validation_success_rate", success_rate)
            self.record_metric("final_typos_detected", self.typos_detected)
            self.record_metric("final_silent_failures_prevented", self.silent_failures_prevented)
            self.record_metric("final_revenue_incidents_prevented", self.revenue_incidents_prevented)
            
        # Final revenue protection assessment
        protection_effective = (
            self.typos_detected > 0 and 
            self.silent_failures_prevented >= 0 and
            hasattr(self, 'revenue_validator')
        )
        
        self.record_metric("revenue_protection_effective", protection_effective)
        
        super().teardown_method(method)


class TestWebSocketEventTypoProductionSimulation(SSotAsyncTestCase):
    """
    Production simulation tests for typo scenarios based on real incidents.
    
    These tests simulate actual production conditions where typos have
    caused revenue-impacting failures in the past.
    """
    
    def setup_method(self, method=None):
        """Setup production simulation environment."""
        super().setup_method(method)
        
        self.production_user_id = f"prod_user_{uuid.uuid4().hex[:8]}"
        self.validator = UnifiedEventValidator(validation_mode="realtime", strict_mode=True)
        
    async def test_high_traffic_typo_detection_simulation(self):
        """Simulate high traffic conditions with random typos - LOAD TESTING."""
        import random
        
        # Common typos observed in production
        production_typos = [
            ("agent_started", ["agnt_started", "agent_stared", "agentstarted"]),
            ("agent_thinking", ["agent_thinkng", "agentthinking", "agent_thinkin"]),
            ("tool_executing", ["tool_executng", "toolexecuting", "tool_execute"]),
            ("tool_completed", ["tool_completd", "toolcompleted", "tool_complete"]),
            ("agent_completed", ["agent_completd", "agentcompleted", "agent_complete"])
        ]
        
        # Simulate high traffic with random typos
        num_events = 1000
        typo_probability = 0.15  # 15% chance of typo (realistic production rate)
        
        events_processed = 0
        typos_detected = 0
        performance_times = []
        
        for i in range(num_events):
            # Randomly select event type and possibly introduce typo
            correct_event, possible_typos = random.choice(production_typos)
            
            if random.random() < typo_probability:
                # Introduce typo
                event_type = random.choice(possible_typos)
                is_typo = True
            else:
                # Use correct event
                event_type = correct_event
                is_typo = False
                
            # Create event
            event = {
                "type": event_type,
                "run_id": f"load_test_{i}",
                "agent_name": "LoadTestAgent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"load_test": True, "iteration": i}
            }
            
            # Measure validation performance
            start_time = time.time()
            result = self.validator.validate_event(event, self.production_user_id, f"conn_{i}")
            end_time = time.time()
            
            performance_times.append((end_time - start_time) * 1000)  # ms
            events_processed += 1
            
            # Check typo detection
            if is_typo:
                if result.is_valid and result.criticality != EventCriticality.MISSION_CRITICAL:
                    typos_detected += 1
                elif not result.is_valid:
                    typos_detected += 1  # Blocked typos also count as detected
                    
        # Calculate metrics
        expected_typos = int(num_events * typo_probability)
        detection_rate = (typos_detected / expected_typos * 100) if expected_typos > 0 else 0
        avg_performance = sum(performance_times) / len(performance_times)
        
        # Performance and detection assertions
        self.assertGreater(detection_rate, 90.0, f"Should detect >90% of typos in high traffic, got {detection_rate:.1f}%")
        self.assertLess(avg_performance, 2.0, f"Average validation should be under 2ms, got {avg_performance:.3f}ms")
        
        # Record load test metrics
        self.record_metric("load_test_events", events_processed)
        self.record_metric("load_test_typo_detection_rate", detection_rate)
        self.record_metric("load_test_avg_performance_ms", avg_performance)


# === TEST COLLECTION AND EXECUTION ===

def test_suite():
    """Return test suite for this module."""
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add main typo prevention test class
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketEventTypoPrevention))
    
    # Add production simulation test class
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketEventTypoProductionSimulation))
    
    return suite


if __name__ == "__main__":
    # Allow direct execution for debugging
    import unittest
    unittest.main()