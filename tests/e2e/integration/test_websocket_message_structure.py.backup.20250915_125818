"""WebSocket Message Structure Consistency Test - Test #9 P1 CRITICAL

Test #9: WebSocket Message Structure Consistency Test [P1 - COMPATIBILITY]
Issue: Inconsistent message formats {type, payload} vs {event, data}
Impact: Frontend randomly fails to parse messages
Test: ALL WebSocket messages use consistent structure
Spec: websocket_communication.xml lines 210-219

Business Value Justification (BVJ):
1. Segment: ALL customer tiers (Free, Early, Mid, Enterprise) 
2. Business Goal: Ensure consistent frontend-backend communication
3. Value Impact: Prevents random message parsing failures affecting all UX
4. Revenue Impact: Protects conversion/retention by ensuring reliable chat experience

CRITICAL VALIDATIONS:
- ALL messages use {type, payload} structure consistently
- NO messages use deprecated {event, data} structure  
- Message parsing doesn't fail on any message type
- Frontend can parse all message types without errors
- All server-to-client messages follow the standard
- All client-to-server messages follow the standard

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (focused on message structure validation)
- Function size: <25 lines each  
- Real WebSocket connections, deterministic under 10 seconds
- Tests actual message structure between frontend and backend
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set, Union
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


@pytest.mark.asyncio
@pytest.mark.e2e
class TestWebSocketMessageStructure:
    """Test #9: WebSocket Message Structure Consistency - P1 CRITICAL"""
    
    @pytest.mark.e2e
    async def test_all_messages_use_type_payload_structure(self):
        """Test that ALL WebSocket messages use {type, payload} structure."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Send various message types and validate structure
            test_messages = [
                {"type": "user_message", "payload": {"content": "Test message", "thread_id": None}},
                {"type": "start_agent", "payload": {"query": "Test query", "user_id": user_id}},
                {"type": "create_thread", "payload": {"name": "Test thread"}},
                {"type": "ping", "payload": {"timestamp": time.time()}},
                {"type": "get_thread_history", "payload": {"limit": 10}}
            ]
            
            # Send messages and collect all responses
            collected_messages = []
            for test_msg in test_messages:
                await client.send(test_msg)
                
                # Collect responses for 2 seconds
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    try:
                        response = await client.receive(timeout=0.5)
                        if response:
                            collected_messages.append(response)
                    except asyncio.TimeoutError:
                        break
            
            # Validate ALL messages use {type, payload} structure
            assert len(collected_messages) > 0, "No messages received from server"
            
            for i, message in enumerate(collected_messages):
                structure_validation = self._validate_message_structure(message)
                assert structure_validation["has_type_field"], f"Message {i} missing 'type' field: {message}"
                assert structure_validation["has_payload_field"], f"Message {i} missing 'payload' field: {message}"
                assert not structure_validation["has_event_data_structure"], f"Message {i} uses deprecated {{event, data}}: {message}"
                assert structure_validation["is_consistent"], f"Message {i} structure inconsistent: {message}"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_no_event_data_structure_used(self):
        """Test that NO messages use deprecated {event, data} structure."""
        user_id = TEST_USERS["early"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Test various scenarios that could trigger different message types
            test_scenarios = [
                {"type": "user_message", "payload": {"content": "Trigger agent response", "thread_id": None}},
                {"type": "start_agent", "payload": {"query": "Start agent", "user_id": user_id}},
                {"type": "list_threads", "payload": {}},
                {"type": "ping", "payload": {}}
            ]
            
            collected_responses = []
            for scenario in test_scenarios:
                await client.send(scenario)
                
                # Collect responses for each scenario
                responses = await self._collect_responses(client, timeout=2.0)
                collected_responses.extend(responses)
            
            # Validate NO {event, data} structures found
            event_data_violations = []
            for response in collected_responses:
                if self._has_event_data_structure(response):
                    event_data_violations.append(response)
            
            assert len(event_data_violations) == 0, f"Found {len(event_data_violations)} messages using deprecated {{event, data}} structure: {event_data_violations}"
            
            # Validate all use proper structure
            for response in collected_responses:
                assert "type" in response, f"Message missing 'type' field: {response}"
                assert "payload" in response, f"Message missing 'payload' field: {response}"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_message_parsing_never_fails(self):
        """Test that message parsing doesn't fail on any message type."""
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Test message types that could have parsing issues
            complex_messages = [
                {
                    "type": "user_message", 
                    "payload": {
                        "content": "Complex message with special chars: {}[]()\"'\\", 
                        "thread_id": None,
                        "metadata": {"complex": {"nested": "data"}}
                    }
                },
                {
                    "type": "start_agent",
                    "payload": {
                        "query": "Query with unicode: [U+1F680] [U+6D4B][U+8BD5] [U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629]",
                        "user_id": user_id,
                        "context": {"numbers": [1, 2, 3], "boolean": True, "null_value": None}
                    }
                }
            ]
            
            parsing_results = []
            for test_msg in complex_messages:
                try:
                    # Send complex message
                    await client.send(test_msg)
                    
                    # Try to parse responses
                    responses = await self._collect_responses(client, timeout=3.0)
                    
                    # Validate each response can be parsed
                    for response in responses:
                        parse_result = self._validate_message_parsing(response)
                        parsing_results.append(parse_result)
                        
                except Exception as parse_error:
                    parsing_results.append({
                        "success": False,
                        "error": str(parse_error),
                        "message": test_msg
                    })
            
            # Validate no parsing failures
            failed_parsing = [result for result in parsing_results if not result.get("success", True)]
            assert len(failed_parsing) == 0, f"Message parsing failed: {failed_parsing}"
            
            # Validate all messages properly structured
            for result in parsing_results:
                if result.get("success", True):
                    assert result.get("has_type"), "Parsed message missing 'type'"
                    assert result.get("has_payload"), "Parsed message missing 'payload'"
                    assert result.get("json_valid"), "Message not valid JSON"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_frontend_can_parse_all_message_types(self):
        """Test that frontend can parse all message types without errors."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Trigger various server message types
            trigger_messages = [
                {"type": "user_message", "payload": {"content": "Trigger agent_started", "thread_id": None}},
                {"type": "start_agent", "payload": {"query": "Test agent", "user_id": user_id}},
                {"type": "create_thread", "payload": {"name": "Test thread"}},
                {"type": "get_thread_history", "payload": {"limit": 5}},
                {"type": "list_threads", "payload": {}}
            ]
            
            # Expected server message types that should be parseable by frontend
            expected_server_types = {
                "agent_started", "agent_completed", "agent_update", "agent_error",
                "partial_result", "final_report", "error", "connection_established",
                "thread_created", "thread_history", "threads_list"
            }
            
            received_message_types = set()
            frontend_parsing_results = []
            
            for trigger_msg in trigger_messages:
                await client.send(trigger_msg)
                
                responses = await self._collect_responses(client, timeout=3.0)
                
                for response in responses:
                    msg_type = response.get("type")
                    if msg_type:
                        received_message_types.add(msg_type)
                        
                        # Simulate frontend parsing
                        parse_result = self._simulate_frontend_parsing(response)
                        frontend_parsing_results.append(parse_result)
            
            # Validate frontend can parse all received message types
            failed_frontend_parsing = [
                result for result in frontend_parsing_results 
                if not result.get("frontend_parseable", False)
            ]
            
            assert len(failed_frontend_parsing) == 0, f"Frontend parsing failed for: {failed_frontend_parsing}"
            
            # Validate structure consistency across all received types
            for result in frontend_parsing_results:
                assert result.get("has_type_field"), "Message missing 'type' field for frontend"
                assert result.get("has_payload_field"), "Message missing 'payload' field for frontend"
                assert result.get("structure_consistent"), "Message structure inconsistent for frontend"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_all_server_messages_follow_standard(self):
        """Test that all server-to-client messages follow {type, payload} standard."""
        user_id = TEST_USERS["free"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Send message to trigger comprehensive server responses
            comprehensive_trigger = {
                "type": "user_message",
                "payload": {
                    "content": "Please provide a comprehensive response that triggers all server message types",
                    "thread_id": None
                }
            }
            
            await client.send(comprehensive_trigger)
            
            # Collect all server responses
            server_messages = await self._collect_responses(client, timeout=5.0)
            
            assert len(server_messages) > 0, "No server messages received"
            
            # Validate each server message follows standard
            standard_violations = []
            for server_msg in server_messages:
                validation = self._validate_server_message_standard(server_msg)
                if not validation["follows_standard"]:
                    standard_violations.append({
                        "message": server_msg,
                        "violations": validation["violations"]
                    })
            
            assert len(standard_violations) == 0, f"Server messages violate standard: {standard_violations}"
            
            # Validate consistency across all server messages
            message_types_seen = set()
            for server_msg in server_messages:
                msg_type = server_msg.get("type")
                if msg_type:
                    message_types_seen.add(msg_type)
                    
                    # Ensure consistent structure for same message type
                    structure = self._get_message_structure(server_msg)
                    assert structure["has_type"], f"Server message type '{msg_type}' missing 'type' field"
                    assert structure["has_payload"], f"Server message type '{msg_type}' missing 'payload' field"
                    assert not structure["has_event_data"], f"Server message type '{msg_type}' uses deprecated {{event, data}}"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    @pytest.mark.e2e
    async def test_client_server_message_structure_compatibility(self):
        """Test full client-server message structure compatibility."""
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await self._establish_connection(user_id)
            
            # Test bidirectional communication with structure validation
            client_messages = [
                {"type": "user_message", "payload": {"content": "Test bidirectional communication", "thread_id": None}},
                {"type": "ping", "payload": {"timestamp": time.time()}},
                {"type": "create_thread", "payload": {"name": "Compatibility test"}}
            ]
            
            compatibility_results = []
            
            for client_msg in client_messages:
                # Validate client message structure before sending
                client_validation = self._validate_message_structure(client_msg)
                assert client_validation["is_consistent"], f"Client message invalid: {client_msg}"
                
                # Send and receive responses
                await client.send(client_msg)
                server_responses = await self._collect_responses(client, timeout=2.0)
                
                # Validate server response structures
                for server_response in server_responses:
                    server_validation = self._validate_message_structure(server_response)
                    compatibility_results.append({
                        "client_message": client_msg,
                        "server_response": server_response,
                        "client_valid": client_validation["is_consistent"],
                        "server_valid": server_validation["is_consistent"],
                        "structures_compatible": (
                            client_validation["is_consistent"] and 
                            server_validation["is_consistent"]
                        )
                    })
            
            # Validate all communications are structurally compatible
            incompatible = [
                result for result in compatibility_results 
                if not result["structures_compatible"]
            ]
            
            assert len(incompatible) == 0, f"Structure incompatibilities found: {incompatible}"
            
            # Validate consistency across the conversation
            all_messages = [result["client_message"] for result in compatibility_results]
            all_messages.extend([result["server_response"] for result in compatibility_results])
            
            structures = [self._get_message_structure(msg) for msg in all_messages]
            consistent_structures = all(
                struct["has_type"] and struct["has_payload"] and not struct["has_event_data"]
                for struct in structures
            )
            
            assert consistent_structures, "Message structures not consistent across conversation"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise

    # Helper methods

    async def _establish_connection(self, user_id: str) -> RealWebSocketClient:
        """Establish WebSocket connection for testing."""
        from tests.e2e.config import TestDataFactory
        
        client = RealWebSocketClient(TEST_ENDPOINTS.ws_url)
        headers = TestDataFactory.create_websocket_auth(f"test-token-{user_id}")
        connected = await client.connect(headers)
        if not connected:
            raise ConnectionError("Failed to establish WebSocket connection")
        return client

    async def _collect_responses(self, client: RealWebSocketClient, timeout: float) -> List[Dict[str, Any]]:
        """Collect WebSocket responses within timeout."""
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await client.receive(timeout=0.5)
                if response:
                    responses.append(response)
            except asyncio.TimeoutError:
                break
        
        return responses

    def _validate_message_structure(self, message: Dict[str, Any]) -> Dict[str, bool]:
        """Validate message follows {type, payload} structure."""
        return {
            "has_type_field": "type" in message,
            "has_payload_field": "payload" in message,
            "has_event_data_structure": "event" in message and "data" in message,
            "is_consistent": (
                "type" in message and 
                "payload" in message and 
                not ("event" in message and "data" in message)
            )
        }

    def _has_event_data_structure(self, message: Dict[str, Any]) -> bool:
        """Check if message uses deprecated {event, data} structure."""
        return "event" in message and "data" in message

    def _validate_message_parsing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate message can be properly parsed."""
        try:
            # Test JSON serialization/deserialization
            json_str = json.dumps(message)
            parsed = json.loads(json_str)
            
            return {
                "success": True,
                "has_type": "type" in parsed,
                "has_payload": "payload" in parsed,
                "json_valid": True,
                "parseable": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "json_valid": False,
                "parseable": False
            }

    def _simulate_frontend_parsing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate frontend TypeScript parsing of message."""
        try:
            # Simulate TypeScript interface validation
            msg_type = message.get("type")
            payload = message.get("payload")
            
            # TypeScript would expect these fields
            typescript_compatible = self._check_typescript_compatibility(msg_type, payload)
            structure_consistent = self._check_structure_consistency(message)
            
            return {
                "frontend_parseable": typescript_compatible,
                "has_type_field": "type" in message,
                "has_payload_field": "payload" in message,
                "structure_consistent": structure_consistent,
                "typescript_compatible": typescript_compatible
            }
        except Exception as e:
            return {
                "frontend_parseable": False,
                "error": str(e),
                "structure_consistent": False
            }

    def _check_typescript_compatibility(self, msg_type: Any, payload: Any) -> bool:
        """Check TypeScript compatibility."""
        return isinstance(msg_type, str) and payload is not None and isinstance(payload, dict)

    def _check_structure_consistency(self, message: Dict[str, Any]) -> bool:
        """Check message structure consistency."""
        return (
            "type" in message and 
            "payload" in message and
            not ("event" in message and "data" in message)
        )

    def _validate_server_message_standard(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate server message follows the standard."""
        violations = []
        
        if "type" not in message:
            violations.append("Missing 'type' field")
        
        if "payload" not in message:
            violations.append("Missing 'payload' field")
        
        if "event" in message and "data" in message:
            violations.append("Uses deprecated {event, data} structure")
        
        return {
            "follows_standard": len(violations) == 0,
            "violations": violations
        }

    def _get_message_structure(self, message: Dict[str, Any]) -> Dict[str, bool]:
        """Get message structure information."""
        return {
            "has_type": "type" in message,
            "has_payload": "payload" in message,
            "has_event_data": "event" in message and "data" in message
        }
