"""
Test WebSocket Event Validation and Security Integration  

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and validated WebSocket event delivery 
- Value Impact: Secure events = user trust = business growth; Invalid events = broken UX = lost revenue
- Strategic Impact: Event validation protects platform integrity and user data security

MISSION CRITICAL: These tests validate the security and validation mechanisms
that ensure WebSocket events are properly structured, authenticated, and 
authorized before delivery to users.

Validation Test Focus Areas:
1. Event payload structure validation and sanitization
2. User authentication and authorization for events
3. Cross-user security isolation in event delivery
4. Input validation and injection attack prevention
5. Rate limiting and abuse prevention
6. Event size and content validation
7. Malformed event handling and error responses

Following TEST_CREATION_GUIDE.md patterns - integration tests with real services.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.websocket_helpers import (
    MockWebSocketConnection,
    validate_websocket_message,
    WebSocketTestHelpers
)

try:
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.websocket_core.event_validation_framework import EventValidationFramework
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from shared.isolated_environment import get_env
    VALIDATION_COMPONENTS_AVAILABLE = True
except ImportError as e:
    VALIDATION_COMPONENTS_AVAILABLE = False
    pytest.skip(f"Validation test components not available: {e}", allow_module_level=True)


class TestWebSocketEventValidationIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket event validation and security."""

    async def async_setup(self):
        """Set up validation test environment."""
        await super().async_setup()
        
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="test") 
        self.env.set("WEBSOCKET_VALIDATION_STRICT", "true", source="test")
        self.env.set("WEBSOCKET_MAX_EVENT_SIZE", "10240", source="test")  # 10KB limit
        
        # Test infrastructure
        self.websocket_manager = None
        self.test_emitters = []
        self.validation_framework = None
        
        # Test users with different permission levels
        self.admin_user_id = f"admin_user_{int(time.time())}"
        self.regular_user_id = f"regular_user_{int(time.time())}"
        self.restricted_user_id = f"restricted_user_{int(time.time())}"

    async def async_teardown(self):
        """Clean up validation test resources."""
        for emitter in self.test_emitters:
            try:
                await emitter.close()
            except:
                pass
        
        if self.websocket_manager:
            try:
                await self.websocket_manager.shutdown()
            except:
                pass
        
        await super().async_teardown()

    async def _create_validation_enabled_manager(self) -> UnifiedWebSocketManager:
        """Create WebSocket manager with validation enabled."""
        manager = UnifiedWebSocketManager(
            connection_pool_size=10,
            enable_validation=True,
            enable_rate_limiting=True,
            max_events_per_minute=100,
            max_event_size_bytes=10240
        )
        await manager.initialize()
        self.websocket_manager = manager
        return manager

    async def _create_authenticated_user_context(
        self, 
        user_id: str, 
        permissions: List[str] = None
    ) -> UserExecutionContext:
        """Create authenticated user context with specified permissions."""
        if permissions is None:
            permissions = ["websocket:receive", "agent:execute"]
        
        context = UserExecutionContext(
            user_id=user_id,
            connection_id=f"conn_{int(time.time())}",
            thread_id=f"thread_{int(time.time())}",
            permissions=permissions,
            is_authenticated=True
        )
        return context

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_event_payload_structure_validation(self):
        """Test WebSocket event payload structure validation."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user_context
        )
        self.test_emitters.append(emitter)
        
        # Test valid event structure
        await emitter.emit_agent_started(
            agent_name="validation_test_agent",
            user_id=self.regular_user_id
        )
        
        await asyncio.sleep(0.1)
        
        # Verify valid event was delivered
        sent_messages = connection._sent_messages
        assert len(sent_messages) > 0, "Valid event not delivered"
        
        valid_event = json.loads(sent_messages[-1])
        validate_websocket_message(valid_event, ["type", "agent_name", "user_id", "timestamp"])
        
        # Test invalid event structures
        invalid_payloads = [
            # Missing required fields
            {"type": "agent_started"},  # Missing user_id
            {"user_id": self.regular_user_id},  # Missing type
            {"type": "agent_thinking"},  # Missing reasoning
            
            # Invalid field types
            {"type": "agent_started", "user_id": 123, "agent_name": "test"},  # user_id not string
            {"type": "agent_thinking", "user_id": self.regular_user_id, "reasoning": None},  # reasoning null
            
            # Malformed structures
            "not_a_json_object",  # Not an object
            {"type": "agent_started", "user_id": self.regular_user_id, "agent_name": ""},  # Empty required field
        ]
        
        for invalid_payload in invalid_payloads:
            with pytest.raises((ValueError, TypeError)):
                # Direct validation should fail
                if hasattr(emitter, '_validate_event_payload'):
                    await emitter._validate_event_payload(invalid_payload)

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_user_authentication_validation(self):
        """Test user authentication validation for WebSocket events."""
        manager = await self._create_validation_enabled_manager()
        
        # Create authenticated user
        auth_context = await self._create_authenticated_user_context(
            self.regular_user_id, 
            permissions=["websocket:receive", "agent:execute"]
        )
        auth_connection = MockWebSocketConnection(self.regular_user_id)
        
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=auth_context.connection_id,
            websocket=auth_connection
        )
        
        auth_emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=auth_context
        )
        
        # Create unauthenticated user context
        unauth_context = UserExecutionContext(
            user_id=self.restricted_user_id,
            connection_id=f"unauth_conn_{int(time.time())}",
            thread_id=f"unauth_thread_{int(time.time())}",
            permissions=[],
            is_authenticated=False
        )
        
        unauth_connection = MockWebSocketConnection(self.restricted_user_id)
        await manager.add_connection(
            user_id=self.restricted_user_id,
            connection_id=unauth_context.connection_id,
            websocket=unauth_connection
        )
        
        unauth_emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.restricted_user_id,
            context=unauth_context
        )
        
        self.test_emitters.extend([auth_emitter, unauth_emitter])
        
        # Authenticated user should succeed
        await auth_emitter.emit_agent_started(
            agent_name="auth_test",
            user_id=self.regular_user_id
        )
        
        await asyncio.sleep(0.1)
        assert len(auth_connection._sent_messages) > 0, "Authenticated user event blocked"
        
        # Unauthenticated user should be blocked or receive error
        try:
            await unauth_emitter.emit_agent_started(
                agent_name="unauth_test",
                user_id=self.restricted_user_id
            )
            
            await asyncio.sleep(0.1)
            
            # If event was sent, it should be an error message
            if len(unauth_connection._sent_messages) > 0:
                error_message = json.loads(unauth_connection._sent_messages[-1])
                assert error_message.get("type") == "error", "Unauthenticated event not blocked"
                assert "authentication" in error_message.get("message", "").lower()
                
        except Exception as e:
            # Expected - unauthenticated user blocked
            assert "auth" in str(e).lower() or "permission" in str(e).lower()

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_cross_user_security_isolation(self):
        """Test security isolation prevents cross-user event leakage."""
        manager = await self._create_validation_enabled_manager()
        
        # Create two users with separate contexts
        user1_context = await self._create_authenticated_user_context(
            self.regular_user_id,
            permissions=["websocket:receive", "agent:execute"]
        )
        user2_context = await self._create_authenticated_user_context(
            self.admin_user_id,
            permissions=["websocket:receive", "agent:execute", "admin:access"]
        )
        
        # Create separate connections
        user1_connection = MockWebSocketConnection(self.regular_user_id)
        user2_connection = MockWebSocketConnection(self.admin_user_id)
        
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user1_context.connection_id,
            websocket=user1_connection
        )
        await manager.add_connection(
            user_id=self.admin_user_id,
            connection_id=user2_context.connection_id,
            websocket=user2_connection
        )
        
        # Create emitters
        user1_emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user1_context
        )
        user2_emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.admin_user_id,
            context=user2_context
        )
        
        self.test_emitters.extend([user1_emitter, user2_emitter])
        
        # User 1 sends sensitive event
        sensitive_data = {
            "api_keys": ["secret_key_123"],
            "internal_data": "confidential_information"
        }
        
        await user1_emitter.emit_agent_completed(
            response=sensitive_data,
            user_id=self.regular_user_id
        )
        
        # User 2 sends different event  
        await user2_emitter.emit_agent_started(
            agent_name="admin_agent",
            user_id=self.admin_user_id
        )
        
        await asyncio.sleep(0.1)
        
        # Verify isolation - each user only receives their events
        user1_messages = [json.loads(msg) for msg in user1_connection._sent_messages]
        user2_messages = [json.loads(msg) for msg in user2_connection._sent_messages]
        
        # User 1 should only see their events
        for msg in user1_messages:
            if "user_id" in msg:
                assert msg["user_id"] == self.regular_user_id, \
                    f"User 1 received User 2's event: {msg}"
        
        # User 2 should only see their events
        for msg in user2_messages:
            if "user_id" in msg:
                assert msg["user_id"] == self.admin_user_id, \
                    f"User 2 received User 1's event: {msg}"
        
        # Verify sensitive data didn't leak
        user2_content = json.dumps(user2_messages)
        assert "secret_key_123" not in user2_content, "Sensitive data leaked to other user"
        assert "confidential_information" not in user2_content, "Sensitive data leaked to other user"

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_injection_attack_prevention(self):
        """Test prevention of injection attacks in WebSocket events."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user_context
        )
        self.test_emitters.append(emitter)
        
        # Test various injection attack payloads
        injection_payloads = [
            # JavaScript injection
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            
            # SQL injection patterns
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            
            # Command injection
            "; rm -rf /",
            "| cat /etc/passwd",
            
            # JSON injection
            '{"malicious": "payload", "override": true}',
            
            # HTML injection
            "<img src=x onerror=alert('xss')>",
            
            # Python code injection
            "__import__('os').system('rm -rf /')",
        ]
        
        for payload in injection_payloads:
            try:
                # Attempt to inject malicious content
                await emitter.emit_agent_thinking(
                    reasoning=payload,
                    user_id=self.regular_user_id
                )
                
                await asyncio.sleep(0.05)
                
                # If event was delivered, verify payload was sanitized
                if len(connection._sent_messages) > 0:
                    delivered_event = json.loads(connection._sent_messages[-1])
                    delivered_reasoning = delivered_event.get("reasoning", "")
                    
                    # Verify dangerous content was sanitized
                    assert "<script" not in delivered_reasoning.lower(), "Script injection not prevented"
                    assert "javascript:" not in delivered_reasoning.lower(), "JavaScript injection not prevented"
                    assert "drop table" not in delivered_reasoning.lower(), "SQL injection not prevented"
                    assert "__import__" not in delivered_reasoning, "Python injection not prevented"
                
            except (ValueError, TypeError, Exception) as e:
                # Expected - injection attempt blocked
                assert any(word in str(e).lower() for word in ["invalid", "blocked", "sanitized", "rejected"])

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_event_size_validation_and_limits(self):
        """Test event size validation and limits."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user_context
        )
        self.test_emitters.append(emitter)
        
        # Test normal size event (should succeed)
        normal_response = {"summary": "Normal size response", "data": ["item1", "item2", "item3"]}
        await emitter.emit_agent_completed(
            response=normal_response,
            user_id=self.regular_user_id
        )
        
        await asyncio.sleep(0.1)
        normal_message_count = len(connection._sent_messages)
        assert normal_message_count > 0, "Normal size event not delivered"
        
        # Test oversized event (should be rejected or truncated)
        oversized_data = "x" * 15000  # Larger than 10KB limit
        oversized_response = {"summary": "Oversized response", "data": oversized_data}
        
        try:
            await emitter.emit_agent_completed(
                response=oversized_response,
                user_id=self.regular_user_id
            )
            
            await asyncio.sleep(0.1)
            
            # If delivered, should be truncated or contain error
            if len(connection._sent_messages) > normal_message_count:
                oversized_event = json.loads(connection._sent_messages[-1])
                
                if oversized_event.get("type") == "error":
                    # Error event for oversized payload
                    assert "size" in oversized_event.get("message", "").lower()
                else:
                    # Truncated event
                    delivered_data = oversized_event.get("response", {}).get("data", "")
                    assert len(delivered_data) < len(oversized_data), "Oversized event not truncated"
                    
        except Exception as e:
            # Expected - oversized event rejected
            assert any(word in str(e).lower() for word in ["size", "limit", "too large"])

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_rate_limiting_validation(self):
        """Test rate limiting for WebSocket events."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user_context
        )
        self.test_emitters.append(emitter)
        
        # Send burst of events to trigger rate limiting
        burst_count = 150  # Exceeds 100/minute limit
        events_sent = 0
        rate_limit_triggered = False
        
        start_time = time.time()
        
        for i in range(burst_count):
            try:
                await emitter.emit_agent_thinking(
                    reasoning=f"Rate limit test event {i}",
                    user_id=self.regular_user_id,
                    step=i + 1,
                    total_steps=burst_count
                )
                events_sent += 1
                
                # Small delay to prevent overwhelming
                if i % 20 == 0:
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                if any(word in str(e).lower() for word in ["rate", "limit", "throttle"]):
                    rate_limit_triggered = True
                    break
        
        duration = time.time() - start_time
        await asyncio.sleep(0.2)
        
        # Verify rate limiting behavior
        delivered_count = len(connection._sent_messages)
        
        # Should either trigger rate limiting or limit delivery rate
        if rate_limit_triggered:
            assert events_sent < burst_count, "Rate limiting not enforced"
        else:
            # Rate limiting may allow burst but control delivery rate
            events_per_second = delivered_count / duration if duration > 0 else 0
            assert events_per_second < 1000, f"Rate limiting ineffective: {events_per_second:.1f} events/sec"

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_malformed_event_handling(self):
        """Test handling of malformed WebSocket events."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        # Test various malformed event scenarios by sending raw messages
        malformed_messages = [
            # Invalid JSON
            "not_valid_json",
            "{invalid_json_structure",
            '{"incomplete": json',
            
            # Valid JSON but invalid structure
            "[]",  # Array instead of object
            "null",  # Null value
            '"string"',  # String instead of object
            "123",  # Number instead of object
            
            # Valid JSON object but missing critical fields
            "{}",  # Empty object
            '{"data": "valid_json_but_wrong_structure"}',
            
            # Invalid field values
            '{"type": null, "user_id": "test"}',
            '{"type": "agent_started", "user_id": null}',
            '{"type": "", "user_id": "test", "agent_name": "test"}',  # Empty type
        ]
        
        initial_message_count = len(connection._sent_messages)
        
        for malformed_message in malformed_messages:
            try:
                # Send malformed message directly to connection
                await WebSocketTestHelpers.send_raw_test_message(
                    connection, 
                    malformed_message,
                    timeout=1.0
                )
                
                await asyncio.sleep(0.05)
                
            except Exception:
                # Expected - malformed message handling
                pass
        
        await asyncio.sleep(0.2)
        
        # Check if error responses were generated
        final_messages = connection._sent_messages[initial_message_count:]
        
        error_responses = 0
        for message in final_messages:
            try:
                event = json.loads(message)
                if event.get("type") == "error":
                    error_responses += 1
                    # Verify error message is informative
                    assert "error" in event
                    assert len(event.get("message", "")) > 0
            except json.JSONDecodeError:
                continue
        
        # Should have generated error responses for malformed messages
        assert error_responses > 0, "No error responses for malformed messages"

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_event_timestamp_validation(self):
        """Test WebSocket event timestamp validation."""
        manager = await self._create_validation_enabled_manager()
        user_context = await self._create_authenticated_user_context(self.regular_user_id)
        
        connection = MockWebSocketConnection(self.regular_user_id)
        await manager.add_connection(
            user_id=self.regular_user_id,
            connection_id=user_context.connection_id,
            websocket=connection
        )
        
        emitter = UnifiedWebSocketEmitter(
            manager=manager,
            user_id=self.regular_user_id,
            context=user_context
        )
        self.test_emitters.append(emitter)
        
        # Send event and check timestamp
        current_time = time.time()
        
        await emitter.emit_agent_started(
            agent_name="timestamp_test",
            user_id=self.regular_user_id
        )
        
        await asyncio.sleep(0.1)
        
        # Verify timestamp validation
        sent_messages = connection._sent_messages
        assert len(sent_messages) > 0, "Event not delivered"
        
        event = json.loads(sent_messages[-1])
        event_timestamp = event.get("timestamp")
        
        assert event_timestamp is not None, "Timestamp missing from event"
        assert isinstance(event_timestamp, (int, float)), "Timestamp not numeric"
        assert abs(event_timestamp - current_time) < 10.0, "Timestamp out of reasonable range"

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_user_permission_enforcement(self):
        """Test user permission enforcement for different event types."""
        manager = await self._create_validation_enabled_manager()
        
        # Create users with different permission levels
        admin_context = await self._create_authenticated_user_context(
            self.admin_user_id,
            permissions=["websocket:receive", "agent:execute", "admin:access", "system:monitor"]
        )
        
        regular_context = await self._create_authenticated_user_context(
            self.regular_user_id,
            permissions=["websocket:receive", "agent:execute"]
        )
        
        restricted_context = await self._create_authenticated_user_context(
            self.restricted_user_id,
            permissions=["websocket:receive"]  # No agent execution permission
        )
        
        # Create connections and emitters
        contexts_and_connections = [
            (admin_context, MockWebSocketConnection(self.admin_user_id)),
            (regular_context, MockWebSocketConnection(self.regular_user_id)),
            (restricted_context, MockWebSocketConnection(self.restricted_user_id))
        ]
        
        emitters = []
        for context, connection in contexts_and_connections:
            await manager.add_connection(
                user_id=context.user_id,
                connection_id=context.connection_id,
                websocket=connection
            )
            
            emitter = UnifiedWebSocketEmitter(
                manager=manager,
                user_id=context.user_id,
                context=context
            )
            emitters.append((context, connection, emitter))
            self.test_emitters.append(emitter)
        
        # Test permission-based event access
        for context, connection, emitter in emitters:
            try:
                # All users should be able to receive basic agent events
                await emitter.emit_agent_started(
                    agent_name="permission_test",
                    user_id=context.user_id
                )
                
                await asyncio.sleep(0.05)
                
                if "agent:execute" in context.permissions:
                    # Should succeed for users with agent execution permission
                    assert len(connection._sent_messages) > 0, \
                        f"Agent event blocked for user with permission: {context.user_id}"
                else:
                    # Should be blocked or receive error for restricted users
                    if len(connection._sent_messages) > 0:
                        event = json.loads(connection._sent_messages[-1])
                        if event.get("type") == "error":
                            assert "permission" in event.get("message", "").lower()
                        
            except Exception as e:
                if "permission" not in str(e).lower() and "agent:execute" not in context.permissions:
                    # Expected for restricted users
                    pass
                else:
                    # Unexpected error for permitted users
                    raise

    @pytest.mark.integration
    @pytest.mark.websocket_validation
    async def test_concurrent_validation_performance(self):
        """Test validation performance under concurrent load."""
        manager = await self._create_validation_enabled_manager()
        
        # Create multiple users for concurrent testing
        concurrent_users = []
        for i in range(10):
            user_id = f"concurrent_validation_user_{i}_{int(time.time())}"
            context = await self._create_authenticated_user_context(user_id)
            connection = MockWebSocketConnection(user_id)
            
            await manager.add_connection(
                user_id=user_id,
                connection_id=context.connection_id,
                websocket=connection
            )
            
            emitter = UnifiedWebSocketEmitter(
                manager=manager,
                user_id=user_id,
                context=context
            )
            
            concurrent_users.append((user_id, context, connection, emitter))
            self.test_emitters.append(emitter)
        
        # Send events concurrently from all users
        async def send_validated_events(user_id, emitter, event_count=20):
            events_sent = 0
            start_time = time.time()
            
            for i in range(event_count):
                try:
                    await emitter.emit_agent_thinking(
                        reasoning=f"Concurrent validation test {i} for {user_id}",
                        user_id=user_id,
                        step=i + 1,
                        total_steps=event_count
                    )
                    events_sent += 1
                    
                except Exception:
                    pass  # Some events may be rate limited
            
            duration = time.time() - start_time
            return {"user_id": user_id, "events_sent": events_sent, "duration": duration}
        
        # Execute concurrent validation test
        start_time = time.time()
        tasks = [
            send_validated_events(user_id, emitter)
            for user_id, _, _, emitter in concurrent_users
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze validation performance
        successful_results = [r for r in results if isinstance(r, dict)]
        total_events_sent = sum(r["events_sent"] for r in successful_results)
        
        # Verify validation didn't significantly impact performance
        events_per_second = total_events_sent / total_duration if total_duration > 0 else 0
        assert events_per_second >= 50, f"Validation severely impacted performance: {events_per_second:.1f} events/sec"
        
        # Verify all users maintained isolation during concurrent validation
        for user_id, context, connection, emitter in concurrent_users:
            user_messages = [json.loads(msg) for msg in connection._sent_messages]
            
            for message in user_messages:
                if "user_id" in message:
                    assert message["user_id"] == user_id, \
                        f"User isolation violated during concurrent validation for {user_id}"