"""
Test WebSocket JSON SSOT Violations Reproduction

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical)
- Business Goal: Protect $120K+ MRR from WebSocket 1011 errors
- Value Impact: Reproduces exact JSON validation failures causing chat disconnections
- Strategic Impact: Critical for diagnosing WebSocket stability issues in GitHub Issue #117

This test suite reproduces the specific JSON SSOT violations that cause WebSocket 1011 errors,
timeout failures, and agent execution breakdowns identified in P1 critical tests.

@compliance CLAUDE.md - Real services over mocks for authentic testing
@compliance SPEC/core.xml - SSOT patterns for message validation
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase, require_docker_services

# CRITICAL: Import actual WebSocket message types and handlers
from netra_backend.app.websocket_core.types import (
    MessageType, 
    WebSocketMessage,
    ServerMessage,
    ErrorMessage,
    create_standard_message,
    create_error_message,
    normalize_message_type
)
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    AgentRequestHandler,
    get_message_router
)
from netra_backend.app.services.websocket.message_handler import StartAgentHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env


class TestWebSocketJSONSSOTViolationsReproduction(BaseIntegrationTest):
    """
    Reproduce WebSocket JSON SSOT violations that cause P1 critical failures.
    
    CRITICAL: These tests MUST fail initially to reproduce the exact issues
    identified in GitHub Issue #117 test plan.
    """
    
    @pytest.mark.unit
    @pytest.mark.real_services  
    async def test_websocket_message_type_validation_ssot_violation(self):
        """
        REPRODUCTION TEST: WebSocket message type validation SSOT violations.
        
        This test reproduces the specific issue where message type normalization
        fails due to SSOT violations, causing WebSocket 1011 errors.
        
        Expected to FAIL until remediation is complete.
        """
        # Create malformed message that should trigger SSOT violation
        malformed_message = {
            "type": "EXECUTE_AGENT",  # Wrong case - should be "execute_agent"
            "data": {
                "agent_name": "test_agent",
                "user_request": "Test request"
            },
            "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time()
        }
        
        # CRITICAL: This should fail validation due to SSOT violation
        # The message type doesn't match any SSOT enum values
        try:
            normalized_type = normalize_message_type("EXECUTE_AGENT")
            # If this doesn't raise an exception, we have an SSOT violation
            assert False, f"SSOT VIOLATION: Message type 'EXECUTE_AGENT' should not be valid but was normalized to: {normalized_type}"
        except (ValueError, KeyError, AttributeError) as e:
            # Expected failure - SSOT validation working correctly
            assert "EXECUTE_AGENT" in str(e) or "not found" in str(e).lower()
            
        # Test JSON serialization SSOT violation
        try:
            websocket_message = create_standard_message(
                message_type="EXECUTE_AGENT",  # Invalid type
                data=malformed_message["data"]
            )
            # If this succeeds, we have an SSOT violation
            assert False, f"SSOT VIOLATION: Invalid message type should not create valid WebSocketMessage: {websocket_message}"
        except (ValueError, TypeError, AttributeError) as e:
            # Expected failure - SSOT validation working
            assert "EXECUTE_AGENT" in str(e) or "invalid" in str(e).lower()
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_websocket_json_schema_validation_failures(self):
        """
        REPRODUCTION TEST: JSON schema validation failures in WebSocket messages.
        
        This reproduces the specific schema validation errors that cause
        timeout failures and agent execution breakdowns.
        
        Expected to FAIL until remediation is complete.
        """
        # Test invalid JSON structure that should fail SSOT validation
        invalid_json_structures = [
            # Missing required fields
            {"type": "agent_request"},  # Missing data
            {"data": {"request": "test"}},  # Missing type
            
            # Invalid field types
            {"type": 123, "data": "not_an_object"},  # Wrong types
            {"type": "agent_request", "data": "should_be_dict"},
            
            # Extra forbidden fields that violate SSOT
            {
                "type": "agent_request",
                "data": {"request": "test"},
                "forbidden_field": "should_not_exist",  # SSOT violation
                "another_violation": {"nested": "data"}
            }
        ]
        
        validation_failures = []
        
        for i, invalid_structure in enumerate(invalid_json_structures):
            try:
                # Try to create a WebSocket message with invalid structure
                message = create_standard_message(
                    message_type=invalid_structure.get("type", "unknown"),
                    data=invalid_structure.get("data", {})
                )
                
                # If this succeeds, we have an SSOT violation
                validation_failures.append(f"Structure {i}: SSOT violation - invalid structure created valid message: {message}")
                
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                # Expected failure - SSOT working correctly
                continue
        
        # CRITICAL: If any invalid structures passed validation, we have SSOT violations
        if validation_failures:
            pytest.fail(f"SSOT VIOLATIONS detected in JSON schema validation:\n" + "\n".join(validation_failures))
    
    @pytest.mark.unit 
    @pytest.mark.real_services
    async def test_websocket_message_serialization_ssot_violations(self):
        """
        REPRODUCTION TEST: Message serialization SSOT violations.
        
        This reproduces the specific serialization issues that cause
        WebSocket connection failures and 1011 errors.
        
        Expected to FAIL until remediation is complete.
        """
        # Test serialization of complex nested data structures
        complex_data = {
            "nested_object": {
                "deep_nesting": {
                    "level_3": {
                        "circular_ref": None,  # Will be set to create circular reference
                        "large_data": "x" * 10000,  # Large data that might cause issues
                        "special_chars": "🚨💀🔥",  # Unicode that might break JSON
                        "null_values": None,
                        "empty_structures": {"empty_list": [], "empty_dict": {}}
                    }
                }
            },
            "function_object": lambda x: x,  # Non-serializable function
            "datetime_object": time.time(),  # Might not serialize properly
        }
        
        # Create circular reference to test SSOT handling
        complex_data["nested_object"]["deep_nesting"]["level_3"]["circular_ref"] = complex_data
        
        serialization_failures = []
        
        try:
            # Try to create WebSocket message with non-serializable data
            message = create_standard_message(
                message_type=MessageType.AGENT_REQUEST,
                data=complex_data
            )
            
            # Try to serialize to JSON
            json_str = json.dumps(message.dict())
            
            # If this succeeds, we may have an SSOT violation
            serialization_failures.append(f"POTENTIAL SSOT VIOLATION: Complex data serialized successfully: {len(json_str)} chars")
            
        except (TypeError, ValueError, RecursionError, UnicodeError) as e:
            # Expected failure - SSOT validation working
            assert "circular" in str(e).lower() or "serializable" in str(e).lower() or "recursion" in str(e).lower()
        
        # Test edge case serialization issues
        edge_cases = [
            {"infinity": float('inf')},  # Infinity values
            {"nan": float('nan')},  # NaN values  
            {"binary": b"binary_data"},  # Binary data
            {"set": {1, 2, 3}},  # Set (not JSON serializable)
        ]
        
        for edge_case in edge_cases:
            try:
                message = create_standard_message(
                    message_type=MessageType.AGENT_REQUEST,
                    data=edge_case
                )
                json.dumps(message.dict())
                serialization_failures.append(f"SSOT VIOLATION: Edge case passed: {edge_case}")
            except (TypeError, ValueError) as e:
                # Expected failure - SSOT working
                continue
        
        # CRITICAL: Report any SSOT violations found
        if serialization_failures:
            pytest.fail(f"JSON Serialization SSOT violations detected:\n" + "\n".join(serialization_failures))
    
    @pytest.mark.unit
    @pytest.mark.real_services
    async def test_websocket_message_routing_ssot_violations(self):
        """
        REPRODUCTION TEST: Message routing SSOT violations.
        
        This reproduces routing failures that cause agent execution
        to timeout or fail silently.
        
        Expected to FAIL until remediation is complete.
        """
        # Create message router to test routing
        router = get_message_router()
        
        # Test routing with invalid message types that should fail SSOT validation
        invalid_routing_cases = [
            # Case-sensitive issues
            {"type": "Agent_Request", "data": {"request": "test"}},
            {"type": "AGENT_request", "data": {"request": "test"}},
            {"type": "agent-request", "data": {"request": "test"}},  # Wrong separator
            
            # Deprecated message types that should no longer route
            {"type": "legacy_agent_start", "data": {"request": "test"}},
            {"type": "old_execute_agent", "data": {"request": "test"}},
            
            # Invalid routing destinations
            {"type": "agent_request", "data": {"route_to": "non_existent_handler"}},
        ]
        
        routing_violations = []
        
        for case in invalid_routing_cases:
            try:
                # Try to route invalid message - create a WebSocket message first
                test_message = create_standard_message(
                    message_type=case["type"],
                    data=case["data"]
                )
                
                # Try to find a handler for this message type
                handler = router.get_handler(test_message.type)
                
                # If routing succeeds, we have an SSOT violation
                if handler is not None:
                    routing_violations.append(f"SSOT VIOLATION: Invalid message routed successfully: {case}")
                    
            except (ValueError, KeyError, AttributeError, NotImplementedError) as e:
                # Expected failure - SSOT working correctly
                continue
            except Exception as e:
                # Unexpected error - might indicate deeper SSOT issue
                routing_violations.append(f"UNEXPECTED ERROR in routing: {case} -> {e}")
        
        # Test that valid messages DO route correctly (sanity check)
        try:
            valid_message = create_standard_message(
                message_type=MessageType.AGENT_REQUEST,
                data={"request": "valid test request"}
            )
            
            # This should NOT fail if SSOT is working
            handler = router.get_handler(valid_message.type)
            if handler is None:
                routing_violations.append(f"CRITICAL: Valid message failed to find handler: {valid_message.type}")
            
            # Valid message should route (or at least not raise an exception)
            
        except Exception as e:
            routing_violations.append(f"CRITICAL: Valid message failed to route: {e}")
        
        # Report SSOT violations
        if routing_violations:
            pytest.fail(f"Message routing SSOT violations detected:\n" + "\n".join(routing_violations))
    
    @pytest.mark.unit
    @pytest.mark.real_services  
    async def test_websocket_error_handling_ssot_violations(self):
        """
        REPRODUCTION TEST: Error handling SSOT violations.
        
        This reproduces error handling failures that cause silent
        failures and WebSocket 1011 disconnections.
        
        Expected to FAIL until remediation is complete.
        """
        # Test error message creation with invalid SSOT patterns
        error_handling_violations = []
        
        # Test invalid error message structures
        invalid_errors = [
            # Missing required error fields
            {"message": "error without code"},
            {"code": "ERROR_001"},  # Missing message
            
            # Invalid error codes not in SSOT
            {"code": "INVALID_ERROR_CODE", "message": "test"},
            {"code": 404, "message": "Wrong type for code"},  # Should be string
            
            # Invalid error data structures
            {"code": "VALIDATION_ERROR", "message": "test", "data": "should_be_dict"},
        ]
        
        for invalid_error in invalid_errors:
            try:
                error_message = create_error_message(
                    error_code=invalid_error.get("code", "UNKNOWN"),
                    error_message=invalid_error.get("message", "Unknown error"),
                    error_data=invalid_error.get("data", {})
                )
                
                # If this succeeds with invalid data, we have SSOT violation
                error_handling_violations.append(f"SSOT VIOLATION: Invalid error created: {error_message}")
                
            except (ValueError, TypeError, KeyError) as e:
                # Expected failure - SSOT working
                continue
        
        # Test error propagation SSOT violations
        try:
            # Create handler with intentionally broken configuration
            broken_handler = StartAgentHandler(
                supervisor=None,  # This should cause immediate failure
                db_session_factory=None
            )
            
            # Try to handle a message with broken handler
            await broken_handler.handle(
                user_id="test_user",
                payload={"request": {"query": "test"}}
            )
            
            # If this doesn't raise an exception, we have SSOT violation
            error_handling_violations.append("SSOT VIOLATION: Broken handler did not fail as expected")
            
        except Exception as e:
            # Expected failure - SSOT error handling working
            assert "None" in str(e) or "supervisor" in str(e).lower()
        
        # Report error handling violations
        if error_handling_violations:
            pytest.fail(f"Error handling SSOT violations detected:\n" + "\n".join(error_handling_violations))