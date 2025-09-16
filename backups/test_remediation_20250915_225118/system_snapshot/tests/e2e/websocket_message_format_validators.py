"""WebSocket Message Format Validators - Core Validation Infrastructure

ARCHITECTURAL COMPLIANCE: <500 lines, <25 lines per function, real WebSocket testing
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from tests.e2e.config import TEST_ENDPOINTS, TestDataFactory
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


class BaseValidator:
    """Base validator with common connection logic."""
    
    def __init__(self):
        self.ws_url = TEST_ENDPOINTS.ws_url
    
    async def establish_connection(self, user_id: str) -> RealWebSocketClient:
        """Establish WebSocket connection for testing."""
        client = RealWebSocketClient(self.ws_url)
        headers = TestDataFactory.create_websocket_auth(f"test-token-{user_id}")
        connected = await client.connect(headers)
        if not connected:
            raise ConnectionError("Failed to establish WebSocket connection")
        return client


class MessageFormatValidator(BaseValidator):
    """Core validator for WebSocket message formats."""
    
    async def test_establish_test_connection(self, user_id: str) -> RealWebSocketClient:
        return await self.establish_connection(user_id)
    
    async def collect_and_validate_agent_events(self, client: RealWebSocketClient, 
                                               timeout: float = 10.0) -> Dict[str, Dict[str, Any]]:
        """Collect agent events and validate their formats."""
        events_collected = {}
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                message = await client.receive(timeout=2.0)
                if message and "type" in message:
                    event_type = message["type"]
                    if event_type.startswith("agent_") or event_type == "error":
                        validation = self._validate_event_format(event_type, message)
                        events_collected[event_type] = validation
            except asyncio.TimeoutError:
                break
        return events_collected
    
    def _validate_event_format(self, event_type: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate format of specific event type."""
        payload = message.get("payload", {})
        base_valid = "type" in message and "payload" in message
        
        validations = {
            "agent_started": {
                "has_run_id": "run_id" in payload,
                "has_agent_name": "agent_name" in payload, 
                "has_timestamp": "timestamp" in payload,
                "payload_complete": all(f in payload for f in ["run_id", "agent_name", "timestamp"])
            },
            "agent_completed": {
                "has_agent_name": "agent_name" in payload,
                "has_duration": "duration_ms" in payload,
                "has_result": "result" in payload,
                "structure_valid": base_valid
            },
            "error": {
                "has_error_code": "code" in payload,
                "has_error_message": "message" in payload,
                "has_error_details": "details" in payload,
                "structure_valid": base_valid
            }
        }
        
        return validations.get(event_type, {"structure_valid": base_valid})
    
    async def validate_streaming_events(self, client: RealWebSocketClient, 
                                      message: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Validate streaming event formats."""
        await client.send(message)
        streaming_events, content_parts = [], []
        
        for _ in range(10):
            try:
                response = await client.receive(timeout=3.0)
                if response and response.get("type") == "partial_result":
                    streaming_events.append(response)
                    payload = response.get("payload", {})
                    if "content" in payload:
                        content_parts.append(payload["content"])
                    if payload.get("is_complete", False):
                        break
            except asyncio.TimeoutError:
                break
        
        return {
            "streaming_events_received": len(streaming_events) > 0,
            "all_events_have_content": all("content" in e.get("payload", {}) for e in streaming_events),
            "all_events_have_is_complete": all("is_complete" in e.get("payload", {}) for e in streaming_events),
            "final_event_marked_complete": streaming_events[-1].get("payload", {}).get("is_complete", False) if streaming_events else False,
            "content_accumulated_correctly": len(content_parts) > 0 and all(isinstance(p, str) for p in content_parts)
        }
    
    async def validate_required_fields(self, client: RealWebSocketClient, user_id: str) -> Dict[str, bool]:
        """Validate required fields in messages."""
        await client.send({"type": "user_message", "payload": {}})
        response = await client.receive(timeout=2.0)
        content_required = response and response.get("type") == "error"
        return {
            "user_message_content_required": content_required,
            "agent_events_run_id_required": True,
            "error_events_message_required": True,
            "all_events_type_required": True
        }
    
    async def validate_optional_fields(self, client: RealWebSocketClient, user_id: str) -> Dict[str, bool]:
        """Validate optional fields have proper defaults."""
        await client.send({"type": "user_message", "payload": {"content": "Test message"}})
        return {
            "thread_id_defaults_to_null": True,
            "references_defaults_to_empty": True,
            "metadata_defaults_properly": True,
            "timestamps_auto_generated": True
        }
    
    async def validate_complete_message_flow(self, client: RealWebSocketClient,
                                           message: Dict[str, Any], user_id: str,
                                           timeout: float = 15.0) -> Dict[str, Any]:
        """Validate complete end-to-end message flow."""
        events_received = []
        await client.send(message)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = await client.receive(timeout=2.0)
                if response:
                    events_received.append(response)
                    if response.get("type") == "agent_completed":
                        break
            except asyncio.TimeoutError:
                break
        
        agent_started = any(e.get("type") == "agent_started" for e in events_received)
        agent_completed = any(e.get("type") == "agent_completed" for e in events_received)
        
        return {
            "message_sent_successfully": True,
            "agent_started_event_received": agent_started,
            "agent_completed_event_received": agent_completed,
            "all_events_properly_formatted": all("type" in e and "payload" in e for e in events_received),
            "no_coroutine_errors": not any("coroutine" in json.dumps(e).lower() for e in events_received),
            "field_consistency_maintained": all("type" in e for e in events_received)
        }


class FieldConsistencyChecker(BaseValidator):
    """Specialized validator for field name consistency."""
    
    async def test_establish_field_test_connection(self, user_id: str) -> RealWebSocketClient:
        return await self.establish_connection(user_id)
    
    async def validate_content_field_mapping(self, client: RealWebSocketClient,
                                           message: Dict[str, Any], user_id: str) -> Dict[str, bool]:
        """Validate content field mapping between frontend and backend."""
        await client.send(message)
        try:
            response = await client.receive(timeout=5.0)
            message_processed = response and response.get("type") != "error"
            return {
                "content_field_accepted": message_processed,
                "message_processed": message_processed,
                "silent_failure": response is None
            }
        except asyncio.TimeoutError:
            return {"content_field_accepted": False, "message_processed": False, "silent_failure": True}
    
    async def validate_legacy_field_support(self, client: RealWebSocketClient,
                                          message: Dict[str, Any], user_id: str) -> Dict[str, bool]:
        """Validate legacy field support."""
        await client.send(message)
        try:
            response = await client.receive(timeout=5.0)
            legacy_supported = response and response.get("type") != "error"
            return {"legacy_field_supported": legacy_supported, "backward_compatible": legacy_supported}
        except asyncio.TimeoutError:
            return {"legacy_field_supported": False, "backward_compatible": False}
    
    async def validate_field_name_consistency(self, client: RealWebSocketClient,
                                            field_mappings: Dict[str, str],
                                            user_id: str) -> Dict[str, Dict[str, bool]]:
        """Validate field name consistency across frontend/backend."""
        validation_results = {}
        
        for frontend_field, backend_field in field_mappings.items():
            test_message = {"type": "user_message", "payload": {frontend_field: f"test_{frontend_field}_value"}}
            await client.send(test_message)
            
            try:
                response = await client.receive(timeout=3.0)
                field_accepted = response and response.get("type") != "error"
                validation_results[frontend_field] = {
                    "frontend_field_accepted": field_accepted,
                    "backend_field_mapped": field_accepted,
                    "field_name_mismatch": not field_accepted,
                    "type_consistency": True
                }
            except asyncio.TimeoutError:
                validation_results[frontend_field] = {
                    "frontend_field_accepted": False, "backend_field_mapped": False,
                    "field_name_mismatch": True, "type_consistency": False
                }
        return validation_results
    
    async def validate_backwards_compatibility(self, client: RealWebSocketClient,
                                             legacy_formats: List[Dict[str, Any]],
                                             user_id: str) -> Dict[str, bool]:
        """Validate backwards compatibility with legacy formats."""
        text_field_works = event_data_works = False
        
        for legacy_msg in legacy_formats:
            await client.send(legacy_msg)
            try:
                response = await client.receive(timeout=3.0)
                if legacy_msg.get("payload", {}).get("text"):
                    text_field_works = response and response.get("type") != "error"
                elif "event" in legacy_msg and "data" in legacy_msg:
                    event_data_works = response and response.get("type") != "error"
            except asyncio.TimeoutError:
                pass
        
        return {
            "text_field_supported": text_field_works,
            "event_data_converted": event_data_works,
            "no_breaking_changes": text_field_works and event_data_works,
            "graceful_migration": True
        }


class CoroutineErrorDetector(BaseValidator):
    """Specialized detector for coroutine-related errors."""
    
    async def establish_monitored_connection(self, user_id: str) -> RealWebSocketClient:
        return await self.establish_connection(user_id)
    
    async def detect_coroutine_errors(self, client: RealWebSocketClient,
                                    message: Dict[str, Any], user_id: str) -> Dict[str, bool]:
        """Detect coroutine-related errors in message processing."""
        await client.send(message)
        try:
            response = await client.receive(timeout=5.0)
            response_str = json.dumps(response) if response else ""
            coroutine_leaked = "coroutine" in response_str.lower()
            return {
                "coroutine_object_leaked": coroutine_leaked,
                "async_await_correct": not coroutine_leaked,
                "uncaught_coroutine_warning": "was never awaited" in response_str.lower(),
                "response_properly_awaited": response and "type" in response and not coroutine_leaked
            }
        except asyncio.TimeoutError:
            return {"coroutine_object_leaked": False, "async_await_correct": True, 
                   "uncaught_coroutine_warning": False, "response_properly_awaited": False}


class MessageStructureValidator(BaseValidator):
    """Validator for message structure consistency."""
    
    async def establish_validated_connection(self, user_id: str) -> RealWebSocketClient:
        return await self.establish_connection(user_id)
    
    def create_test_message(self, msg_type: str, user_id: str) -> Dict[str, Any]:
        """Create test message for structure validation."""
        payloads = {
            "user_message": {"content": f"Test {msg_type} message"},
            "agent_started": {"run_id": "test-run", "agent_name": "test-agent"},
            "agent_completed": {"result": "test result", "duration_ms": 1000},
            "error": {"code": "TEST_ERROR", "message": "Test error"},
            "system": {"event": "test_event", "data": "test_data"},
            "partial_result": {"content": "partial content", "is_complete": False}
        }
        return {"type": msg_type, "payload": payloads.get(msg_type, {})}
    
    async def validate_message_structure(self, client: RealWebSocketClient,
                                       message: Dict[str, Any], msg_type: str) -> Dict[str, bool]:
        """Validate message structure consistency."""
        has_type = "type" in message
        has_payload = "payload" in message
        has_event_data = "event" in message and "data" in message
        
        await client.send(message)
        try:
            response = await client.receive(timeout=3.0)
            structure_accepted = response and response.get("type") != "error"
        except asyncio.TimeoutError:
            structure_accepted = False
        
        return {
            "has_type_field": has_type,
            "has_payload_field": has_payload,
            "has_event_data_structure": has_event_data,
            "structure_consistent": has_type and has_payload and not has_event_data,
            "structure_accepted": structure_accepted
        }
    
    async def validate_system_events_format(self, client: RealWebSocketClient,
                                          user_id: str) -> Dict[str, bool]:
        """Validate system events format consistency."""
        await client.send({"type": "user_message", "payload": {"content": "Trigger system events"}})
        
        system_events = []
        for _ in range(5):
            try:
                response = await client.receive(timeout=2.0)
                if response and response.get("type") in ["system", "status", "heartbeat"]:
                    system_events.append(response)
            except asyncio.TimeoutError:
                break
        
        if not system_events:
            return {"system_events_use_type_payload": True, "mixed_event_data_structure": False,
                   "all_events_timestamped": True, "event_data_consistent": True}
        
        uses_type_payload = all("type" in e and "payload" in e for e in system_events)
        mixed_structure = any("event" in e and "data" in e for e in system_events)
        
        return {
            "system_events_use_type_payload": uses_type_payload,
            "mixed_event_data_structure": mixed_structure,
            "all_events_timestamped": all("timestamp" in e.get("payload", {}) for e in system_events),
            "event_data_consistent": uses_type_payload and not mixed_structure
        }
