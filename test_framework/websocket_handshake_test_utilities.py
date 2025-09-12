"""
WebSocket Handshake Test Utilities

Business Value Justification:
- Segment: Platform/Internal - Test Infrastructure  
- Business Goal: Provide robust testing tools for WebSocket handshake issues
- Value Impact: Enables comprehensive validation of $500K+ ARR chat functionality
- Strategic Impact: Critical for preventing regression in Golden Path user flows

USAGE:
These utilities support the comprehensive WebSocket authentication handshake test plan.
They provide reusable components for testing RFC 6455 compliance, timing issues,
and business value preservation during handshake fixes.

TESTING STRATEGY:
- Mock WebSocket connections with proper header simulation
- Sequence tracking for handshake timing validation  
- Business value validation helpers
- Performance regression testing utilities
- Error scenario simulation tools
"""

import asyncio
import json
import uuid
import time
import logging
from typing import Dict, Optional, Any, List, Tuple, Callable
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import pytest

# Core WebSocket testing imports
from test_framework.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@dataclass
class WebSocketHandshakeSequence:
    """
    Tracks the sequence of WebSocket handshake operations for RFC 6455 compliance testing.
    
    This class helps verify that handshake operations happen in the correct order
    according to RFC 6455 specifications.
    """
    sequence_log: List[str] = field(default_factory=list)
    timing_log: List[Tuple[str, float]] = field(default_factory=list)
    start_time: Optional[float] = None
    
    def log_operation(self, operation: str):
        """Log a handshake operation with timestamp."""
        if self.start_time is None:
            self.start_time = time.time()
        
        current_time = time.time()
        relative_time = current_time - self.start_time
        
        self.sequence_log.append(operation)
        self.timing_log.append((operation, relative_time))
        
        logger.debug(f"Handshake sequence [{relative_time:.3f}s]: {operation}")
    
    def validate_rfc6455_compliance(self) -> Dict[str, Any]:
        """
        Validate that the sequence complies with RFC 6455 handshake requirements.
        
        Returns:
            Dict with validation results and any compliance violations
        """
        violations = []
        
        # Check that JWT extraction happens before accept()
        jwt_extraction_index = None
        accept_index = None
        
        for i, operation in enumerate(self.sequence_log):
            if "jwt_extract" in operation.lower():
                jwt_extraction_index = i
            elif "accept" in operation.lower():
                accept_index = i
                break
        
        if accept_index is not None and jwt_extraction_index is not None:
            if jwt_extraction_index > accept_index:
                violations.append("JWT extraction must happen before WebSocket accept()")
        elif accept_index is not None and jwt_extraction_index is None:
            violations.append("JWT extraction must happen before WebSocket accept()")
        
        # Check that subprotocol negotiation happens before accept()
        negotiation_index = None
        for i, operation in enumerate(self.sequence_log):
            if "negotiat" in operation.lower() and "subprotocol" in operation.lower():
                negotiation_index = i
                break
        
        if accept_index is not None and negotiation_index is not None:
            if negotiation_index > accept_index:
                violations.append("Subprotocol negotiation must happen before WebSocket accept()")
        elif accept_index is not None and negotiation_index is None:
            violations.append("Subprotocol negotiation should happen before WebSocket accept()")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "sequence": self.sequence_log,
            "timing": self.timing_log,
            "total_time": self.timing_log[-1][1] if self.timing_log else 0
        }


class MockWebSocketFactory:
    """
    Factory for creating mock WebSocket connections with realistic behavior.
    
    This factory creates WebSocket mocks that behave like real FastAPI WebSocket
    objects, including proper header handling and state management.
    """
    
    @staticmethod
    def create_websocket_with_jwt(
        jwt_token: str,
        connection_state: WebSocketState = WebSocketState.CONNECTING,
        additional_headers: Optional[Dict[str, str]] = None,
        use_authorization_header: bool = False
    ) -> Mock:
        """
        Create a mock WebSocket with JWT authentication.
        
        Args:
            jwt_token: JWT token to embed in headers
            connection_state: WebSocket connection state
            additional_headers: Additional headers to include
            use_authorization_header: If True, use Authorization header instead of subprotocol
            
        Returns:
            Mock WebSocket object with proper headers and methods
        """
        websocket = Mock(spec=WebSocket)
        websocket.state = connection_state
        
        # Build headers
        headers = {}
        if additional_headers:
            headers.update(additional_headers)
        
        if use_authorization_header:
            headers["authorization"] = f"Bearer {jwt_token}"
        else:
            headers["sec-websocket-protocol"] = f"jwt.{jwt_token}"
        
        # Add standard WebSocket headers
        headers.update({
            "host": "localhost:8000",
            "connection": "Upgrade", 
            "upgrade": "websocket",
            "sec-websocket-version": "13",
            "sec-websocket-key": "dGhlIHNhbXBsZSBub25jZQ=="
        })
        
        websocket.headers = headers
        
        # Mock WebSocket methods
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.send_json = AsyncMock() 
        websocket.receive_text = AsyncMock()
        websocket.receive_json = AsyncMock()
        websocket.close = AsyncMock()
        
        return websocket
    
    @staticmethod
    def create_malformed_websocket(
        malformed_type: str,
        connection_state: WebSocketState = WebSocketState.CONNECTING
    ) -> Mock:
        """
        Create a mock WebSocket with malformed headers for error testing.
        
        Args:
            malformed_type: Type of malformation to simulate
            connection_state: WebSocket connection state
            
        Returns:
            Mock WebSocket with malformed headers
        """
        websocket = Mock(spec=WebSocket)
        websocket.state = connection_state
        
        # Define malformed header cases
        malformed_headers = {
            "empty_jwt": {"sec-websocket-protocol": "jwt."},
            "invalid_jwt": {"sec-websocket-protocol": "jwt.invalid_token_format"},
            "no_jwt_protocol": {"sec-websocket-protocol": "other-protocol"},
            "oversized_jwt": {"sec-websocket-protocol": f"jwt.{'a' * 10000}"},
            "multiple_jwt": {"sec-websocket-protocol": "jwt.token1, jwt.token2, jwt.token3"},
            "malformed_base64": {"sec-websocket-protocol": "jwt.invalid!@#$%base64"},
            "missing_headers": {},  # No headers at all
        }
        
        headers = malformed_headers.get(malformed_type, {})
        
        # Add minimal WebSocket headers
        if malformed_type != "missing_headers":
            headers.update({
                "host": "localhost:8000", 
                "connection": "Upgrade",
                "upgrade": "websocket"
            })
        
        websocket.headers = headers
        
        # Mock methods that might be called during error handling
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_json = AsyncMock()
        
        return websocket


class WebSocketHandshakeValidator:
    """
    Validator for WebSocket handshake processes and RFC 6455 compliance.
    
    This validator provides comprehensive testing of handshake sequences,
    timing validation, and business value preservation checks.
    """
    
    def __init__(self):
        self.sequence_tracker = WebSocketHandshakeSequence()
        
    def track_operation(self, operation: str):
        """Track a handshake operation."""
        self.sequence_tracker.log_operation(operation)
    
    def validate_jwt_extraction_timing(self, websocket: Mock, jwt_token: str) -> Dict[str, Any]:
        """
        Validate JWT extraction happens at the correct time in handshake.
        
        Args:
            websocket: Mock WebSocket object
            jwt_token: Expected JWT token
            
        Returns:
            Validation results including timing and correctness
        """
        self.track_operation("jwt_extraction_start")
        
        try:
            # Import here to avoid circular imports
            from netra_backend.app.websocket_core.unified_jwt_protocol_handler import UnifiedJWTProtocolHandler
            
            extracted_jwt = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(websocket)
            
            self.track_operation("jwt_extraction_complete")
            
            success = extracted_jwt == jwt_token
            
            return {
                "success": success,
                "extracted_jwt": extracted_jwt,
                "expected_jwt": jwt_token,
                "operation": "jwt_extraction"
            }
            
        except Exception as e:
            self.track_operation(f"jwt_extraction_error_{type(e).__name__}")
            return {
                "success": False,
                "error": str(e),
                "operation": "jwt_extraction"
            }
    
    def validate_subprotocol_negotiation_timing(self, client_protocols: List[str]) -> Dict[str, Any]:
        """
        Validate subprotocol negotiation happens at correct time.
        
        Args:
            client_protocols: List of client-requested protocols
            
        Returns:
            Validation results for subprotocol negotiation
        """
        self.track_operation("subprotocol_negotiation_start")
        
        try:
            from netra_backend.app.websocket_core.unified_jwt_protocol_handler import negotiate_websocket_subprotocol
            
            accepted_protocol = negotiate_websocket_subprotocol(client_protocols)
            
            self.track_operation("subprotocol_negotiation_complete")
            
            return {
                "success": True,
                "accepted_protocol": accepted_protocol,
                "client_protocols": client_protocols,
                "operation": "subprotocol_negotiation"
            }
            
        except Exception as e:
            self.track_operation(f"subprotocol_negotiation_error_{type(e).__name__}")
            return {
                "success": False,
                "error": str(e),
                "operation": "subprotocol_negotiation"
            }
    
    def validate_websocket_accept_timing(self, websocket: Mock, subprotocol: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate WebSocket accept() call happens at correct time.
        
        Args:
            websocket: Mock WebSocket object
            subprotocol: Optional subprotocol to use
            
        Returns:
            Validation results for accept timing
        """
        self.track_operation("websocket_accept_start")
        
        try:
            # Track when accept is called
            if subprotocol:
                asyncio.create_task(websocket.accept(subprotocol=subprotocol))
                self.track_operation("websocket_accept_with_subprotocol")
            else:
                asyncio.create_task(websocket.accept())
                self.track_operation("websocket_accept_without_subprotocol")
            
            self.track_operation("websocket_accept_complete")
            
            return {
                "success": True,
                "subprotocol_used": subprotocol,
                "operation": "websocket_accept"
            }
            
        except Exception as e:
            self.track_operation(f"websocket_accept_error_{type(e).__name__}")
            return {
                "success": False,
                "error": str(e),
                "operation": "websocket_accept"
            }
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Get comprehensive RFC 6455 compliance report."""
        return self.sequence_tracker.validate_rfc6455_compliance()


class WebSocketBusinessValueValidator:
    """
    Validator for WebSocket business value preservation during handshake fixes.
    
    This validator ensures that handshake fixes don't break the core business
    functionality that generates revenue.
    """
    
    @staticmethod
    async def validate_golden_path_preservation(
        websocket_client_factory: Callable,
        jwt_token: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Validate that Golden Path functionality is preserved.
        
        Args:
            websocket_client_factory: Factory function for creating WebSocket clients
            jwt_token: Valid JWT token for authentication
            timeout: Timeout for operations
            
        Returns:
            Validation results for Golden Path preservation
        """
        results = {
            "golden_path_preserved": False,
            "authentication_success": False,
            "agent_execution_success": False, 
            "websocket_events_delivered": False,
            "business_value_delivered": False,
            "errors": [],
            "events_received": []
        }
        
        try:
            # Test Golden Path: Login  ->  AI Response
            async with websocket_client_factory(
                headers={"sec-websocket-protocol": f"jwt.{jwt_token}"}
            ) as client:
                
                # Step 1: Authentication (implicit in connection)
                results["authentication_success"] = True
                
                # Step 2: Send agent request  
                test_message = {
                    "type": "agent_request",
                    "message": "Test business value preservation",
                    "agent": "triage_agent",
                    "thread_id": f"test_thread_{uuid.uuid4().hex[:8]}"
                }
                
                await client.send_json(test_message)
                
                # Step 3: Collect agent response events
                events = []
                required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
                
                async for event in client.receive_events(timeout=timeout):
                    events.append(event)
                    results["events_received"].append(event.get("type"))
                    
                    if event.get("type") == "agent_completed":
                        break
                
                # Step 4: Validate business value delivery
                event_types = [event.get("type") for event in events]
                
                # Check if all required events were delivered
                missing_events = [e for e in required_events if e not in event_types]
                if not missing_events:
                    results["websocket_events_delivered"] = True
                else:
                    results["errors"].append(f"Missing required events: {missing_events}")
                
                # Check if agent delivered business value
                completion_event = next((e for e in events if e.get("type") == "agent_completed"), None)
                if completion_event and "result" in completion_event.get("data", {}):
                    results["business_value_delivered"] = True
                    results["agent_execution_success"] = True
                else:
                    results["errors"].append("Agent did not deliver business value")
                
                # Overall Golden Path success
                results["golden_path_preserved"] = (
                    results["authentication_success"] and
                    results["agent_execution_success"] and  
                    results["websocket_events_delivered"] and
                    results["business_value_delivered"]
                )
                
        except Exception as e:
            results["errors"].append(f"Golden Path validation error: {str(e)}")
        
        return results
    
    @staticmethod
    def validate_revenue_protection(validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that revenue-generating functionality is protected.
        
        Args:
            validation_results: Results from Golden Path validation
            
        Returns:
            Revenue protection analysis
        """
        # Chat functionality represents 90% of platform value
        chat_functionality_score = 0
        
        if validation_results.get("authentication_success"):
            chat_functionality_score += 20  # User can connect
            
        if validation_results.get("websocket_events_delivered"):
            chat_functionality_score += 30  # Real-time interaction works
            
        if validation_results.get("agent_execution_success"):
            chat_functionality_score += 30  # AI responses work
            
        if validation_results.get("business_value_delivered"):
            chat_functionality_score += 20  # Actual value delivered
        
        # Calculate revenue risk
        revenue_at_risk_percentage = max(0, 100 - chat_functionality_score)
        estimated_revenue_impact = "$500K+ ARR" if revenue_at_risk_percentage > 50 else f"{revenue_at_risk_percentage}% at risk"
        
        return {
            "chat_functionality_score": chat_functionality_score,
            "revenue_at_risk_percentage": revenue_at_risk_percentage,
            "estimated_revenue_impact": estimated_revenue_impact,
            "protection_status": "PROTECTED" if chat_functionality_score >= 80 else "AT_RISK",
            "recommendations": _get_revenue_protection_recommendations(chat_functionality_score)
        }


def _get_revenue_protection_recommendations(score: int) -> List[str]:
    """Get recommendations for revenue protection based on functionality score."""
    recommendations = []
    
    if score < 20:
        recommendations.append("CRITICAL: Authentication is broken - users cannot connect")
    elif score < 50:
        recommendations.append("HIGH: Core chat functionality is impaired")
    elif score < 80:
        recommendations.append("MEDIUM: Some chat features not working properly")
    else:
        recommendations.append("LOW: Minor issues that don't impact core value")
    
    if score < 80:
        recommendations.extend([
            "Prioritize fixing WebSocket handshake issues",
            "Test with real user scenarios",
            "Monitor business metrics during fixes",
            "Have rollback plan ready"
        ])
    
    return recommendations


class WebSocketPerformanceProfiler:
    """
    Performance profiler for WebSocket handshake operations.
    
    This profiler helps ensure that handshake fixes don't introduce
    performance regressions that could impact user experience.
    """
    
    def __init__(self):
        self.operations = []
        self.start_time = None
    
    @asynccontextmanager
    async def profile_operation(self, operation_name: str):
        """Profile a single WebSocket operation."""
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            self.operations.append({
                "operation": operation_name,
                "duration": duration,
                "timestamp": start_time
            })
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        if not self.operations:
            return {"error": "No operations profiled"}
        
        durations = [op["duration"] for op in self.operations]
        
        return {
            "total_operations": len(self.operations),
            "total_time": sum(durations),
            "average_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations),
            "operations": self.operations,
            "performance_rating": _calculate_performance_rating(durations)
        }
    
    def assert_performance_requirements(
        self,
        max_total_time: float = 1.0,
        max_average_time: float = 0.1,
        max_single_operation: float = 0.5
    ):
        """Assert that performance requirements are met."""
        report = self.get_performance_report()
        
        if report.get("error"):
            pytest.fail(f"Performance profiling error: {report['error']}")
        
        if report["total_time"] > max_total_time:
            pytest.fail(f"Total time {report['total_time']:.3f}s exceeds limit {max_total_time}s")
        
        if report["average_time"] > max_average_time:
            pytest.fail(f"Average time {report['average_time']:.3f}s exceeds limit {max_average_time}s")
        
        if report["max_time"] > max_single_operation:
            pytest.fail(f"Slowest operation {report['max_time']:.3f}s exceeds limit {max_single_operation}s")


def _calculate_performance_rating(durations: List[float]) -> str:
    """Calculate performance rating based on operation durations."""
    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)
    
    if avg_duration < 0.01 and max_duration < 0.05:
        return "EXCELLENT"
    elif avg_duration < 0.05 and max_duration < 0.1:
        return "GOOD" 
    elif avg_duration < 0.1 and max_duration < 0.5:
        return "ACCEPTABLE"
    else:
        return "NEEDS_IMPROVEMENT"


# Convenience functions for test integration

def create_mock_websocket(
    headers: Optional[Dict[str, str]] = None,
    state: WebSocketState = WebSocketState.CONNECTING
) -> Mock:
    """Create a basic mock WebSocket for testing."""
    return MockWebSocketFactory.create_websocket_with_jwt(
        jwt_token="test_jwt_token",
        connection_state=state,
        additional_headers=headers or {}
    )


def create_handshake_validator() -> WebSocketHandshakeValidator:
    """Create a WebSocket handshake validator for testing."""
    return WebSocketHandshakeValidator()


def create_performance_profiler() -> WebSocketPerformanceProfiler:
    """Create a WebSocket performance profiler for testing."""
    return WebSocketPerformanceProfiler()


# Test fixtures for pytest integration

@pytest.fixture
def websocket_handshake_validator():
    """Pytest fixture for WebSocket handshake validator."""
    return WebSocketHandshakeValidator()


@pytest.fixture
def websocket_performance_profiler():
    """Pytest fixture for WebSocket performance profiler."""  
    return WebSocketPerformanceProfiler()


@pytest.fixture
def mock_websocket_factory():
    """Pytest fixture for mock WebSocket factory."""
    return MockWebSocketFactory()


# Business value testing utilities

def assert_golden_path_preserved(validation_results: Dict[str, Any]):
    """Assert that Golden Path business functionality is preserved."""
    if not validation_results.get("golden_path_preserved"):
        errors = validation_results.get("errors", ["Unknown error"])
        pytest.fail(f"Golden Path not preserved: {'; '.join(errors)}")


def assert_revenue_protection(validation_results: Dict[str, Any], minimum_score: int = 80):
    """Assert that revenue-generating functionality is protected."""
    revenue_analysis = WebSocketBusinessValueValidator.validate_revenue_protection(validation_results)
    
    if revenue_analysis["chat_functionality_score"] < minimum_score:
        pytest.fail(
            f"Revenue at risk: {revenue_analysis['estimated_revenue_impact']} "
            f"(score: {revenue_analysis['chat_functionality_score']}/100)"
        )


def assert_no_1011_errors(operation_results: List[Dict[str, Any]]):
    """Assert that operations don't generate 1011 WebSocket policy errors."""
    for result in operation_results:
        if result.get("error") and "1011" in str(result["error"]):
            pytest.fail(f"1011 error detected in operation {result.get('operation', 'unknown')}: {result['error']}")


if __name__ == "__main__":
    print("WebSocket Handshake Test Utilities")
    print("=" * 40)
    print("Provides comprehensive testing tools for WebSocket handshake validation")
    print("Supports RFC 6455 compliance testing and business value preservation")