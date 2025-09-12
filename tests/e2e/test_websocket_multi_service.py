"""WebSocket Multi-Service Communication Tests.

Tests cross-service WebSocket message routing per SPEC/independent_services.xml
and SPEC/websockets.xml requirements:
- Main Backend (/app) - primary application service
- Auth Service (/auth_service) - authentication service  
- Frontend (/frontend) - user interface service

Business Value: Ensures reliable communication between microservices
maintaining service independence while enabling coordinated functionality.

BVJ: Enterprise - Platform Stability - Multi-service WebSocket coordination
prevents service communication failures that could impact user experience.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.config import UnifiedTestConfig


@pytest.mark.e2e
class TestWebSocketMultiService:
    """Test suite for WebSocket multi-service communication."""
    
    @pytest.fixture
    async def backend_client(self):
        """Get authenticated backend client."""
        client = BackendTestClient()
        await client.authenticate()
        try:
            yield client
        finally:
            await client.close()
    
    @pytest.fixture
    async def websocket_client(self, backend_client):
        """Get authenticated WebSocket client."""
        token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        await ws_client.connect(token)
        try:
            yield ws_client
        finally:
            await ws_client.disconnect()
    
    @pytest.fixture
    async def auth_service_client(self):
        """Get dedicated auth service client."""
        config = UnifiedTestConfig()
        auth_client = BackendTestClient(base_url=config.auth_service_url)
        try:
            yield auth_client
        finally:
            await auth_client.close()
    
    @pytest.mark.e2e
    async def test_cross_service_authentication_flow(self, websocket_client, auth_service_client):
        """Test WebSocket authentication coordinates across services."""
        # Verify auth service is accessible
        auth_health = await auth_service_client.get("/health")
        if auth_health.status_code != 200:
            pytest.skip("Auth service not available for multi-service testing")
        
        # Trigger authentication-related WebSocket events
        await websocket_client.send_message({
            "type": "auth_status_request",
            "payload": {"request_id": "multi_service_test_001"}
        })
        
        # Look for authentication coordination events
        auth_events = []
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    # Look for auth-related events from different services
                    if any(auth_keyword in event_type.lower() for auth_keyword in ["auth", "token", "session"]):
                        auth_events.append(message)
                        
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate cross-service auth coordination
        if len(auth_events) > 0:
            for event in auth_events:
                payload = event.get("payload", {})
                
                # Should include service identification
                service_indicators = ["service_id", "service_name", "source_service"]
                has_service_indicator = any(indicator in payload for indicator in service_indicators)
                
                assert has_service_indicator or "service" in str(payload).lower(), (
                    f"Auth event missing service identification: {event}"
                )
                
                # Verify message structure compliance
                assert "type" in event, "Auth event missing type field"
                assert "payload" in event, "Auth event missing payload field"
    
    @pytest.mark.e2e
    async def test_service_independence_validation(self, websocket_client):
        """Test services maintain independence per SPEC/independent_services.xml."""
        # Trigger events that might involve multiple services
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Test service independence with agent execution"}
        })
        
        # Track service origins of events
        service_events = {}
        timeout = 15.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    # Try to identify service origin
                    service_origin = self._identify_service_origin(message)
                    
                    if service_origin not in service_events:
                        service_events[service_origin] = []
                    service_events[service_origin].append(message)
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate service independence principles
        for service, events in service_events.items():
            for event in events:
                payload = event.get("payload", {})
                
                # Should not contain references to internal modules of other services
                forbidden_imports = ["app.internal", "auth_service.internal", "frontend.internal"]
                event_str = str(event)
                
                for forbidden in forbidden_imports:
                    assert forbidden not in event_str, (
                        f"Service independence violation: {service} event references {forbidden}: {event}"
                    )
                
                # Should not expose service-internal implementation details
                internal_fields = ["_internal", "private_", "__internal__"]
                for field in internal_fields:
                    assert field not in str(payload), (
                        f"Service {service} exposing internal field {field} in WebSocket event"
                    )
    
    @pytest.mark.e2e
    async def test_message_routing_between_services(self, websocket_client):
        """Test messages are properly routed between services."""
        # Send messages that require multi-service coordination
        test_messages = [
            {
                "type": "user_message",
                "payload": {"content": "Agent task requiring auth verification"}
            },
            {
                "type": "service_health_check",
                "payload": {"services": ["main", "auth", "frontend"]}
            }
        ]
        
        routing_results = []
        
        for test_msg in test_messages:
            await websocket_client.send_message(test_msg)
            
            # Track message routing patterns
            received_events = []
            timeout = 8.0
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        websocket_client.receive_message(),
                        timeout=1.0
                    )
                    
                    if isinstance(message, str):
                        message = json.loads(message)
                    
                    if isinstance(message, dict):
                        received_events.append(message)
                        
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    break
            
            routing_results.append({
                "request": test_msg,
                "responses": received_events,
                "service_participation": self._analyze_service_participation(received_events)
            })
            
            # Brief pause between test messages
            await asyncio.sleep(1.0)
        
        # Validate routing effectiveness
        for result in routing_results:
            responses = result["responses"]
            assert len(responses) > 0, f"No responses for message: {result['request']}"
            
            # Should have proper message correlation
            request_type = result["request"]["type"]
            response_types = [r.get("type", "") for r in responses]
            
            # Responses should be related to request
            assert any(
                request_type.replace("_", "").lower() in response_type.replace("_", "").lower()
                or "response" in response_type.lower()
                or "result" in response_type.lower()
                for response_type in response_types
            ), f"No correlated responses for {request_type}: {response_types}"
    
    @pytest.mark.e2e
    async def test_service_failure_isolation(self, websocket_client):
        """Test WebSocket continues working when individual services have issues."""
        # Trigger comprehensive workflow
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Test service failure isolation with comprehensive workflow"}
        })
        
        # Monitor events and service health
        events_by_service = {}
        service_errors = []
        timeout = 20.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    service = self._identify_service_origin(message)
                    
                    if service not in events_by_service:
                        events_by_service[service] = []
                    events_by_service[service].append(message)
                    
                    # Check for service error indicators
                    if "error" in message.get("type", "").lower():
                        service_errors.append({
                            "service": service,
                            "error_event": message,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                        
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate failure isolation
        participating_services = set(events_by_service.keys())
        assert len(participating_services) >= 1, "No service participation detected"
        
        # Even with some service errors, core functionality should continue
        if service_errors:
            error_services = {error["service"] for error in service_errors}
            working_services = participating_services - error_services
            
            assert len(working_services) > 0, (
                f"All services failed: {error_services}. "
                f"Service isolation should prevent complete failure."
            )
            
            # Working services should continue providing events
            for service in working_services:
                service_events = events_by_service[service]
                recent_events = [
                    e for e in service_events 
                    if any(error["timestamp"] < asyncio.get_event_loop().time() - 5 
                          for error in service_errors)
                ]
                assert len(recent_events) > 0, (
                    f"Service {service} stopped working after other service failures"
                )
    
    @pytest.mark.e2e
    async def test_websocket_load_balancing_compatibility(self, websocket_client):
        """Test WebSocket works correctly with load balancing between services."""
        # Send multiple requests to test load balancing scenarios
        request_count = 5
        session_consistency_results = []
        
        for i in range(request_count):
            await websocket_client.send_message({
                "type": "user_message",
                "payload": {
                    "content": f"Load balancing test request {i+1}",
                    "session_marker": f"lb_test_{i+1}"
                }
            })
            
            # Track session consistency across requests
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            request_events = []
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        websocket_client.receive_message(),
                        timeout=1.0
                    )
                    
                    if isinstance(message, str):
                        message = json.loads(message)
                    
                    if isinstance(message, dict):
                        request_events.append(message)
                        
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    break
            
            session_consistency_results.append({
                "request_id": i + 1,
                "events": request_events,
                "service_origins": [self._identify_service_origin(e) for e in request_events]
            })
            
            await asyncio.sleep(0.5)  # Brief pause between requests
        
        # Validate load balancing compatibility
        all_service_origins = set()
        for result in session_consistency_results:
            all_service_origins.update(result["service_origins"])
        
        # Should maintain session consistency regardless of load balancing
        user_ids = set()
        session_ids = set()
        
        for result in session_consistency_results:
            for event in result["events"]:
                payload = event.get("payload", {})
                
                # Extract session/user identifiers if present
                if "user_id" in payload:
                    user_ids.add(payload["user_id"])
                if "session_id" in payload:
                    session_ids.add(payload["session_id"])
        
        # Session identifiers should be consistent across load-balanced requests
        if len(user_ids) > 1:
            pytest.fail(
                f"Load balancing broke user session consistency: {user_ids}. "
                f"Same WebSocket connection should maintain consistent user identity."
            )
        
        if len(session_ids) > 1:
            pytest.fail(
                f"Load balancing broke session consistency: {session_ids}. "
                f"Same WebSocket connection should maintain consistent session."
            )
    
    @pytest.mark.e2e
    async def test_service_version_compatibility(self, websocket_client, backend_client):
        """Test WebSocket handles service version mismatches gracefully."""
        # Get service version information
        try:
            main_version_response = await backend_client.get("/api/version")
            main_version = main_version_response.json() if main_version_response.status_code == 200 else {}
        except:
            main_version = {}
        
        # Test version compatibility with WebSocket events
        await websocket_client.send_message({
            "type": "version_compatibility_test",
            "payload": {"client_version": "test_1.0.0"}
        })
        
        # Look for version compatibility responses
        version_events = []
        timeout = 8.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    if any(keyword in event_type.lower() for keyword in ["version", "compatibility", "error"]):
                        version_events.append(message)
                        
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate version handling
        compatibility_errors = [
            e for e in version_events 
            if "error" in e.get("type", "").lower() and "version" in str(e).lower()
        ]
        
        # Should handle version mismatches gracefully, not crash
        if compatibility_errors:
            for error in compatibility_errors:
                payload = error.get("payload", {})
                assert "message" in payload or "error" in payload, (
                    "Version compatibility errors should include descriptive messages"
                )
                
                # Should not be internal server errors
                error_message = str(payload)
                assert "500" not in error_message and "internal error" not in error_message.lower(), (
                    f"Version mismatch should not cause internal server error: {error_message}"
                )
    
    # Helper methods (each  <= 8 lines)
    def _identify_service_origin(self, event: Dict[str, Any]) -> str:
        """Identify which service originated the event."""
        payload = str(event.get("payload", {})).lower()
        event_type = event.get("type", "").lower()
        
        if "auth" in event_type or "auth" in payload:
            return "auth_service"
        elif "frontend" in payload or "ui" in event_type:
            return "frontend"
        else:
            return "main_backend"
    
    def _analyze_service_participation(self, events: List[Dict]) -> Dict[str, int]:
        """Analyze which services participated in event responses."""
        participation = {}
        for event in events:
            service = self._identify_service_origin(event)
            participation[service] = participation.get(service, 0) + 1
        return participation
    
    def _extract_session_markers(self, events: List[Dict]) -> Set[str]:
        """Extract session/correlation markers from events."""
        markers = set()
        for event in events:
            payload = event.get("payload", {})
            for field in ["session_id", "correlation_id", "request_id"]:
                if field in payload:
                    markers.add(str(payload[field]))
        return markers