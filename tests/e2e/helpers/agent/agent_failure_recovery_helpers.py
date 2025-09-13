"""Agent Failure Recovery Testing Utilities



This module provides comprehensive agent failure recovery testing infrastructure including:

- Agent failure simulation and error injection

- WebSocket error event validation

- Circuit breaker testing

- Recovery mechanism validation

- Error propagation and communication testing

"""



import asyncio

import json

import time

from datetime import datetime

from enum import Enum

from typing import Any, Dict, List, Optional



from netra_backend.app.logging_config import central_logger

from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS

from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient



logger = central_logger.get_logger(__name__)





class FailureType(Enum):

    """Types of agent failures to simulate"""

    TIMEOUT = "timeout"

    NETWORK_ERROR = "network_error"

    AUTHENTICATION_FAILURE = "auth_failure"

    PROCESSING_ERROR = "processing_error"

    RESOURCE_EXHAUSTION = "resource_exhaustion"

    INVALID_INPUT = "invalid_input"





class RecoveryAction(Enum):

    """Types of recovery actions"""

    RETRY = "retry"

    FALLBACK = "fallback"

    CIRCUIT_BREAKER = "circuit_breaker"

    GRACEFUL_DEGRADATION = "graceful_degradation"

    USER_NOTIFICATION = "user_notification"





class MockCircuitBreakerConfig:

    """Mock circuit breaker config for testing."""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 30):

        self.name = name

        self.failure_threshold = failure_threshold

        self.recovery_timeout = recovery_timeout





class MockWebSocketErrorInfo:

    """Mock WebSocket error info for testing."""

    def __init__(self, user_id: str = None, error_type: str = None, message: str = None, 

                 severity: str = "MEDIUM", context: Dict[str, Any] = None, recoverable: bool = True, **kwargs):

        self.user_id = user_id

        self.error_type = error_type

        self.message = message

        self.severity = severity

        self.context = context or {}

        self.recoverable = recoverable





class AgentFailureSimulator:

    """Simulates various agent failure scenarios for testing recovery mechanisms."""

    

    def __init__(self):

        self.active_failures: Dict[str, Dict[str, Any]] = {}

        self.failure_history: List[Dict[str, Any]] = []

        self.recovery_attempts: List[Dict[str, Any]] = []

    

    async def simulate_agent_timeout(self, agent_id: str, timeout_duration: float = 30.0) -> Dict[str, Any]:

        """Simulate agent timeout failure."""

        failure_id = f"timeout_{agent_id}_{int(time.time())}"

        

        failure_data = {

            "failure_id": failure_id,

            "agent_id": agent_id,

            "failure_type": FailureType.TIMEOUT.value,

            "timeout_duration": timeout_duration,

            "triggered_at": time.time(),

            "status": "active"

        }

        

        self.active_failures[failure_id] = failure_data

        self.failure_history.append(failure_data.copy())

        

        logger.info(f"Simulated timeout failure for agent {agent_id}")

        return failure_data

    

    async def simulate_network_error(self, agent_id: str, error_code: str = "CONNECTION_LOST") -> Dict[str, Any]:

        """Simulate network connectivity error."""

        failure_id = f"network_{agent_id}_{int(time.time())}"

        

        failure_data = {

            "failure_id": failure_id,

            "agent_id": agent_id,

            "failure_type": FailureType.NETWORK_ERROR.value,

            "error_code": error_code,

            "triggered_at": time.time(),

            "status": "active"

        }

        

        self.active_failures[failure_id] = failure_data

        self.failure_history.append(failure_data.copy())

        

        logger.info(f"Simulated network error for agent {agent_id}: {error_code}")

        return failure_data

    

    async def simulate_processing_error(self, agent_id: str, error_message: str = "Processing failed") -> Dict[str, Any]:

        """Simulate agent processing error."""

        failure_id = f"processing_{agent_id}_{int(time.time())}"

        

        failure_data = {

            "failure_id": failure_id,

            "agent_id": agent_id,

            "failure_type": FailureType.PROCESSING_ERROR.value,

            "error_message": error_message,

            "triggered_at": time.time(),

            "status": "active"

        }

        

        self.active_failures[failure_id] = failure_data

        self.failure_history.append(failure_data.copy())

        

        logger.info(f"Simulated processing error for agent {agent_id}: {error_message}")

        return failure_data

    

    def get_failure_statistics(self) -> Dict[str, Any]:

        """Get comprehensive failure statistics."""

        active_count = len(self.active_failures)

        total_count = len(self.failure_history)

        recovery_count = len(self.recovery_attempts)

        

        failure_types = {}

        for failure in self.failure_history:

            failure_type = failure.get("failure_type")

            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1

        

        return {

            "active_failures": active_count,

            "total_failures": total_count,

            "recovery_attempts": recovery_count,

            "failure_types": failure_types,

            "success_rate": recovery_count / max(total_count, 1)

        }

    

    async def trigger_recovery(self, failure_id: str, recovery_action: RecoveryAction) -> Dict[str, Any]:

        """Trigger recovery action for a specific failure."""

        if failure_id not in self.active_failures:

            return {"success": False, "error": "Failure not found"}

        

        failure_data = self.active_failures[failure_id]

        

        recovery_data = {

            "recovery_id": f"recovery_{failure_id}_{int(time.time())}",

            "failure_id": failure_id,

            "recovery_action": recovery_action.value,

            "triggered_at": time.time(),

            "success": True

        }

        

        self.recovery_attempts.append(recovery_data)

        

        # Mark failure as resolved

        failure_data["status"] = "recovered"

        failure_data["recovered_at"] = time.time()

        

        # Remove from active failures

        if failure_id in self.active_failures:

            del self.active_failures[failure_id]

        

        logger.info(f"Triggered recovery for failure {failure_id} using {recovery_action.value}")

        return recovery_data





class WebSocketErrorEventValidator:

    """Validates WebSocket error events and recovery communications."""

    

    def __init__(self):

        self.captured_events: List[Dict[str, Any]] = []

        self.validation_errors: List[str] = []

    

    def capture_error_event(self, event_data: Dict[str, Any]) -> None:

        """Capture WebSocket error event for validation."""

        event_data["captured_at"] = time.time()

        self.captured_events.append(event_data)

        logger.debug(f"Captured error event: {event_data.get('type', 'unknown')}")

    

    def validate_error_event_structure(self, event: Dict[str, Any]) -> bool:

        """Validate error event has required structure."""

        required_fields = {"type", "payload", "timestamp"}

        

        missing_fields = required_fields - set(event.keys())

        if missing_fields:

            self.validation_errors.append(f"Error event missing fields: {missing_fields}")

            return False

        

        # Validate payload structure

        payload = event.get("payload", {})

        required_payload_fields = {"error_type", "message", "severity"}

        

        missing_payload_fields = required_payload_fields - set(payload.keys())

        if missing_payload_fields:

            self.validation_errors.append(f"Error payload missing fields: {missing_payload_fields}")

            return False

        

        return True

    

    def validate_recovery_communication(self, events: List[Dict[str, Any]]) -> bool:

        """Validate recovery is properly communicated via WebSocket."""

        error_events = [e for e in events if e.get("type", "").endswith("_error")]

        recovery_events = [e for e in events if e.get("type", "").endswith("_recovery")]

        

        if not error_events:

            self.validation_errors.append("No error events found")

            return False

        

        # For each error, there should be a corresponding recovery communication

        for error_event in error_events:

            error_id = error_event.get("payload", {}).get("error_id")

            if error_id:

                # Look for recovery event with same error_id

                recovery_found = any(

                    recovery.get("payload", {}).get("error_id") == error_id

                    for recovery in recovery_events

                )

                

                if not recovery_found:

                    self.validation_errors.append(f"No recovery communication for error {error_id}")

                    return False

        

        return True

    

    def get_validation_errors(self) -> List[str]:

        """Get all validation errors."""

        return self.validation_errors.copy()

    

    def clear_errors(self) -> None:

        """Clear validation errors."""

        self.validation_errors.clear()





class CircuitBreakerTester:

    """Tests circuit breaker functionality during agent failures."""

    

    def __init__(self):

        self.circuit_states: Dict[str, str] = {}  # CLOSED, OPEN, HALF_OPEN

        self.failure_counts: Dict[str, int] = {}

        self.state_changes: List[Dict[str, Any]] = []

    

    def initialize_circuit(self, circuit_name: str, threshold: int = 5) -> None:

        """Initialize circuit breaker for testing."""

        self.circuit_states[circuit_name] = "CLOSED"

        self.failure_counts[circuit_name] = 0

        

        logger.info(f"Initialized circuit breaker: {circuit_name} (threshold: {threshold})")

    

    async def trigger_failure(self, circuit_name: str) -> Dict[str, Any]:

        """Trigger failure and update circuit breaker state."""

        if circuit_name not in self.circuit_states:

            self.initialize_circuit(circuit_name)

        

        self.failure_counts[circuit_name] += 1

        current_count = self.failure_counts[circuit_name]

        

        # Check if circuit should open (threshold: 5 failures)

        if current_count >= 5 and self.circuit_states[circuit_name] == "CLOSED":

            self.circuit_states[circuit_name] = "OPEN"

            self.state_changes.append({

                "circuit": circuit_name,

                "previous_state": "CLOSED",

                "new_state": "OPEN",

                "failure_count": current_count,

                "timestamp": time.time()

            })

            

            logger.warning(f"Circuit breaker {circuit_name} OPENED after {current_count} failures")

        

        return {

            "circuit": circuit_name,

            "state": self.circuit_states[circuit_name],

            "failure_count": current_count,

            "triggered_at": time.time()

        }

    

    async def attempt_recovery(self, circuit_name: str) -> Dict[str, Any]:

        """Attempt recovery and transition to half-open state."""

        if circuit_name not in self.circuit_states:

            return {"success": False, "error": "Circuit not found"}

        

        if self.circuit_states[circuit_name] == "OPEN":

            self.circuit_states[circuit_name] = "HALF_OPEN"

            self.state_changes.append({

                "circuit": circuit_name,

                "previous_state": "OPEN",

                "new_state": "HALF_OPEN",

                "timestamp": time.time()

            })

            

            logger.info(f"Circuit breaker {circuit_name} transitioned to HALF_OPEN")

        

        return {

            "circuit": circuit_name,

            "state": self.circuit_states[circuit_name],

            "recovery_attempted": True,

            "timestamp": time.time()

        }

    

    def validate_circuit_behavior(self, circuit_name: str, expected_behavior: Dict[str, Any]) -> bool:

        """Validate circuit breaker behaves as expected."""

        if circuit_name not in self.circuit_states:

            return False

        

        current_state = self.circuit_states[circuit_name]

        expected_state = expected_behavior.get("expected_state")

        

        if expected_state and current_state != expected_state:

            return False

        

        current_failures = self.failure_counts.get(circuit_name, 0)

        expected_failures = expected_behavior.get("expected_failure_count")

        

        if expected_failures is not None and current_failures != expected_failures:

            return False

        

        return True

    

    def get_circuit_statistics(self) -> Dict[str, Any]:

        """Get comprehensive circuit breaker statistics."""

        return {

            "circuits": dict(self.circuit_states),

            "failure_counts": dict(self.failure_counts),

            "state_changes": len(self.state_changes),

            "active_circuits": len(self.circuit_states)

        }





def create_error_test_scenarios() -> List[Dict[str, Any]]:

    """Create various error scenarios for testing."""

    scenarios = [

        {

            "name": "Agent Timeout",

            "failure_type": FailureType.TIMEOUT,

            "expected_recovery": RecoveryAction.RETRY,

            "severity": "HIGH"

        },

        {

            "name": "Network Connectivity Lost",

            "failure_type": FailureType.NETWORK_ERROR,

            "expected_recovery": RecoveryAction.RETRY,

            "severity": "HIGH"

        },

        {

            "name": "Processing Error",

            "failure_type": FailureType.PROCESSING_ERROR,

            "expected_recovery": RecoveryAction.FALLBACK,

            "severity": "MEDIUM"

        },

        {

            "name": "Authentication Failure",

            "failure_type": FailureType.AUTHENTICATION_FAILURE,

            "expected_recovery": RecoveryAction.USER_NOTIFICATION,

            "severity": "HIGH"

        },

        {

            "name": "Resource Exhaustion",

            "failure_type": FailureType.RESOURCE_EXHAUSTION,

            "expected_recovery": RecoveryAction.CIRCUIT_BREAKER,

            "severity": "CRITICAL"

        }

    ]

    

    return scenarios





async def validate_recovery_timing(recovery_start: float, recovery_end: float, 

                                 expected_max_duration: float = 30.0) -> bool:

    """Validate recovery completed within expected timeframe."""

    actual_duration = recovery_end - recovery_start

    return actual_duration <= expected_max_duration





def create_mock_websocket_error(error_type: str, message: str, severity: str = "MEDIUM") -> MockWebSocketErrorInfo:

    """Create mock WebSocket error for testing."""

    return MockWebSocketErrorInfo(

        error_type=error_type,

        message=message,

        severity=severity,

        recoverable=True

    )

