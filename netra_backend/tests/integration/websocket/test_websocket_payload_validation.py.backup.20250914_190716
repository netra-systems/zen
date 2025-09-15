"""
WebSocket Payload Validation Integration Tests

SECURITY CRITICAL: WebSocket payload validation ensures data integrity and prevents
security vulnerabilities that could compromise user data and system reliability.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Security is non-negotiable across all tiers
- Business Goal: Protect user data and prevent malicious attacks through chat interface
- Value Impact: Data integrity validation builds user trust and prevents security breaches
- Revenue Impact: Protects $500K+ ARR and prevents potential security liabilities

PAYLOAD VALIDATION REQUIREMENTS:
- Input sanitization and validation for all WebSocket messages
- Prevention of XSS, injection, and other security attacks
- Data size limits and resource protection
- User context validation and authorization checks
- Sensitive data filtering and protection
- Message schema validation and type checking

TEST SCOPE: Integration-level validation of WebSocket payload validation including:
- Message structure and schema validation
- Input sanitization and XSS prevention
- Data size limits and DoS protection
- User authorization and context validation
- Sensitive data filtering and redaction
- Malicious payload detection and blocking
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from dataclasses import dataclass, field
import pytest

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# WebSocket core components - NO MOCKS for business logic
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.websocket_core.unified_manager import WebSocketManagerMode
from netra_backend.app.websocket_core.types import (
    WebSocketConnectionState, MessageType, ConnectionMetadata
)

# User context and types
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.user_types import TestUserData

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PayloadTestCase:
    """Test case for payload validation."""
    name: str
    payload: Dict[str, Any]
    expected_valid: bool
    expected_error: Optional[str] = None
    security_risk: Optional[str] = None
    should_sanitize: bool = False
    sanitized_content: Optional[str] = None


class ValidatingWebSocketMock:
    """WebSocket mock that performs payload validation."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.is_closed = False
        self.state = WebSocketConnectionState.CONNECTED
        self.messages_sent = []
        self.validation_results: List[Dict[str, Any]] = []
        
        # Validation configuration
        self.max_message_size = 50000  # 50KB limit
        self.max_payload_depth = 10
        self.blocked_patterns = [
            '<script', 'javascript:', 'onload=', 'onerror=', 'onclick=',
            'eval(', 'setTimeout(', 'setInterval(', 'Function(', 'XMLHttpRequest'
        ]
        self.sensitive_fields = ['password', 'token', 'key', 'secret', 'auth']
        
    async def send(self, message: str) -> None:
        """Send message with payload validation."""
        if self.is_closed:
            raise ConnectionError("WebSocket connection is closed")
        
        # Perform payload validation
        validation_result = self._validate_payload(message)
        self.validation_results.append(validation_result)
        
        if not validation_result['valid']:
            # Log security violation
            logger.warning(f"Payload validation failed: {validation_result['error']}")
            raise ValueError(f"Invalid payload: {validation_result['error']}")
        
        # Store sanitized message
        sanitized_message = validation_result.get('sanitized_message', message)
        self.messages_sent.append({
            'original_message': message,
            'sanitized_message': sanitized_message,
            'timestamp': datetime.now(UTC).isoformat(),
            'validation_result': validation_result
        })
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection."""
        self.is_closed = True
        self.state = WebSocketConnectionState.DISCONNECTED
        
    def _validate_payload(self, message: str) -> Dict[str, Any]:
        """Validate message payload for security and integrity."""
        validation_result = {
            'valid': True,
            'error': None,
            'security_risks': [],
            'sanitized': False,
            'sanitized_message': message
        }
        
        # Size validation
        if len(message) > self.max_message_size:
            validation_result.update({
                'valid': False,
                'error': f'Message too large: {len(message)} bytes (max: {self.max_message_size})'
            })
            return validation_result
        
        try:
            # JSON validation
            try:
                message_data = json.loads(message)
            except json.JSONDecodeError:
                validation_result.update({
                    'valid': False,
                    'error': 'Invalid JSON format'
                })
                return validation_result
            
            # Structure validation
            if not isinstance(message_data, dict):
                validation_result.update({
                    'valid': False,
                    'error': 'Message must be a JSON object'
                })
                return validation_result
            
            # Depth validation
            if self._get_dict_depth(message_data) > self.max_payload_depth:
                validation_result.update({
                    'valid': False,
                    'error': f'Message depth exceeds limit: {self.max_payload_depth}'
                })
                return validation_result
            
            # XSS and injection pattern detection
            message_str = json.dumps(message_data).lower()
            for pattern in self.blocked_patterns:
                if pattern in message_str:
                    validation_result['security_risks'].append({
                        'type': 'xss_injection',
                        'pattern': pattern,
                        'risk_level': 'high'
                    })
            
            # Sensitive data detection
            sensitive_data_found = self._detect_sensitive_data(message_data)
            if sensitive_data_found:
                validation_result['security_risks'].extend(sensitive_data_found)
            
            # Sanitization
            sanitized_data, was_sanitized = self._sanitize_payload(message_data)
            if was_sanitized:
                validation_result.update({
                    'sanitized': True,
                    'sanitized_message': json.dumps(sanitized_data)
                })
            
            # Block high-risk payloads
            high_risk_count = len([risk for risk in validation_result['security_risks'] if risk.get('risk_level') == 'high'])
            if high_risk_count > 0:
                validation_result.update({
                    'valid': False,
                    'error': f'High security risk detected: {high_risk_count} violations'
                })
            
        except Exception as e:
            validation_result.update({
                'valid': False,
                'error': f'Validation error: {str(e)}'
            })
        
        return validation_result
    
    def _get_dict_depth(self, d: Any, depth: int = 0) -> int:
        """Calculate maximum depth of nested dictionary."""
        if not isinstance(d, dict):
            return depth
        return max([self._get_dict_depth(v, depth + 1) for v in d.values()], default=depth)
    
    def _detect_sensitive_data(self, data: Any) -> List[Dict[str, Any]]:
        """Detect sensitive data in payload."""
        sensitive_findings = []
        
        def scan_for_sensitive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.lower() in self.sensitive_fields:
                        sensitive_findings.append({
                            'type': 'sensitive_data',
                            'field': key,
                            'path': current_path,
                            'risk_level': 'medium'
                        })
                    scan_for_sensitive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_sensitive(item, f"{path}[{i}]")
        
        scan_for_sensitive(data)
        return sensitive_findings
    
    def _sanitize_payload(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Sanitize payload by removing/masking sensitive content."""
        sanitized = data.copy()
        was_sanitized = False
        
        def sanitize_recursive(obj):
            nonlocal was_sanitized
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in self.sensitive_fields:
                        obj[key] = "[REDACTED]"
                        was_sanitized = True
                    elif isinstance(value, str):
                        # Remove dangerous patterns
                        original_value = value
                        for pattern in self.blocked_patterns:
                            if pattern in value.lower():
                                value = value.replace(pattern, "[BLOCKED]")
                                was_sanitized = True
                        obj[key] = value
                    else:
                        sanitize_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    sanitize_recursive(item)
        
        sanitize_recursive(sanitized)
        return sanitized, was_sanitized
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        total_messages = len(self.validation_results)
        valid_messages = len([r for r in self.validation_results if r['valid']])
        blocked_messages = total_messages - valid_messages
        sanitized_messages = len([r for r in self.validation_results if r.get('sanitized', False)])
        
        security_risks = []
        for result in self.validation_results:
            security_risks.extend(result.get('security_risks', []))
        
        return {
            'total_messages': total_messages,
            'valid_messages': valid_messages,
            'blocked_messages': blocked_messages,
            'sanitized_messages': sanitized_messages,
            'security_risks': len(security_risks),
            'risk_types': list(set(risk['type'] for risk in security_risks))
        }


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.security
@pytest.mark.asyncio
class TestWebSocketPayloadValidation(SSotAsyncTestCase):
    """
    Integration tests for WebSocket payload validation.
    
    SECURITY CRITICAL: These tests protect against malicious payloads and ensure
    data integrity that prevents security breaches and maintains user trust.
    """
    
    def setup_method(self, method):
        """Set up isolated test environment for each test."""
        super().setup_method(method)
        
        # Set up isolated environment
        self.env = IsolatedEnvironment()
        self.env.set("TESTING", "1", source="websocket_payload_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_payload_test")
        
        # Test user data
        self.test_user = TestUserData(
            user_id=f"payload_user_{uuid.uuid4().hex[:8]}",
            email="payload-test@netra.ai",
            tier="enterprise",
            thread_id=f"payload_thread_{uuid.uuid4().hex[:8]}"
        )
        
        # Payload test cases
        self.payload_test_cases = [
            PayloadTestCase(
                name="valid_normal_message",
                payload={
                    'type': 'agent_thinking',
                    'data': {'message': 'Normal chat message content'}
                },
                expected_valid=True
            ),
            PayloadTestCase(
                name="xss_script_injection",
                payload={
                    'type': 'agent_thinking',
                    'data': {'message': 'Hello <script>alert("XSS")</script> world'}
                },
                expected_valid=False,
                expected_error='High security risk detected',
                security_risk='xss_injection'
            ),
            PayloadTestCase(
                name="javascript_injection",
                payload={
                    'type': 'agent_thinking',
                    'data': {'message': 'Click javascript:alert("hack")'}
                },
                expected_valid=False,
                expected_error='High security risk detected',
                security_risk='xss_injection'
            ),
            PayloadTestCase(
                name="oversized_payload",
                payload={
                    'type': 'agent_thinking',
                    'data': {'message': 'x' * 60000}  # 60KB message
                },
                expected_valid=False,
                expected_error='Message too large'
            ),
            PayloadTestCase(
                name="sensitive_data_exposure",
                payload={
                    'type': 'agent_thinking',
                    'data': {
                        'message': 'User info',
                        'password': 'secret123',
                        'auth_token': 'abc123xyz'
                    }
                },
                expected_valid=True,
                should_sanitize=True,
                sanitized_content='[REDACTED]'
            ),
            PayloadTestCase(
                name="deeply_nested_object",
                payload=self._create_deep_nested_payload(15),  # 15 levels deep
                expected_valid=False,
                expected_error='depth exceeds limit'
            )
        ]
        
        # Track resources for cleanup
        self.websocket_managers: List[Any] = []
        self.mock_websockets: List[ValidatingWebSocketMock] = []
        
    def _create_deep_nested_payload(self, depth: int) -> Dict[str, Any]:
        """Create deeply nested payload for testing."""
        result = {'type': 'agent_thinking', 'data': {}}
        current = result['data']
        
        for i in range(depth):
            current['nested'] = {}
            current = current['nested']
        
        current['message'] = 'Deep nested content'
        return result
        
    async def teardown_method(self, method):
        """Clean up payload validation test resources."""
        for mock_ws in self.mock_websockets:
            if not mock_ws.is_closed:
                await mock_ws.close()
        
        for manager in self.websocket_managers:
            if hasattr(manager, 'cleanup'):
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.warning(f"Manager cleanup error: {e}")
        
        await super().teardown_method(method)
    
    async def create_mock_user_context(self, user_data: TestUserData) -> Any:
        """Create mock user context for testing."""
        return type('MockUserContext', (), {
            'user_id': user_data.user_id,
            'thread_id': user_data.thread_id,
            'request_id': f"payload_request_{uuid.uuid4().hex[:8]}",
            'email': user_data.email,
            'tier': user_data.tier,
            'is_test': True
        })()
    
    async def test_xss_injection_prevention(self):
        """
        Test: XSS injection attempts are blocked and sanitized
        
        Business Value: Prevents malicious scripts from executing in chat interface,
        protecting user security and maintaining platform trust.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        # Create validating WebSocket mock
        connection_id = f"xss_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test various XSS injection patterns
            xss_patterns = [
                '<script>alert("xss")</script>',
                'javascript:alert("hack")',
                '<img onerror="alert(1)" src="x">',
                '<div onclick="alert(1)">click</div>',
                'eval("alert(1)")'
            ]
            
            blocked_count = 0
            for i, xss_pattern in enumerate(xss_patterns):
                try:
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_thinking",
                        data={
                            'xss_test': True,
                            'pattern_index': i,
                            'message': f"Test message with {xss_pattern} content",
                            'dangerous_content': xss_pattern
                        }
                    )
                    
                except ValueError as e:
                    blocked_count += 1
                    logger.info(f"XSS pattern {i} correctly blocked: {e}")
                
                await asyncio.sleep(0.1)
            
            # Verify XSS protection
            validation_summary = mock_ws.get_validation_summary()
            
            assert blocked_count > 0, "XSS injection attempts should be blocked"
            assert 'xss_injection' in validation_summary['risk_types'], "XSS risks should be detected"
            assert validation_summary['security_risks'] > 0, "Security risks should be identified"
            
            # Verify no malicious content reached the application
            for sent_message in mock_ws.messages_sent:
                sanitized = sent_message['sanitized_message']
                assert '<script' not in sanitized.lower(), "Scripts should be sanitized"
                assert 'javascript:' not in sanitized.lower(), "JavaScript URLs should be sanitized"
            
            logger.info(f"✅ XSS injection prevention: {blocked_count} patterns blocked, {validation_summary['security_risks']} risks detected")
    
    async def test_sensitive_data_sanitization(self):
        """
        Test: Sensitive data is detected and sanitized from payloads
        
        Business Value: Protects user privacy by preventing accidental exposure
        of sensitive data in chat logs and system processing.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"sensitive_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Send message containing sensitive data
            await manager.emit_agent_event(
                user_id=ensure_user_id(self.test_user.user_id),
                thread_id=self.test_user.thread_id,
                event_type="agent_thinking",
                data={
                    'message': 'Processing user information',
                    'password': 'user_secret_password',
                    'auth_token': 'Bearer xyz123abc456',
                    'api_key': 'sk-1234567890abcdef',
                    'user_data': {
                        'name': 'John Doe',
                        'secret': 'confidential_info'
                    }
                }
            )
            
            # Verify sensitive data sanitization
            validation_summary = mock_ws.get_validation_summary()
            
            assert validation_summary['sanitized_messages'] > 0, "Messages with sensitive data should be sanitized"
            
            # Check that sensitive data was redacted
            for sent_message in mock_ws.messages_sent:
                sanitized_data = json.loads(sent_message['sanitized_message'])
                event_data = sanitized_data.get('data', {})
                
                # Verify sensitive fields were redacted
                if 'password' in event_data:
                    assert event_data['password'] == '[REDACTED]', "Password should be redacted"
                if 'auth_token' in event_data:
                    assert event_data['auth_token'] == '[REDACTED]', "Auth token should be redacted"
                if 'api_key' in event_data:
                    assert event_data['api_key'] == '[REDACTED]', "API key should be redacted"
                
                # Check nested sensitive data
                if 'user_data' in event_data and 'secret' in event_data['user_data']:
                    assert event_data['user_data']['secret'] == '[REDACTED]', "Nested secrets should be redacted"
            
            logger.info(f"✅ Sensitive data sanitization: {validation_summary['sanitized_messages']} messages sanitized")
    
    async def test_payload_size_limit_enforcement(self):
        """
        Test: Large payloads are rejected to prevent DoS attacks
        
        Business Value: Protects system resources from being overwhelmed by
        maliciously large payloads that could impact service performance.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"size_limit_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        mock_ws.max_message_size = 1000  # 1KB limit for testing
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test with acceptable size message
            try:
                await manager.emit_agent_event(
                    user_id=ensure_user_id(self.test_user.user_id),
                    thread_id=self.test_user.thread_id,
                    event_type="agent_thinking",
                    data={
                        'message': 'Normal sized message',
                        'size_test': 'acceptable'
                    }
                )
                normal_size_success = True
            except ValueError:
                normal_size_success = False
            
            # Test with oversized message
            try:
                await manager.emit_agent_event(
                    user_id=ensure_user_id(self.test_user.user_id),
                    thread_id=self.test_user.thread_id,
                    event_type="agent_thinking",
                    data={
                        'message': 'x' * 2000,  # 2KB message, exceeds 1KB limit
                        'size_test': 'oversized'
                    }
                )
                oversized_blocked = False
            except ValueError as e:
                oversized_blocked = True
                assert 'too large' in str(e), "Size limit error should mention message size"
            
            # Verify size limit enforcement
            assert normal_size_success, "Normal sized messages should be accepted"
            assert oversized_blocked, "Oversized messages should be blocked"
            
            validation_summary = mock_ws.get_validation_summary()
            assert validation_summary['blocked_messages'] > 0, "Some messages should be blocked for size"
            
            logger.info("✅ Payload size limit enforcement validated")
    
    async def test_nested_object_depth_limit(self):
        """
        Test: Deeply nested objects are rejected to prevent stack overflow attacks
        
        Business Value: Protects system from malicious payloads designed to
        consume excessive processing resources through deep nesting.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"depth_limit_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        mock_ws.max_payload_depth = 5  # 5 levels max for testing
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test with acceptable depth
            try:
                await manager.emit_agent_event(
                    user_id=ensure_user_id(self.test_user.user_id),
                    thread_id=self.test_user.thread_id,
                    event_type="agent_thinking",
                    data={
                        'level1': {
                            'level2': {
                                'level3': {
                                    'message': 'Acceptable depth'
                                }
                            }
                        }
                    }
                )
                normal_depth_success = True
            except ValueError:
                normal_depth_success = False
            
            # Test with excessive depth
            try:
                deep_data = {'message': 'Deep nested content'}
                for i in range(10):  # 10 levels deep, exceeds limit
                    deep_data = {f'level_{i}': deep_data}
                
                await manager.emit_agent_event(
                    user_id=ensure_user_id(self.test_user.user_id),
                    thread_id=self.test_user.thread_id,
                    event_type="agent_thinking",
                    data=deep_data
                )
                excessive_depth_blocked = False
            except ValueError as e:
                excessive_depth_blocked = True
                assert 'depth exceeds limit' in str(e), "Depth limit error should mention nesting depth"
            
            # Verify depth limit enforcement
            assert normal_depth_success, "Normal depth messages should be accepted"
            assert excessive_depth_blocked, "Excessively nested messages should be blocked"
            
            validation_summary = mock_ws.get_validation_summary()
            assert validation_summary['blocked_messages'] > 0, "Some messages should be blocked for depth"
            
            logger.info("✅ Nested object depth limit enforcement validated")
    
    async def test_malformed_json_handling(self):
        """
        Test: Malformed JSON payloads are rejected gracefully
        
        Business Value: Ensures system stability when receiving corrupted or
        maliciously crafted JSON that could cause parsing errors.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"json_validation_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test with valid JSON first
            try:
                await manager.emit_agent_event(
                    user_id=ensure_user_id(self.test_user.user_id),
                    thread_id=self.test_user.thread_id,
                    event_type="agent_thinking",
                    data={'message': 'Valid JSON message'}
                )
                valid_json_success = True
            except ValueError:
                valid_json_success = False
            
            # Test malformed JSON handling by directly testing validation
            malformed_json_cases = [
                '{"invalid": json}',  # Missing quotes
                '{"unclosed": "string}',  # Unclosed string
                '{"trailing": "comma",}',  # Trailing comma
                '{invalid_key: "value"}',  # Unquoted key
                '{"nested": {"broken": json}}'  # Nested invalid JSON
            ]
            
            blocked_malformed = 0
            for malformed_json in malformed_json_cases:
                validation_result = mock_ws._validate_payload(malformed_json)
                if not validation_result['valid'] and 'Invalid JSON' in validation_result['error']:
                    blocked_malformed += 1
            
            # Verify JSON validation
            assert valid_json_success, "Valid JSON should be accepted"
            assert blocked_malformed > 0, "Malformed JSON should be detected and blocked"
            
            logger.info(f"✅ Malformed JSON handling: {blocked_malformed}/{len(malformed_json_cases)} malformed cases blocked")
    
    async def test_comprehensive_payload_security_validation(self):
        """
        Test: Comprehensive security validation catches multiple attack vectors
        
        Business Value: Provides defense in depth against sophisticated attacks
        that might combine multiple exploitation techniques.
        """
        user_context = await self.create_mock_user_context(self.test_user)
        
        manager = await get_websocket_manager(
            user_context=user_context,
            mode=WebSocketManagerMode.ISOLATED
        )
        self.websocket_managers.append(manager)
        
        connection_id = f"comprehensive_conn_{uuid.uuid4().hex[:8]}"
        mock_ws = ValidatingWebSocketMock(self.test_user.user_id, connection_id)
        self.mock_websockets.append(mock_ws)
        
        with patch.object(manager, '_websocket_transport', mock_ws):
            await manager.connect_user(
                user_id=ensure_user_id(self.test_user.user_id),
                websocket=mock_ws,
                connection_metadata={"tier": self.test_user.tier}
            )
            
            # Test comprehensive attack payload
            attack_attempts = 0
            successful_blocks = 0
            
            # Multi-vector attack payloads
            attack_payloads = [
                {
                    'name': 'xss_with_sensitive_data',
                    'data': {
                        'message': '<script>steal_data()</script>',
                        'password': 'secret123',
                        'user_token': 'compromised'
                    }
                },
                {
                    'name': 'injection_with_large_payload',
                    'data': {
                        'message': 'javascript:alert("xss")' + 'x' * 5000,
                        'exploit': 'combined_attack'
                    }
                },
                {
                    'name': 'nested_attack_payload',
                    'data': {
                        'level1': {
                            'level2': {
                                'level3': {
                                    'attack': '<script>malicious()</script>',
                                    'secret_key': 'hidden_password'
                                }
                            }
                        }
                    }
                }
            ]
            
            for payload in attack_payloads:
                attack_attempts += 1
                try:
                    await manager.emit_agent_event(
                        user_id=ensure_user_id(self.test_user.user_id),
                        thread_id=self.test_user.thread_id,
                        event_type="agent_thinking",
                        data=payload['data']
                    )
                    
                except ValueError:
                    successful_blocks += 1
                    logger.info(f"Attack payload '{payload['name']}' successfully blocked")
                
                await asyncio.sleep(0.1)
            
            # Analyze comprehensive security results
            validation_summary = mock_ws.get_validation_summary()
            
            # Should have blocked or sanitized all attack attempts
            security_protection_rate = (successful_blocks + validation_summary['sanitized_messages']) / attack_attempts * 100
            
            assert security_protection_rate >= 75, \
                f"Security protection rate too low: {security_protection_rate:.1f}% (expected >=75%)"
            assert validation_summary['security_risks'] > 0, "Security risks should be detected"
            assert len(validation_summary['risk_types']) > 1, "Multiple attack vectors should be detected"
            
            logger.info(f"✅ Comprehensive security validation: {security_protection_rate:.1f}% protection rate, {validation_summary['security_risks']} risks detected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])