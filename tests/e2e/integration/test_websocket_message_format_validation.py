"""E2E WebSocket Message Format Validation - Critical P0 Test

CRITICAL E2E tests for WebSocket message format consistency between frontend/backend.
This test validates that message structures are aligned, field names are consistent,
and coroutine objects are properly handled.

Business Value Justification (BVJ):
1. Segment: ALL customer tiers (Critical system reliability)
2. Business Goal: Prevent silent failures in WebSocket communication
3. Value Impact: Ensures real-time features work correctly for all users
4. Revenue Impact: Protects revenue by preventing communication breakdowns

CRITICAL VALIDATIONS:
- Frontend "content" field correctly maps to backend "content" field  
- Message structure is consistent: always {type, payload} format
- No mixing of {event, data} with {type, payload} structures
- All async/await patterns work correctly (no coroutine objects leaked)
- Field names match between frontend TypeScript and backend Python
- Required fields are always present, optional fields have proper defaults

KNOWN ISSUES TESTED:
- Frontend sends "content", backend handler was looking for "text" (fixed?)
- Coroutine objects being accessed without await
- Type/payload vs event/data structure mismatch
- Missing timestamp fields in some events

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (focused on message format validation)
- Function size: <25 lines each
- Real WebSocket connections, deterministic under 30 seconds
- Tests actual message flow between frontend and backend
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union
import pytest
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS, TEST_ENDPOINTS
from tests.e2e.integration.websocket_message_format_validators import (
    MessageFormatValidator, FieldConsistencyChecker, CoroutineErrorDetector, MessageStructureValidator
)


@pytest.mark.asyncio
@pytest.mark.e2e
class WebSocketMessageFormatValidationTests:
    """Test #7: WebSocket Message Format Validation - P0 CRITICAL"""
    
    @pytest.fixture
    def format_validator(self):
        """Initialize message format validator."""
        return MessageFormatValidator()
    
    @pytest.fixture  
    def field_checker(self):
        """Initialize field consistency checker."""
        return FieldConsistencyChecker()
    
    @pytest.fixture
    def coroutine_detector(self):
        """Initialize coroutine error detector."""
        return CoroutineErrorDetector()
    
    @pytest.fixture
    def structure_validator(self):
        """Initialize message structure validator."""
        return MessageStructureValidator()

    @pytest.mark.e2e
    async def test_user_message_content_field_consistency(self, format_validator, field_checker):
        """Test that frontend 'content' field maps correctly to backend 'content' field."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            # Connect and test content field mapping
            client = await format_validator.establish_test_connection(user_id)
            
            # Test 1: Frontend sends "content" field
            frontend_message = {
                "type": "user_message",
                "payload": {
                    "content": "Test message with content field",
                    "thread_id": None
                }
            }
            
            field_validation = await field_checker.validate_content_field_mapping(
                client, frontend_message, user_id
            )
            
            # Validate field consistency
            assert field_validation["content_field_accepted"], "Backend rejected 'content' field"
            assert field_validation["message_processed"], "Message was not processed by backend"
            assert not field_validation["silent_failure"], "Silent failure detected in content mapping"
            
            # Test 2: Ensure backward compatibility with "text" field
            legacy_message = {
                "type": "user_message", 
                "payload": {
                    "text": "Test message with legacy text field",
                    "thread_id": None
                }
            }
            
            legacy_validation = await field_checker.validate_legacy_field_support(
                client, legacy_message, user_id
            )
            
            assert legacy_validation["legacy_field_supported"], "Legacy 'text' field not supported"
            assert legacy_validation["backward_compatible"], "Backward compatibility broken"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_message_structure_type_payload_consistency(self, structure_validator):
        """Test message structure is consistent: always {type, payload} format."""
        user_id = TEST_USERS["early"].id
        
        try:
            client = await structure_validator.establish_validated_connection(user_id)
            
            # Test all required message types use {type, payload} structure
            message_types = [
                "user_message",
                "agent_started", 
                "agent_completed",
                "error",
                "system",
                "partial_result"
            ]
            
            structure_results = {}
            for msg_type in message_types:
                test_message = structure_validator.create_test_message(msg_type, user_id)
                validation = await structure_validator.validate_message_structure(
                    client, test_message, msg_type
                )
                structure_results[msg_type] = validation
            
            # Validate all message types use consistent structure
            for msg_type, result in structure_results.items():
                assert result["has_type_field"], f"{msg_type} missing 'type' field"
                assert result["has_payload_field"], f"{msg_type} missing 'payload' field"
                assert not result["has_event_data_structure"], f"{msg_type} uses deprecated {{event, data}} structure"
                assert result["structure_consistent"], f"{msg_type} structure inconsistent"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_coroutine_error_handling_validation(self, coroutine_detector):
        """Test that coroutine objects are properly handled (no leaked coroutines)."""
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await coroutine_detector.establish_monitored_connection(user_id)
            
            # Test messages that trigger async operations
            async_test_messages = [
                {
                    "type": "user_message",
                    "payload": {"content": "Trigger agent processing", "thread_id": None}
                },
                {
                    "type": "start_agent", 
                    "payload": {"query": "Test agent startup", "user_id": user_id}
                },
                {
                    "type": "get_thread_history",
                    "payload": {"limit": 10}
                }
            ]
            
            coroutine_validations = []
            for test_msg in async_test_messages:
                validation = await coroutine_detector.detect_coroutine_errors(
                    client, test_msg, user_id
                )
                coroutine_validations.append(validation)
            
            # Validate no coroutine objects leaked
            for validation in coroutine_validations:
                assert not validation["coroutine_object_leaked"], "Coroutine object leaked to client"
                assert validation["async_await_correct"], "Async/await pattern incorrect"
                assert not validation["uncaught_coroutine_warning"], "Uncaught coroutine warning detected"
                assert validation["response_properly_awaited"], "Response not properly awaited"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_agent_event_message_formats(self, format_validator):
        """Test agent events have correct message formats with required fields."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await format_validator.establish_test_connection(user_id)
            
            # Trigger agent execution to generate events
            agent_trigger_message = {
                "type": "user_message",
                "payload": {
                    "content": "Start agent to test event formats",
                    "thread_id": None
                }
            }
            
            await client.send(agent_trigger_message)
            
            # Collect agent events
            event_validations = await format_validator.collect_and_validate_agent_events(
                client, timeout=10.0
            )
            
            # Validate agent_started event format
            if "agent_started" in event_validations:
                started_event = event_validations["agent_started"]
                assert started_event["has_run_id"], "agent_started missing run_id"
                assert started_event["has_agent_name"], "agent_started missing agent_name"
                assert started_event["has_timestamp"], "agent_started missing timestamp"
                assert started_event["payload_complete"], "agent_started payload incomplete"
            
            # Validate agent_completed event format
            if "agent_completed" in event_validations:
                completed_event = event_validations["agent_completed"]
                assert completed_event["has_agent_name"], "agent_completed missing agent_name"
                assert completed_event["has_duration"], "agent_completed missing duration_ms"
                assert completed_event["has_result"], "agent_completed missing result"
                assert completed_event["structure_valid"], "agent_completed structure invalid"
            
            # Validate error events format (if any)
            if "error" in event_validations:
                error_event = event_validations["error"]
                assert error_event["has_error_code"], "error event missing code"
                assert error_event["has_error_message"], "error event missing message"
                assert error_event["has_error_details"], "error event missing details"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_streaming_event_format_validation(self, format_validator):
        """Test streaming events (partial_result) have correct format."""
        user_id = TEST_USERS["early"].id
        
        try:
            client = await format_validator.establish_test_connection(user_id)
            
            # Trigger streaming response
            streaming_message = {
                "type": "user_message",
                "payload": {
                    "content": "Generate a long response to test streaming",
                    "thread_id": None
                }
            }
            
            streaming_validation = await format_validator.validate_streaming_events(
                client, streaming_message, user_id
            )
            
            # Validate streaming event format
            assert streaming_validation["streaming_events_received"], "No streaming events received"
            assert streaming_validation["all_events_have_content"], "Some streaming events missing content"
            assert streaming_validation["all_events_have_is_complete"], "Some streaming events missing is_complete"
            assert streaming_validation["final_event_marked_complete"], "Final streaming event not marked complete"
            assert streaming_validation["content_accumulated_correctly"], "Streaming content not accumulated correctly"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_system_event_format_consistency(self, structure_validator):
        """Test system events have consistent format structure."""
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await structure_validator.establish_validated_connection(user_id)
            
            # Test system events format
            system_events_validation = await structure_validator.validate_system_events_format(
                client, user_id
            )
            
            # Validate system event structure
            assert system_events_validation["system_events_use_type_payload"], "System events don't use {type, payload}"
            assert not system_events_validation["mixed_event_data_structure"], "Mixed {event, data} structure found"
            assert system_events_validation["all_events_timestamped"], "Not all system events have timestamps"
            assert system_events_validation["event_data_consistent"], "System event data structure inconsistent"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_field_name_typescript_python_consistency(self, field_checker):
        """Test field names match between frontend TypeScript and backend Python."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await field_checker.establish_field_test_connection(user_id)
            
            # Test TypeScript/Python field mapping
            field_mappings = {
                "content": "content",  # UserMessagePayload.content -> backend content
                "thread_id": "thread_id",  # Optional thread_id mapping
                "references": "references",  # Message references array
                "run_id": "run_id",  # Agent run identifier
                "agent_name": "agent_name",  # Agent name in events
                "timestamp": "timestamp"  # Event timestamps
            }
            
            mapping_validation = await field_checker.validate_field_name_consistency(
                client, field_mappings, user_id
            )
            
            # Validate field name consistency
            for field_name, validation in mapping_validation.items():
                assert validation["frontend_field_accepted"], f"Frontend field '{field_name}' not accepted"
                assert validation["backend_field_mapped"], f"Backend field '{field_name}' not mapped correctly"
                assert not validation["field_name_mismatch"], f"Field name mismatch for '{field_name}'"
                assert validation["type_consistency"], f"Type inconsistency for field '{field_name}'"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_required_optional_fields_validation(self, format_validator):
        """Test required fields are always present, optional fields have proper defaults."""
        user_id = TEST_USERS["early"].id
        
        try:
            client = await format_validator.establish_test_connection(user_id)
            
            # Test required fields validation
            required_fields_test = await format_validator.validate_required_fields(
                client, user_id
            )
            
            # Validate required fields
            assert required_fields_test["user_message_content_required"], "user_message content not required"
            assert required_fields_test["agent_events_run_id_required"], "agent events run_id not required"
            assert required_fields_test["error_events_message_required"], "error events message not required"
            assert required_fields_test["all_events_type_required"], "event type not required"
            
            # Test optional fields defaults
            optional_fields_test = await format_validator.validate_optional_fields(
                client, user_id
            )
            
            # Validate optional fields
            assert optional_fields_test["thread_id_defaults_to_null"], "thread_id doesn't default to null"
            assert optional_fields_test["references_defaults_to_empty"], "references doesn't default to empty array"
            assert optional_fields_test["metadata_defaults_properly"], "metadata doesn't default properly"
            assert optional_fields_test["timestamps_auto_generated"], "timestamps not auto-generated"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_backwards_compatibility_validation(self, field_checker):
        """Test that backwards compatibility is maintained for legacy field names."""
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await field_checker.establish_field_test_connection(user_id)
            
            # Test legacy message formats still work
            legacy_formats = [
                {
                    "type": "user_message",
                    "payload": {"text": "Legacy text field", "thread_id": None}
                },
                {
                    "event": "user_message",  # Legacy event format
                    "data": {"content": "Legacy event/data structure"}
                }
            ]
            
            compatibility_validation = await field_checker.validate_backwards_compatibility(
                client, legacy_formats, user_id
            )
            
            # Validate backwards compatibility
            assert compatibility_validation["text_field_supported"], "Legacy 'text' field not supported"
            assert compatibility_validation["event_data_converted"], "Legacy {event, data} not converted"
            assert compatibility_validation["no_breaking_changes"], "Breaking changes detected"
            assert compatibility_validation["graceful_migration"], "Migration not graceful"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_end_to_end_message_flow_validation(self, format_validator):
        """Test complete end-to-end message flow with format validation."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await format_validator.establish_test_connection(user_id)
            
            # Test complete message flow
            start_time = time.time()
            
            # Send user message and validate complete flow
            e2e_message = {
                "type": "user_message",
                "payload": {
                    "content": "Complete end-to-end message flow test",
                    "thread_id": None,
                    "references": []
                }
            }
            
            flow_validation = await format_validator.validate_complete_message_flow(
                client, e2e_message, user_id, timeout=15.0
            )
            
            total_time = time.time() - start_time
            
            # Validate complete flow
            assert flow_validation["message_sent_successfully"], "Message not sent successfully"
            assert flow_validation["agent_started_event_received"], "agent_started event not received"
            assert flow_validation["agent_completed_event_received"], "agent_completed event not received"
            assert flow_validation["all_events_properly_formatted"], "Not all events properly formatted"
            assert flow_validation["no_coroutine_errors"], "Coroutine errors detected"
            assert flow_validation["field_consistency_maintained"], "Field consistency not maintained"
            assert total_time < 30.0, f"E2E flow took {total_time:.2f}s, exceeding 30s limit"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
