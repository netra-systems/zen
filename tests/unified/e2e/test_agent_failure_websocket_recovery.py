"""Agent Failure Recovery via WebSocket Test - P1 HIGH Priority Integration Test

Comprehensive test suite for validating agent failure recovery mechanisms through 
WebSocket communication. Tests error event propagation, graceful degradation,
circuit breaker activation, and system recovery patterns.

Business Value Justification (BVJ):
1. Segment: All paid tiers ($80K+ MRR protection)
2. Business Goal: Ensure system resilience during agent failures
3. Value Impact: Prevents complete service outages, maintains partial functionality
4. Revenue Impact: Protects against customer churn from system failures

Architecture: P1 High Priority test for production resilience
- Tests real failure scenarios with proper error handling
- Ensures no silent failures - all errors communicated via WebSocket
- Validates recovery mechanisms work correctly
- Must run deterministically in < 30 seconds
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from ..config import TEST_USERS, TEST_ENDPOINTS, UnifiedTestConfig
from .websocket_resilience_core import WebSocketResilienceTestCore
from ..real_websocket_client import RealWebSocketClient
from .agent_conversation_helpers import AgentConversationTestCore

# Mock classes to avoid importing full app configuration
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
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockAgentError:
    """Mock agent error for testing."""
    def __init__(self, agent_name: str, error_type: str, error_message: str, 
                 timestamp: datetime = None, is_recoverable: bool = True):
        self.agent_name = agent_name
        self.error_type = error_type
        self.error_message = error_message
        self.timestamp = timestamp or datetime.utcnow()
        self.is_recoverable = is_recoverable


class AgentFailureSimulator:
    """Simulates various agent failure scenarios for testing."""
    
    def __init__(self):
        self.failure_scenarios = {
            "llm_timeout": {
                "error_type": "timeout",
                "error_message": "LLM API request timed out",
                "recovery_time": 5.0,
                "is_recoverable": True
            },
            "rate_limit": {
                "error_type": "rate_limit",
                "error_message": "API rate limit exceeded",
                "recovery_time": 30.0,
                "is_recoverable": True
            },
            "memory_exhaustion": {
                "error_type": "resource_limit",
                "error_message": "Memory limit exceeded",
                "recovery_time": 0.0,
                "is_recoverable": False
            },
            "network_failure": {
                "error_type": "network_error",
                "error_message": "Network connection failed",
                "recovery_time": 10.0,
                "is_recoverable": True
            },
            "invalid_response": {
                "error_type": "validation_error",
                "error_message": "Invalid LLM response format",
                "recovery_time": 2.0,
                "is_recoverable": True
            }
        }
    
    def create_agent_error(self, failure_type: str, agent_name: str = "test_agent") -> MockAgentError:
        """Create AgentError for failure type."""
        scenario = self.failure_scenarios.get(failure_type, self.failure_scenarios["llm_timeout"])
        return MockAgentError(
            agent_name=agent_name,
            error_type=scenario["error_type"],
            error_message=scenario["error_message"],
            timestamp=datetime.utcnow(),
            is_recoverable=scenario["is_recoverable"]
        )
    
    def create_websocket_error(self, failure_type: str, user_id: str = "test_user") -> MockWebSocketErrorInfo:
        """Create WebSocketErrorInfo for failure type."""
        scenario = self.failure_scenarios.get(failure_type, self.failure_scenarios["llm_timeout"])
        severity = "HIGH" if not scenario["is_recoverable"] else "MEDIUM"
        return MockWebSocketErrorInfo(
            user_id=user_id,
            error_type=scenario["error_type"],
            message=scenario["error_message"],
            severity=severity,
            context={"failure_scenario": failure_type},
            recoverable=scenario["is_recoverable"]
        )


class WebSocketEventValidator:
    """Validates WebSocket events during agent failure recovery."""
    
    def __init__(self):
        self.received_events: List[Dict[str, Any]] = []
        self.expected_event_types = [
            "agent_error",
            "agent_fallback_activated", 
            "circuit_breaker_triggered",
            "partial_result_preserved",
            "recovery_attempt",
            "graceful_degradation"
        ]
    
    async def collect_events(self, client: RealWebSocketClient, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Collect WebSocket events during timeout period."""
        start_time = time.time()
        events = []
        
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(client.receive(), timeout=1.0)
                if message:
                    event = json.loads(message) if isinstance(message, str) else message
                    events.append(event)
                    self.received_events.append(event)
            except asyncio.TimeoutError:
                break
            except Exception:
                break
        
        return events
    
    def validate_error_event(self, event: Dict[str, Any], expected_error_type: str) -> Dict[str, bool]:
        """Validate agent error event structure and content."""
        return {
            "has_correct_type": event.get("type") == "agent_error",
            "has_error_type": event.get("error_type") == expected_error_type,
            "has_actionable_info": "message" in event and "agent_name" in event,
            "has_recovery_info": "is_recoverable" in event,
            "has_timestamp": "timestamp" in event
        }
    
    def validate_circuit_breaker_event(self, event: Dict[str, Any]) -> Dict[str, bool]:
        """Validate circuit breaker activation event."""
        return {
            "has_correct_type": event.get("type") == "circuit_breaker_triggered",
            "has_agent_name": "agent_name" in event,
            "has_failure_threshold": "failure_threshold_reached" in event,
            "has_cooldown_period": "cooldown_period" in event,
            "has_fallback_status": "fallback_active" in event
        }
    
    def validate_partial_result_event(self, event: Dict[str, Any]) -> Dict[str, bool]:
        """Validate partial result preservation event."""
        return {
            "has_correct_type": event.get("type") == "partial_result_preserved", 
            "has_preserved_data": "preserved_data" in event,
            "has_lost_data_info": "lost_data" in event,
            "has_confidence_info": "confidence_reduced" in event
        }


class TestAgentFailureWebSocketRecovery:
    """Main test class for agent failure recovery via WebSocket."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return UnifiedTestConfig()
    
    @pytest.fixture 
    def websocket_core(self):
        """WebSocket test core."""
        return WebSocketResilienceTestCore()
    
    @pytest.fixture
    def conversation_core(self):
        """Agent conversation test core."""
        return AgentConversationTestCore()
    
    @pytest.fixture
    def failure_simulator(self):
        """Agent failure simulator."""
        return AgentFailureSimulator()
    
    @pytest.fixture
    def event_validator(self):
        """WebSocket event validator."""
        return WebSocketEventValidator()
    
    @pytest.mark.asyncio
    async def test_llm_timeout_error_propagation(self, websocket_core, failure_simulator, event_validator):
        """Test LLM timeout error propagation through WebSocket."""
        # Setup authenticated WebSocket connection
        test_user = TEST_USERS["free"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate LLM timeout failure
        error = failure_simulator.create_websocket_error("llm_timeout", test_user.id)
        
        # Simulate sending agent request that will timeout
        agent_request = {
            "type": "agent_request",
            "message": "Analyze my data patterns",
            "user_id": test_user.id,
            "simulate_timeout": True  # Flag for test simulation
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect WebSocket events
        events = await event_validator.collect_events(client, timeout=8.0)
        
        # Validate timeout error event was sent
        error_events = [e for e in events if e.get("type") == "agent_error"]
        assert len(error_events) > 0, "No agent error events received"
        
        error_event = error_events[0]
        validation = event_validator.validate_error_event(error_event, "timeout")
        
        assert validation["has_correct_type"], "Error event missing correct type"
        assert validation["has_error_type"], "Error event missing timeout error type"
        assert validation["has_actionable_info"], "Error event missing actionable information"
        assert validation["has_recovery_info"], "Error event missing recovery information"
        
        # Verify timeout is marked as recoverable
        assert error_event.get("is_recoverable") is True, "Timeout should be marked as recoverable"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation_notification(self, websocket_core, failure_simulator, event_validator):
        """Test circuit breaker activation triggers WebSocket notification."""
        test_user = TEST_USERS["early"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate repeated failures to trigger circuit breaker
        for i in range(6):  # Exceed default failure threshold of 5
            agent_request = {
                "type": "agent_request",
                "message": f"Test request {i}",
                "user_id": test_user.id,
                "simulate_failure": "rate_limit"
            }
            await client.send(json.dumps(agent_request))
            await asyncio.sleep(0.5)  # Small delay between requests
        
        # Collect events 
        events = await event_validator.collect_events(client, timeout=10.0)
        
        # Validate circuit breaker event
        cb_events = [e for e in events if e.get("type") == "circuit_breaker_triggered"]
        assert len(cb_events) > 0, "No circuit breaker events received"
        
        cb_event = cb_events[0]
        validation = event_validator.validate_circuit_breaker_event(cb_event)
        
        assert validation["has_correct_type"], "Circuit breaker event missing correct type"
        assert validation["has_agent_name"], "Circuit breaker event missing agent name"
        assert validation["has_failure_threshold"], "Circuit breaker event missing failure threshold info"
        assert validation["has_cooldown_period"], "Circuit breaker event missing cooldown period"
        assert validation["has_fallback_status"], "Circuit breaker event missing fallback status"
        
        # Verify fallback is activated
        assert cb_event.get("fallback_active") is True, "Fallback should be activated when circuit breaker triggers"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_partial_result_preservation(self, websocket_core, failure_simulator, event_validator):
        """Test partial results are preserved and communicated before failure."""
        test_user = TEST_USERS["enterprise"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Send agent request that will partially complete then fail
        agent_request = {
            "type": "agent_request",
            "message": "Comprehensive analysis with multiple steps",
            "user_id": test_user.id,
            "simulate_partial_failure": True,
            "partial_results": {
                "step1": "Data ingestion completed",
                "step2": "Initial analysis completed", 
                "step3_failed": "Memory exhaustion during processing"
            }
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=12.0)
        
        # Validate partial result preservation event
        partial_events = [e for e in events if e.get("type") == "partial_result_preserved"]
        assert len(partial_events) > 0, "No partial result preservation events received"
        
        partial_event = partial_events[0]
        validation = event_validator.validate_partial_result_event(partial_event)
        
        assert validation["has_correct_type"], "Partial result event missing correct type"
        assert validation["has_preserved_data"], "Partial result event missing preserved data"
        assert validation["has_lost_data_info"], "Partial result event missing lost data info"
        assert validation["has_confidence_info"], "Partial result event missing confidence info"
        
        # Verify preserved data contains completed steps
        preserved_data = partial_event.get("preserved_data", {})
        assert "step1" in preserved_data, "Step1 results should be preserved"
        assert "step2" in preserved_data, "Step2 results should be preserved"
        
        # Verify confidence is reduced
        assert partial_event.get("confidence_reduced") is True, "Confidence should be reduced for partial results"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_notification(self, websocket_core, failure_simulator, event_validator):
        """Test graceful degradation mode is communicated to frontend."""
        test_user = TEST_USERS["free"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate service degradation scenario
        agent_request = {
            "type": "agent_request", 
            "message": "Advanced analysis request",
            "user_id": test_user.id,
            "simulate_degradation": True
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=8.0)
        
        # Look for graceful degradation event
        degradation_events = [e for e in events if e.get("type") == "graceful_degradation"]
        assert len(degradation_events) > 0, "No graceful degradation events received"
        
        degradation_event = degradation_events[0]
        
        # Validate degradation event content
        assert "available_features" in degradation_event, "Missing available features list"
        assert "disabled_features" in degradation_event, "Missing disabled features list"
        assert "performance_impact" in degradation_event, "Missing performance impact info"
        
        # Verify some features remain available
        available_features = degradation_event.get("available_features", [])
        assert len(available_features) > 0, "No features available during degradation"
        assert "basic_analysis" in available_features, "Basic analysis should remain available"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_recovery_mechanism_communication(self, websocket_core, failure_simulator, event_validator):
        """Test recovery mechanism attempts are communicated."""
        test_user = TEST_USERS["early"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate recoverable failure with retry mechanism
        agent_request = {
            "type": "agent_request",
            "message": "Test recovery mechanism",
            "user_id": test_user.id,
            "simulate_recoverable_failure": True,
            "recovery_strategy": "exponential_backoff"
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=15.0)
        
        # Look for recovery attempt events
        recovery_events = [e for e in events if e.get("type") == "recovery_attempt"]
        assert len(recovery_events) > 0, "No recovery attempt events received"
        
        recovery_event = recovery_events[0]
        
        # Validate recovery event content
        assert "strategy" in recovery_event, "Missing recovery strategy"
        assert "attempt_number" in recovery_event, "Missing attempt number"
        assert "backoff_delay" in recovery_event, "Missing backoff delay info"
        
        # Verify exponential backoff strategy
        assert recovery_event.get("strategy") == "exponential_backoff", "Wrong recovery strategy"
        
        # Look for successful recovery event
        success_events = [e for e in events if e.get("type") == "agent_recovered"]
        if len(success_events) > 0:
            success_event = success_events[0]
            assert "recovery_time" in success_event, "Missing recovery time"
            assert "attempts_made" in success_event, "Missing attempts count"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_notification(self, websocket_core, failure_simulator, event_validator):
        """Test resource cleanup happens after agent failure."""
        test_user = TEST_USERS["enterprise"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate memory exhaustion failure
        agent_request = {
            "type": "agent_request",
            "message": "Memory intensive operation",
            "user_id": test_user.id,
            "simulate_failure": "memory_exhaustion"
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=10.0)
        
        # Look for cleanup notification
        cleanup_events = [e for e in events if e.get("type") == "resource_cleanup"]
        assert len(cleanup_events) > 0, "No resource cleanup events received"
        
        cleanup_event = cleanup_events[0]
        
        # Validate cleanup event content  
        assert "resources_cleaned" in cleanup_event, "Missing resources cleaned list"
        assert "memory_freed" in cleanup_event, "Missing memory freed info"
        assert "cleanup_status" in cleanup_event, "Missing cleanup status"
        
        # Verify cleanup was successful
        assert cleanup_event.get("cleanup_status") == "success", "Cleanup should be successful"
        
        # Verify specific resources were cleaned
        resources_cleaned = cleanup_event.get("resources_cleaned", [])
        assert "agent_memory" in resources_cleaned, "Agent memory should be cleaned"
        assert "temp_files" in resources_cleaned, "Temp files should be cleaned"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_network_failure_during_execution(self, websocket_core, failure_simulator, event_validator):
        """Test network failure during agent execution with partial result saving."""
        test_user = TEST_USERS["free"]  
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate network failure during execution
        agent_request = {
            "type": "agent_request",
            "message": "Long running analysis",
            "user_id": test_user.id,
            "simulate_network_failure_during_execution": True,
            "execution_progress": 0.6  # 60% complete when failure occurs
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=12.0)
        
        # Validate network error event
        network_error_events = [e for e in events if e.get("error_type") == "network_error"]
        assert len(network_error_events) > 0, "No network error events received"
        
        # Validate partial results were saved
        partial_save_events = [e for e in events if e.get("type") == "partial_result_saved"]
        assert len(partial_save_events) > 0, "No partial result save events received"
        
        partial_save_event = partial_save_events[0]
        assert "progress_percentage" in partial_save_event, "Missing progress percentage"
        assert partial_save_event.get("progress_percentage") >= 0.5, "Progress should be at least 50%"
        
        # Verify retry will be attempted
        retry_events = [e for e in events if e.get("type") == "retry_scheduled"]
        assert len(retry_events) > 0, "No retry scheduled events received"
        
        retry_event = retry_events[0]
        assert "retry_delay" in retry_event, "Missing retry delay"
        assert "max_retries" in retry_event, "Missing max retries info"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_error_event_actionable_information(self, websocket_core, failure_simulator, event_validator):
        """Test error events contain actionable information for frontend."""
        test_user = TEST_USERS["early"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Test different error types for actionable information
        error_types = ["llm_timeout", "rate_limit", "invalid_response"]
        
        for error_type in error_types:
            agent_request = {
                "type": "agent_request",
                "message": f"Test {error_type} error",
                "user_id": test_user.id,
                "simulate_failure": error_type
            }
            
            await client.send(json.dumps(agent_request))
            await asyncio.sleep(2.0)  # Wait for error event
        
        # Collect all events
        events = await event_validator.collect_events(client, timeout=10.0)
        
        # Validate each error type has actionable information
        for error_type in error_types:
            error_events = [e for e in events if e.get("error_type") == error_type]
            assert len(error_events) > 0, f"No events for {error_type}"
            
            error_event = error_events[0]
            
            # Check actionable information
            assert "user_message" in error_event, f"Missing user message for {error_type}"
            assert "suggested_action" in error_event, f"Missing suggested action for {error_type}"
            assert "retry_possible" in error_event, f"Missing retry info for {error_type}"
            assert "estimated_recovery_time" in error_event, f"Missing recovery time for {error_type}"
            
            # Verify user message is helpful
            user_message = error_event.get("user_message", "")
            assert len(user_message) > 10, f"User message too short for {error_type}"
            assert error_type.replace("_", " ") in user_message.lower(), f"Error type not mentioned in user message for {error_type}"
        
        await client.disconnect()
    
    @pytest.mark.asyncio 
    async def test_system_recovery_after_transient_failures(self, websocket_core, failure_simulator, event_validator):
        """Test system recovers gracefully after transient failures."""
        test_user = TEST_USERS["enterprise"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # First, cause a transient failure
        failing_request = {
            "type": "agent_request",
            "message": "Request that will fail transiently",
            "user_id": test_user.id,
            "simulate_transient_failure": True
        }
        
        await client.send(json.dumps(failing_request))
        await asyncio.sleep(3.0)  # Wait for failure and recovery attempt
        
        # Then send a normal request to test recovery
        normal_request = {
            "type": "agent_request", 
            "message": "Normal request after recovery",
            "user_id": test_user.id
        }
        
        await client.send(json.dumps(normal_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=15.0)
        
        # Validate failure occurred
        failure_events = [e for e in events if e.get("type") == "agent_error"]
        assert len(failure_events) > 0, "No failure events received"
        
        # Validate recovery occurred
        recovery_events = [e for e in events if e.get("type") == "system_recovered"]
        assert len(recovery_events) > 0, "No recovery events received"
        
        recovery_event = recovery_events[0]
        assert "recovery_successful" in recovery_event, "Missing recovery success status"
        assert recovery_event.get("recovery_successful") is True, "Recovery should be successful"
        
        # Validate normal operation resumed
        success_events = [e for e in events if e.get("type") == "agent_response" and e.get("status") == "success"]
        assert len(success_events) > 0, "No successful responses after recovery"
        
        # Verify response time is reasonable
        success_event = success_events[0]
        if "execution_time" in success_event:
            assert success_event["execution_time"] < 5.0, "Response time should be reasonable after recovery"
        
        await client.disconnect()


class TestCircuitBreakerWebSocketIntegration:
    """Test circuit breaker integration with WebSocket communication."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_prevents_requests(self, websocket_core, failure_simulator, event_validator):
        """Test circuit breaker in open state prevents new agent requests."""
        test_user = TEST_USERS["free"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Simulate circuit breaker already in open state
        cb_open_notification = {
            "type": "circuit_breaker_state_change",
            "state": "open",
            "agent_name": "test_agent",
            "user_id": test_user.id
        }
        
        # Send agent request when circuit breaker is open
        agent_request = {
            "type": "agent_request",
            "message": "Request when circuit breaker is open", 
            "user_id": test_user.id,
            "circuit_breaker_state": "open"
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=5.0)
        
        # Validate request was rejected
        rejection_events = [e for e in events if e.get("type") == "request_rejected"]
        assert len(rejection_events) > 0, "Request should be rejected when circuit breaker is open"
        
        rejection_event = rejection_events[0]
        assert "reason" in rejection_event, "Missing rejection reason"
        assert "circuit_breaker" in rejection_event["reason"].lower(), "Rejection should mention circuit breaker"
        assert "retry_after" in rejection_event, "Missing retry after info"
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_allows_limited_requests(self, websocket_core, event_validator):
        """Test circuit breaker in half-open state allows limited requests."""
        test_user = TEST_USERS["early"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Send test request when circuit breaker is half-open
        agent_request = {
            "type": "agent_request",
            "message": "Test request in half-open state",
            "user_id": test_user.id,
            "circuit_breaker_state": "half_open"
        }
        
        await client.send(json.dumps(agent_request))
        
        # Collect events
        events = await event_validator.collect_events(client, timeout=8.0)
        
        # Validate test request was allowed
        test_events = [e for e in events if e.get("type") == "circuit_breaker_test_request"]
        assert len(test_events) > 0, "Test request should be allowed in half-open state"
        
        test_event = test_events[0]
        assert "test_request_id" in test_event, "Missing test request ID"
        assert "monitoring_enabled" in test_event, "Missing monitoring status"
        
        await client.disconnect()


class TestErrorEventDetailValidation:
    """Test detailed validation of error event structures."""
    
    @pytest.mark.asyncio
    async def test_error_event_schema_compliance(self, websocket_core, failure_simulator):
        """Test all error events comply with expected schema."""
        test_user = TEST_USERS["enterprise"]
        client = await websocket_core.establish_authenticated_connection(test_user.id)
        
        # Generate various error types
        error_types = ["llm_timeout", "rate_limit", "memory_exhaustion", "network_failure", "invalid_response"]
        
        for error_type in error_types:
            agent_request = {
                "type": "agent_request",
                "message": f"Generate {error_type}",
                "user_id": test_user.id,
                "simulate_failure": error_type
            }
            await client.send(json.dumps(agent_request))
            await asyncio.sleep(1.0)
        
        # Collect all error events
        validator = WebSocketEventValidator()
        events = await validator.collect_events(client, timeout=12.0)
        
        error_events = [e for e in events if e.get("type") == "agent_error"]
        assert len(error_events) >= len(error_types), "Not all error types generated events"
        
        # Validate schema for each error event
        required_fields = ["type", "error_type", "message", "agent_name", "timestamp", "is_recoverable", "user_id"]
        optional_fields = ["context", "suggested_action", "retry_possible", "estimated_recovery_time", "user_message"]
        
        for event in error_events:
            # Validate required fields
            for field in required_fields:
                assert field in event, f"Missing required field '{field}' in error event"
                assert event[field] is not None, f"Required field '{field}' is null"
            
            # Validate field types
            assert isinstance(event["timestamp"], str), "Timestamp should be string"
            assert isinstance(event["is_recoverable"], bool), "is_recoverable should be boolean" 
            assert isinstance(event["message"], str), "Message should be string"
            assert len(event["message"]) > 0, "Message should not be empty"
        
        await client.disconnect()