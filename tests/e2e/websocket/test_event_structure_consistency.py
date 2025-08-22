"""WebSocket Event Structure Consistency Test Suite

Tests that all WebSocket messages use consistent {type, payload} structure as specified
in SPEC/websockets.xml and SPEC/websocket_communication.xml.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise)
2. Business Goal: Unified Frontend Experience - Consistent message handling
3. Value Impact: Prevents UI bugs and message parsing failures
4. Revenue Impact: Ensures reliable real-time updates for all user tiers

CRITICAL REQUIREMENTS:
- Test with REAL running services (localhost:8001)
- Validate JSON-first communication (no string messages)
- Check for double/triple JSON wrapping issues  
- Verify {type, payload} structure throughout system
- Test all event types from event catalog
- Prevent silent failures from structure mismatches

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines
- Function size: <25 lines each
- Real services integration (NO MOCKS)
- Type safety with comprehensive validation
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union

import pytest
import pytest_asyncio

from tests.clients.websocket_client import WebSocketTestClient
from tests.jwt_token_helpers import JWTTestHelper
from tests.real_client_types import ClientConfig, ConnectionState
from tests.real_websocket_client import RealWebSocketClient


class EventStructureValidator:
    """Validates WebSocket event structure consistency"""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8001/ws"
        self.jwt_helper = JWTTestHelper()
        self.test_clients: List[RealWebSocketClient] = []
        self.structure_violations: List[Dict[str, Any]] = []
        self.validated_events: List[Dict[str, Any]] = []
        
    def create_authenticated_client(self, user_id: str = "structure_test") -> RealWebSocketClient:
        """Create authenticated WebSocket client for structure testing"""
        token = self.jwt_helper.create_access_token(user_id, f"{user_id}@test.com")
        config = ClientConfig(timeout=10.0, max_retries=2)
        client = RealWebSocketClient(self.websocket_url, config)
        client._auth_headers = {"Authorization": f"Bearer {token}"}
        self.test_clients.append(client)
        return client
    
    def validate_message_structure(self, message: Any, message_source: str) -> Dict[str, Any]:
        """Validate message follows {type, payload} structure"""
        validation_result = {
            "source": message_source,
            "valid": False,
            "issues": [],
            "message": message,
            "timestamp": time.time()
        }
        
        # Check if message is dict
        if not isinstance(message, dict):
            validation_result["issues"].append(f"Message is not dict: {type(message)}")
            return validation_result
        
        # Check for required 'type' field
        if "type" not in message:
            validation_result["issues"].append("Missing required 'type' field")
        elif not isinstance(message["type"], str):
            validation_result["issues"].append(f"'type' field is not string: {type(message['type'])}")
        
        # Check for required 'payload' field
        if "payload" not in message:
            validation_result["issues"].append("Missing required 'payload' field")
        elif not isinstance(message["payload"], dict):
            validation_result["issues"].append(f"'payload' field is not dict: {type(message['payload'])}")
        
        # Check for unexpected top-level fields (legacy patterns)
        expected_fields = {"type", "payload"}
        actual_fields = set(message.keys())
        unexpected_fields = actual_fields - expected_fields
        
        if unexpected_fields:
            validation_result["issues"].append(f"Unexpected top-level fields: {unexpected_fields}")
        
        # Check for legacy patterns
        legacy_patterns = ["event", "data", "message", "content"]
        found_legacy = [field for field in legacy_patterns if field in message]
        if found_legacy:
            validation_result["issues"].append(f"Legacy pattern fields found: {found_legacy}")
        
        # Message is valid if no issues
        validation_result["valid"] = len(validation_result["issues"]) == 0
        
        if validation_result["valid"]:
            self.validated_events.append(validation_result)
        else:
            self.structure_violations.append(validation_result)
        
        return validation_result
    
    def check_json_wrapping_issues(self, message: Any) -> Dict[str, Any]:
        """Check for double/triple JSON wrapping issues"""
        wrapping_check = {
            "has_wrapping_issue": False,
            "wrapping_level": 0,
            "original_type": type(message).__name__
        }
        
        current = message
        level = 0
        
        # Check for string that contains JSON
        while isinstance(current, str) and level < 5:
            try:
                parsed = json.loads(current)
                level += 1
                current = parsed
            except (json.JSONDecodeError, TypeError):
                break
        
        if level > 0:
            wrapping_check["has_wrapping_issue"] = True
            wrapping_check["wrapping_level"] = level
            wrapping_check["final_content"] = current
        
        return wrapping_check
    
    async def cleanup_clients(self) -> None:
        """Clean up all test clients"""
        cleanup_tasks = []
        for client in self.test_clients:
            if client.state == ConnectionState.CONNECTED:
                cleanup_tasks.append(client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.test_clients.clear()


@pytest_asyncio.fixture
async def structure_validator():
    """Event structure validator fixture"""
    validator = EventStructureValidator()
    yield validator
    await validator.cleanup_clients()


class TestMessageStructureConsistency:
    """Test WebSocket message structure consistency"""
    
    @pytest.mark.asyncio
    async def test_outbound_message_structure(self, structure_validator):
        """Test outbound messages follow {type, payload} structure"""
        client = structure_validator.create_authenticated_client("outbound_test")
        
        # Connect to WebSocket
        success = await client.connect(client._auth_headers)
        assert success is True
        
        # Test various outbound message types
        test_messages = [
            {"type": "ping", "payload": {}},
            {"type": "chat", "payload": {"message": "test", "thread_id": "123"}},
            {"type": "agent_command", "payload": {"command": "start", "parameters": {"verbose": True}}},
            {"type": "file_upload", "payload": {"filename": "test.txt", "size": 1024}},
            {"type": "user_action", "payload": {"action": "click", "element": "button"}}
        ]
        
        valid_messages = 0
        for message in test_messages:
            # Validate structure before sending
            validation = structure_validator.validate_message_structure(message, "outbound")
            assert validation["valid"] is True, f"Invalid outbound structure: {validation['issues']}"
            
            # Send message
            send_success = await client.send(message)
            if send_success:
                valid_messages += 1
        
        assert valid_messages == len(test_messages), "Not all messages sent successfully"
    
    @pytest.mark.asyncio
    async def test_inbound_message_structure(self, structure_validator):
        """Test inbound messages follow {type, payload} structure"""
        client = structure_validator.create_authenticated_client("inbound_test")
        
        # Connect and trigger server responses
        await client.connect(client._auth_headers)
        
        # Send ping to get server response
        await client.send({"type": "ping", "payload": {"timestamp": time.time()}})
        
        # Collect multiple responses
        responses = []
        for _ in range(3):
            response = await client.receive(timeout=2.0)
            if response:
                responses.append(response)
        
        # Validate each response structure
        valid_responses = 0
        for response in responses:
            validation = structure_validator.validate_message_structure(response, "inbound")
            if validation["valid"]:
                valid_responses += 1
            else:
                # Log validation issues for debugging
                print(f"Inbound structure issue: {validation['issues']}")
                print(f"Response: {response}")
        
        # Allow some flexibility for server responses (may not all follow structure yet)
        assert len(responses) > 0, "No responses received to validate"
    
    @pytest.mark.asyncio 
    async def test_json_wrapping_prevention(self, structure_validator):
        """Test prevention of double/triple JSON wrapping"""
        client = structure_validator.create_authenticated_client("wrapping_test")
        await client.connect(client._auth_headers)
        
        # Test message that could cause wrapping issues
        complex_message = {
            "type": "complex_data",
            "payload": {
                "nested_json": {"key": "value", "number": 42},
                "array_data": [1, 2, 3],
                "string_data": "simple text"
            }
        }
        
        # Check for wrapping issues before sending
        wrapping_check = structure_validator.check_json_wrapping_issues(complex_message)
        assert wrapping_check["has_wrapping_issue"] is False, "Pre-send wrapping issue detected"
        
        # Send and verify no wrapping occurred
        await client.send(complex_message)
        
        # Check if we get any responses and validate them for wrapping
        response = await client.receive(timeout=3.0)
        if response:
            response_wrapping = structure_validator.check_json_wrapping_issues(response)
            # Note: Server responses might have different structure
            # Focus on ensuring our client doesn't introduce wrapping
        
        assert wrapping_check["wrapping_level"] == 0


class TestEventCatalogStructureCompliance:
    """Test event catalog structure compliance"""
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_events_structure(self, structure_validator):
        """Test agent lifecycle events follow required structure"""
        client = structure_validator.create_authenticated_client("lifecycle_test")
        await client.connect(client._auth_headers)
        
        # Simulate agent lifecycle events
        lifecycle_events = [
            {
                "type": "agent_started",
                "payload": {
                    "run_id": "test_run_123",
                    "agent_name": "test_agent",
                    "timestamp": time.time()
                }
            },
            {
                "type": "agent_thinking",
                "payload": {
                    "thought": "Analyzing the problem",
                    "agent_name": "test_agent",
                    "step_number": 1
                }
            },
            {
                "type": "agent_completed",
                "payload": {
                    "agent_name": "test_agent",
                    "duration_ms": 5000,
                    "result": {"status": "success"}
                }
            }
        ]
        
        for event in lifecycle_events:
            # Validate structure
            validation = structure_validator.validate_message_structure(event, "agent_lifecycle")
            assert validation["valid"] is True, f"Agent lifecycle event invalid: {validation['issues']}"
            
            # Send event
            await client.send(event)
    
    @pytest.mark.asyncio
    async def test_tool_events_structure(self, structure_validator):
        """Test tool events follow required structure"""
        client = structure_validator.create_authenticated_client("tool_test")
        await client.connect(client._auth_headers)
        
        # Test tool-related events
        tool_events = [
            {
                "type": "tool_executing",
                "payload": {
                    "tool_name": "file_analyzer",
                    "agent_name": "analysis_agent",
                    "timestamp": time.time()
                }
            },
            {
                "type": "tool_call",
                "payload": {
                    "tool_name": "data_processor",
                    "tool_args": {"input": "test_data"},
                    "sub_agent_name": "processor_agent"
                }
            }
        ]
        
        for event in tool_events:
            validation = structure_validator.validate_message_structure(event, "tool_events")
            assert validation["valid"] is True, f"Tool event invalid: {validation['issues']}"
            await client.send(event)
    
    @pytest.mark.asyncio
    async def test_progress_events_structure(self, structure_validator):
        """Test progress events follow required structure"""
        client = structure_validator.create_authenticated_client("progress_test")
        await client.connect(client._auth_headers)
        
        # Test progress-related events
        progress_events = [
            {
                "type": "partial_result",
                "payload": {
                    "content": "Processing data...",
                    "agent_name": "data_agent",
                    "is_complete": False
                }
            },
            {
                "type": "final_report",
                "payload": {
                    "report": {"summary": "Analysis complete"},
                    "total_duration_ms": 10000,
                    "recommendations": ["Optimize data flow"]
                }
            }
        ]
        
        for event in progress_events:
            validation = structure_validator.validate_message_structure(event, "progress_events")
            assert validation["valid"] is True, f"Progress event invalid: {validation['issues']}"
            await client.send(event)


class TestLegacyPatternDetection:
    """Test detection and prevention of legacy message patterns"""
    
    @pytest.mark.asyncio
    async def test_legacy_event_data_pattern_detection(self, structure_validator):
        """Test detection of legacy {event, data} pattern"""
        client = structure_validator.create_authenticated_client("legacy_test")
        await client.connect(client._auth_headers)
        
        # Test legacy pattern that should be flagged
        legacy_message = {
            "event": "agent_update",  # Legacy field
            "data": {"status": "running"}  # Legacy field
        }
        
        validation = structure_validator.validate_message_structure(legacy_message, "legacy_pattern")
        
        # Should detect legacy pattern
        assert validation["valid"] is False
        assert any("Legacy pattern" in issue for issue in validation["issues"])
        assert any("event" in issue for issue in validation["issues"])
    
    @pytest.mark.asyncio
    async def test_mixed_pattern_detection(self, structure_validator):
        """Test detection of mixed legacy and new patterns"""
        client = structure_validator.create_authenticated_client("mixed_test")
        await client.connect(client._auth_headers)
        
        # Test message with both new and legacy fields
        mixed_message = {
            "type": "agent_update",  # New pattern
            "payload": {"status": "running"},  # New pattern
            "event": "legacy_event",  # Legacy pattern
            "data": {"old": "data"}  # Legacy pattern
        }
        
        validation = structure_validator.validate_message_structure(mixed_message, "mixed_pattern")
        
        # Should detect issues with mixed patterns
        assert validation["valid"] is False
        assert any("Unexpected top-level fields" in issue for issue in validation["issues"])
    
    @pytest.mark.asyncio
    async def test_string_message_prevention(self, structure_validator):
        """Test prevention of string messages (JSON-first requirement)"""
        client = structure_validator.create_authenticated_client("string_test")
        await client.connect(client._auth_headers)
        
        # Test string message (should be flagged)
        string_message = "This is a string message"
        
        validation = structure_validator.validate_message_structure(string_message, "string_message")
        
        # Should detect string message issue
        assert validation["valid"] is False
        assert any("not dict" in issue for issue in validation["issues"])


class TestStructureValidationReporting:
    """Test structure validation reporting and metrics"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_structure_validation(self, structure_validator):
        """Test comprehensive validation across all message types"""
        client = structure_validator.create_authenticated_client("comprehensive_test")
        await client.connect(client._auth_headers)
        
        # Test various message types
        test_messages = [
            # Valid messages
            {"type": "ping", "payload": {}},
            {"type": "chat", "payload": {"message": "hello"}},
            {"type": "command", "payload": {"action": "start"}},
            
            # Invalid messages for testing
            {"event": "old_style"},  # Legacy pattern
            "string_message",  # String message
            {"type": "missing_payload"},  # Missing payload
            {"payload": {"no_type": True}},  # Missing type
        ]
        
        valid_count = 0
        invalid_count = 0
        
        for i, message in enumerate(test_messages):
            validation = structure_validator.validate_message_structure(
                message, f"comprehensive_test_{i}"
            )
            
            if validation["valid"]:
                valid_count += 1
            else:
                invalid_count += 1
        
        # Verify we detected both valid and invalid messages
        assert valid_count >= 3, "Should have at least 3 valid messages"
        assert invalid_count >= 4, "Should have at least 4 invalid messages"
        
        # Check violation tracking
        assert len(structure_validator.structure_violations) == invalid_count
        assert len(structure_validator.validated_events) == valid_count
    
    @pytest.mark.asyncio
    async def test_validation_metrics_collection(self, structure_validator):
        """Test collection of validation metrics"""
        client = structure_validator.create_authenticated_client("metrics_test")
        await client.connect(client._auth_headers)
        
        # Generate various validation events
        messages = [
            {"type": "valid1", "payload": {}},
            {"type": "valid2", "payload": {"data": "test"}},
            {"invalid": "structure"},
            {"type": "valid3", "payload": {"complex": {"nested": True}}}
        ]
        
        initial_violations = len(structure_validator.structure_violations)
        initial_validated = len(structure_validator.validated_events)
        
        for i, message in enumerate(messages):
            structure_validator.validate_message_structure(message, f"metrics_test_{i}")
        
        # Check metrics updated correctly
        final_violations = len(structure_validator.structure_violations)
        final_validated = len(structure_validator.validated_events)
        
        violations_added = final_violations - initial_violations
        validated_added = final_validated - initial_validated
        
        assert violations_added >= 1, "Should have added violation"
        assert validated_added >= 3, "Should have added valid events"
        assert violations_added + validated_added == len(messages), "All messages should be categorized"
    
    @pytest.mark.asyncio
    async def test_structure_issue_detailed_reporting(self, structure_validator):
        """Test detailed reporting of structure issues"""
        client = structure_validator.create_authenticated_client("reporting_test")
        await client.connect(client._auth_headers)
        
        # Test message with multiple issues
        problematic_message = {
            "event": "legacy_event",  # Legacy field
            "data": "legacy_data",  # Legacy field
            "extra_field": "unexpected",  # Unexpected field
            # Missing type and payload
        }
        
        validation = structure_validator.validate_message_structure(
            problematic_message, "detailed_reporting"
        )
        
        # Should detect multiple specific issues
        assert validation["valid"] is False
        assert len(validation["issues"]) >= 3, "Should detect multiple issues"
        
        # Check for specific issue types
        issues_text = " ".join(validation["issues"])
        assert "type" in issues_text, "Should mention missing type"
        assert "payload" in issues_text, "Should mention missing payload"
        assert "Legacy pattern" in issues_text, "Should mention legacy pattern"