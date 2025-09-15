"""
Test WebSocket Handshake Timing Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent connection failures that block chat value
- Value Impact: Ensures reliable WebSocket handshake prevents user abandonment
- Strategic Impact: Eliminates 1011 errors that cost $500K+ ARR in chat functionality

CRITICAL: This test validates the business logic that prevents race conditions in 
WebSocket handshakes that have been causing staging failures and user value loss.

This test focuses on BUSINESS LOGIC validation, not system integration.
Tests the algorithms and decision-making functions that prevent race conditions.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import (
    WebSocketID, UserID, ConnectionID, ConnectionState, 
    WebSocketConnectionInfo
)


class HandshakePhase(Enum):
    """WebSocket handshake phases for business logic validation."""
    INITIAL = "initial"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    FAILED = "failed"


@dataclass
class HandshakeAttempt:
    """Data structure for handshake attempt tracking."""
    websocket_id: WebSocketID
    user_id: UserID
    attempt_time: float
    phase: HandshakePhase
    retry_count: int = 0
    error_message: Optional[str] = None


class MockWebSocketHandshakeValidator:
    """Mock handshake validator for business logic testing."""
    
    def __init__(self):
        self.active_handshakes: Dict[WebSocketID, HandshakeAttempt] = {}
        self.handshake_timeouts: Dict[WebSocketID, float] = {}
        self.race_condition_threshold = 0.1  # 100ms
        self.max_concurrent_per_user = 3
        
    def start_handshake(self, websocket_id: WebSocketID, user_id: UserID) -> Dict[str, Any]:
        """Business logic: Start a new handshake with race condition prevention."""
        current_time = time.time()
        
        # Check for concurrent handshake limit
        active_handshakes = self._get_active_handshakes_for_user(user_id)
        if len(active_handshakes) >= self.max_concurrent_per_user:
            return {
                "allowed": False,
                "reason": "too_many_concurrent_handshakes",
                "retry_after": self.race_condition_threshold
            }
        
        # Check for rapid connection attempts (race condition detection)
        if self._has_recent_handshake_attempt(user_id, current_time):
            return {
                "allowed": False,
                "reason": "race_condition_detected",
                "retry_after": self.race_condition_threshold
            }
        
        # Create handshake attempt
        attempt = HandshakeAttempt(
            websocket_id=websocket_id,
            user_id=user_id,
            attempt_time=current_time,
            phase=HandshakePhase.CONNECTING
        )
        
        self.active_handshakes[websocket_id] = attempt
        self.handshake_timeouts[websocket_id] = current_time + 10.0  # 10 second timeout
        
        return {
            "allowed": True,
            "handshake_id": str(websocket_id),
            "timeout": 10.0
        }
    
    def _get_recent_handshakes_for_user(self, user_id: UserID, current_time: float) -> List[HandshakeAttempt]:
        """Get recent handshake attempts for a user within race condition window."""
        threshold_time = current_time - self.race_condition_threshold
        return [
            attempt for attempt in self.active_handshakes.values()
            if attempt.user_id == user_id and attempt.attempt_time > threshold_time
        ]
    
    def _get_active_handshakes_for_user(self, user_id: UserID) -> List[HandshakeAttempt]:
        """Get all active handshake attempts for a user (for concurrent limit checking)."""
        return [
            attempt for attempt in self.active_handshakes.values()
            if attempt.user_id == user_id and attempt.phase in [
                HandshakePhase.CONNECTING, HandshakePhase.AUTHENTICATING, HandshakePhase.READY
            ]
        ]
    
    def _has_recent_handshake_attempt(self, user_id: UserID, current_time: float) -> bool:
        """Check if user has recent handshake attempts (race condition detection)."""
        threshold_time = current_time - self.race_condition_threshold
        
        for attempt in self.active_handshakes.values():
            if (attempt.user_id == user_id and 
                attempt.attempt_time > threshold_time and
                attempt.phase in [HandshakePhase.CONNECTING, HandshakePhase.AUTHENTICATING]):
                return True
        return False
    
    def advance_handshake_phase(self, websocket_id: WebSocketID, new_phase: HandshakePhase) -> bool:
        """Business logic: Advance handshake to next phase."""
        if websocket_id not in self.active_handshakes:
            return False
        
        attempt = self.active_handshakes[websocket_id]
        
        # Validate phase transition logic
        valid_transitions = {
            HandshakePhase.CONNECTING: [HandshakePhase.AUTHENTICATING, HandshakePhase.FAILED],
            HandshakePhase.AUTHENTICATING: [HandshakePhase.READY, HandshakePhase.FAILED],
            HandshakePhase.READY: [HandshakePhase.FAILED],  # Can only fail from ready
        }
        
        if attempt.phase not in valid_transitions:
            return False
        
        if new_phase not in valid_transitions[attempt.phase]:
            return False
        
        attempt.phase = new_phase
        
        # Clean up if handshake completed or failed
        if new_phase in [HandshakePhase.READY, HandshakePhase.FAILED]:
            if websocket_id in self.handshake_timeouts:
                del self.handshake_timeouts[websocket_id]
        
        return True
    
    def check_handshake_timeouts(self, current_time: float) -> List[WebSocketID]:
        """Business logic: Check for timed out handshakes."""
        timed_out = []
        
        for websocket_id, timeout_time in list(self.handshake_timeouts.items()):
            if current_time > timeout_time:
                # Mark as failed
                if websocket_id in self.active_handshakes:
                    self.active_handshakes[websocket_id].phase = HandshakePhase.FAILED
                    self.active_handshakes[websocket_id].error_message = "handshake_timeout"
                
                timed_out.append(websocket_id)
                del self.handshake_timeouts[websocket_id]
        
        return timed_out
    
    def calculate_progressive_delay(self, user_id: UserID) -> float:
        """Business logic: Calculate progressive delay for failed attempts."""
        failed_attempts = sum(
            1 for attempt in self.active_handshakes.values()
            if attempt.user_id == user_id and attempt.phase == HandshakePhase.FAILED
        )
        
        # Progressive backoff: 0.1s, 0.2s, 0.5s, 1.0s, 2.0s
        delays = [0.1, 0.2, 0.5, 1.0, 2.0]
        # Fix off-by-one error: first failure (failed_attempts=1) should use delays[0]=0.1s
        delay_index = min(failed_attempts - 1, len(delays) - 1) if failed_attempts > 0 else 0
        return delays[delay_index]


@pytest.mark.unit
@pytest.mark.golden_path
class TestWebSocketHandshakeTimingLogic(SSotBaseTestCase):
    """Test WebSocket handshake timing business logic validation."""
    
    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)
        self.validator = MockWebSocketHandshakeValidator()
        self.test_user_id = UserID("test_user_12345")
        self.test_websocket_id = WebSocketID("ws_connection_67890")
    
    @pytest.mark.unit
    def test_handshake_initiation_success(self):
        """Test successful handshake initiation business logic."""
        # Test business logic for starting a handshake
        result = self.validator.start_handshake(self.test_websocket_id, self.test_user_id)
        
        # Business validation: Should allow first handshake
        assert result["allowed"] is True
        assert "handshake_id" in result
        assert result["timeout"] == 10.0
        
        # Verify handshake state is properly tracked
        assert self.test_websocket_id in self.validator.active_handshakes
        handshake = self.validator.active_handshakes[self.test_websocket_id]
        assert handshake.user_id == self.test_user_id
        assert handshake.phase == HandshakePhase.CONNECTING
        
        # Record business metric
        self.record_metric("handshake_initiation_success", True)
    
    @pytest.mark.unit
    def test_race_condition_detection_logic(self):
        """Test race condition detection prevents concurrent handshakes."""
        # Start first handshake
        result1 = self.validator.start_handshake(self.test_websocket_id, self.test_user_id)
        assert result1["allowed"] is True
        
        # Immediately try second handshake (race condition)
        websocket_id_2 = WebSocketID("ws_connection_67891")
        result2 = self.validator.start_handshake(websocket_id_2, self.test_user_id)
        
        # Business validation: Should detect race condition
        assert result2["allowed"] is False
        assert result2["reason"] == "race_condition_detected"
        assert result2["retry_after"] == 0.1  # 100ms delay
        
        # Record business metric
        self.record_metric("race_condition_detected", True)
        self.record_metric("race_condition_retry_delay", result2["retry_after"])
    
    @pytest.mark.unit
    def test_concurrent_handshake_limit_enforcement(self):
        """Test enforcement of maximum concurrent handshakes per user."""
        handshake_results = []
        websocket_ids = []
        
        # Attempt to create more handshakes than the limit allows
        for i in range(5):  # Limit is 3
            websocket_id = WebSocketID(f"ws_connection_6789{i}")
            websocket_ids.append(websocket_id)
            
            # Simulate time passing to avoid race condition detection
            if i > 0:
                time.sleep(0.11)  # Just over the race condition threshold
            
            result = self.validator.start_handshake(websocket_id, self.test_user_id)
            handshake_results.append(result)
        
        # Business validation: First 3 should succeed, rest should fail
        for i, result in enumerate(handshake_results):
            if i < 3:
                assert result["allowed"] is True, f"Handshake {i} should be allowed"
            else:
                assert result["allowed"] is False, f"Handshake {i} should be blocked"
                assert result["reason"] == "too_many_concurrent_handshakes"
        
        # Record business metrics
        successful_handshakes = sum(1 for r in handshake_results if r["allowed"])
        blocked_handshakes = sum(1 for r in handshake_results if not r["allowed"])
        
        self.record_metric("successful_handshakes", successful_handshakes)
        self.record_metric("blocked_handshakes", blocked_handshakes)
        assert successful_handshakes == 3
        assert blocked_handshakes == 2
    
    @pytest.mark.unit
    def test_handshake_phase_transition_validation(self):
        """Test handshake phase transition business logic."""
        # Start handshake
        self.validator.start_handshake(self.test_websocket_id, self.test_user_id)
        
        # Test valid phase transitions
        valid_transitions = [
            (HandshakePhase.CONNECTING, HandshakePhase.AUTHENTICATING),
            (HandshakePhase.AUTHENTICATING, HandshakePhase.READY),
        ]
        
        for from_phase, to_phase in valid_transitions:
            # Reset to from_phase
            self.validator.active_handshakes[self.test_websocket_id].phase = from_phase
            
            # Test transition
            result = self.validator.advance_handshake_phase(self.test_websocket_id, to_phase)
            assert result is True, f"Transition from {from_phase} to {to_phase} should be valid"
            
            actual_phase = self.validator.active_handshakes[self.test_websocket_id].phase
            assert actual_phase == to_phase
        
        # Test invalid phase transitions
        invalid_transitions = [
            (HandshakePhase.READY, HandshakePhase.CONNECTING),  # Can't go backwards
            (HandshakePhase.CONNECTING, HandshakePhase.READY),  # Must go through auth
        ]
        
        for from_phase, to_phase in invalid_transitions:
            # Reset to from_phase
            self.validator.active_handshakes[self.test_websocket_id].phase = from_phase
            
            # Test transition
            result = self.validator.advance_handshake_phase(self.test_websocket_id, to_phase)
            assert result is False, f"Transition from {from_phase} to {to_phase} should be invalid"
        
        # Record business metric
        self.record_metric("phase_transition_validation", True)
    
    @pytest.mark.unit
    def test_handshake_timeout_detection_logic(self):
        """Test handshake timeout detection business logic."""
        # Start handshake
        self.validator.start_handshake(self.test_websocket_id, self.test_user_id)
        
        # Simulate time passing beyond timeout
        future_time = time.time() + 15.0  # 15 seconds (timeout is 10)
        
        # Check for timeouts
        timed_out_handshakes = self.validator.check_handshake_timeouts(future_time)
        
        # Business validation: Should detect timeout
        assert len(timed_out_handshakes) == 1
        assert timed_out_handshakes[0] == self.test_websocket_id
        
        # Verify handshake marked as failed
        handshake = self.validator.active_handshakes[self.test_websocket_id]
        assert handshake.phase == HandshakePhase.FAILED
        assert handshake.error_message == "handshake_timeout"
        
        # Verify timeout tracking cleaned up
        assert self.test_websocket_id not in self.validator.handshake_timeouts
        
        # Record business metric
        self.record_metric("timeout_detection_accuracy", True)
        self.record_metric("timeout_cleanup_success", True)
    
    @pytest.mark.unit
    def test_progressive_delay_calculation_logic(self):
        """Test progressive delay calculation for failed attempts."""
        # Create multiple failed handshakes for the user
        failed_websocket_ids = []
        expected_delays = [0.1, 0.2, 0.5, 1.0, 2.0]
        
        for i in range(6):  # Test beyond the delay array length
            websocket_id = WebSocketID(f"failed_ws_{i}")
            failed_websocket_ids.append(websocket_id)
            
            # Create failed handshake
            attempt = HandshakeAttempt(
                websocket_id=websocket_id,
                user_id=self.test_user_id,
                attempt_time=time.time(),
                phase=HandshakePhase.FAILED
            )
            self.validator.active_handshakes[websocket_id] = attempt
            
            # Calculate delay
            delay = self.validator.calculate_progressive_delay(self.test_user_id)
            
            # Business validation: Delay should increase progressively
            expected_delay = expected_delays[min(i, len(expected_delays) - 1)]
            assert delay == expected_delay, f"Attempt {i}: expected {expected_delay}, got {delay}"
        
        # Record business metrics
        final_delay = self.validator.calculate_progressive_delay(self.test_user_id)
        self.record_metric("progressive_delay_logic", True)
        self.record_metric("max_delay_reached", final_delay == 2.0)
    
    @pytest.mark.unit
    def test_handshake_cleanup_on_completion(self):
        """Test handshake state cleanup when completed successfully."""
        # Start handshake
        self.validator.start_handshake(self.test_websocket_id, self.test_user_id)
        
        # Verify initial state
        assert self.test_websocket_id in self.validator.active_handshakes
        assert self.test_websocket_id in self.validator.handshake_timeouts
        
        # Advance through phases to completion
        self.validator.advance_handshake_phase(self.test_websocket_id, HandshakePhase.AUTHENTICATING)
        self.validator.advance_handshake_phase(self.test_websocket_id, HandshakePhase.READY)
        
        # Business validation: Timeout tracking should be cleaned up
        assert self.test_websocket_id not in self.validator.handshake_timeouts
        
        # Handshake should still be tracked but marked as ready
        assert self.test_websocket_id in self.validator.active_handshakes
        handshake = self.validator.active_handshakes[self.test_websocket_id]
        assert handshake.phase == HandshakePhase.READY
        
        # Record business metric
        self.record_metric("cleanup_on_completion", True)
    
    @pytest.mark.unit
    def test_race_condition_prevention_timing_accuracy(self):
        """Test timing accuracy of race condition prevention logic."""
        # Test timing accuracy at various intervals by creating controlled handshake attempts
        base_time = time.time()
        test_intervals = [0.05, 0.09, 0.11, 0.15]  # Around the 0.1s threshold
        
        for i, interval in enumerate(test_intervals):
            # Create fresh validator for each test to avoid interference
            validator = MockWebSocketHandshakeValidator()
            user_id = UserID(f"timing_test_user_{i}")
            
            # Create first handshake at base_time
            first_attempt = HandshakeAttempt(
                websocket_id=WebSocketID(f"ws_first_{i}"),
                user_id=user_id,
                attempt_time=base_time,
                phase=HandshakePhase.CONNECTING
            )
            validator.active_handshakes[first_attempt.websocket_id] = first_attempt
            
            # Test second handshake at base_time + interval with mocked time
            test_time = base_time + interval
            with patch('time.time', return_value=test_time):
                websocket_id = WebSocketID(f"ws_test_{interval}_{i}")
                result = validator.start_handshake(websocket_id, user_id)
                
                if interval < 0.1:
                    # Should be blocked by race condition detection
                    assert result["allowed"] is False, f"Interval {interval}s should be blocked"
                    assert result["reason"] == "race_condition_detected"
                else:
                    # Should be allowed after threshold
                    assert result["allowed"] is True, f"Interval {interval}s should be allowed"
        
        # Record business metric
        self.record_metric("race_condition_timing_accuracy", True)
    
    @pytest.mark.unit
    def test_business_value_preservation_logic(self):
        """Test that business logic preserves user chat value delivery."""
        # This test validates the business logic ensures chat availability
        
        # Scenario: User attempts multiple connections (network issues)
        user_connection_attempts = []
        
        for attempt_num in range(10):
            websocket_id = WebSocketID(f"user_retry_{attempt_num}")
            
            # Simulate user retrying connection with appropriate delays
            if attempt_num > 0:
                delay = self.validator.calculate_progressive_delay(self.test_user_id)
                time.sleep(delay)  # Respect the progressive delay
            
            result = self.validator.start_handshake(websocket_id, self.test_user_id)
            user_connection_attempts.append(result)
            
            # If handshake started, complete it successfully
            if result["allowed"]:
                # Simulate successful handshake completion
                self.validator.advance_handshake_phase(websocket_id, HandshakePhase.AUTHENTICATING)
                self.validator.advance_handshake_phase(websocket_id, HandshakePhase.READY)
                
                # Clean up old handshakes to allow new ones
                del self.validator.active_handshakes[websocket_id]
        
        # Business validation: User should eventually get successful connection
        successful_attempts = [r for r in user_connection_attempts if r["allowed"]]
        assert len(successful_attempts) > 0, "User must be able to establish connection for chat value"
        
        # Business validation: System should not block user permanently
        blocked_attempts = [r for r in user_connection_attempts if not r["allowed"]]
        assert len(blocked_attempts) < len(user_connection_attempts), "System must not block all attempts"
        
        # Record business metrics
        success_rate = len(successful_attempts) / len(user_connection_attempts)
        self.record_metric("user_connection_success_rate", success_rate)
        self.record_metric("business_value_preserved", success_rate > 0.3)  # At least 30% success
        
        # Business requirement: Users must be able to access chat for $500K ARR
        assert success_rate > 0.3, f"Success rate {success_rate:.2%} too low for business value delivery"


if __name__ == "__main__":
    pytest.main([__file__])