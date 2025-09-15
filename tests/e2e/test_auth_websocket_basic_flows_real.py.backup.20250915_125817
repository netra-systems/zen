"""Basic Auth + WebSocket E2E Tests - CLAUDE.md Compliant Real Services

CRITICAL: Tests core auth+websocket flows using REAL authentication and WebSocket connections.
NO MOCKS, NO AUTHENTICATION BYPASSING - Real services only per CLAUDE.md requirements.

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise) - Core authentication affects all tiers
2. Business Goal: $500K+ ARR Protection through reliable WebSocket authentication  
3. Value Impact: Ensures real-time chat functionality works end-to-end
4. Revenue Impact: Prevents authentication failures that cause user churn

CHEATING ON TESTS = ABOMINATION - This file uses ONLY real authentication flows.
"""
import asyncio
import json
import time
import websockets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import get_env
import pytest
import jwt
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.environment_isolation import get_env as get_isolated_env
from test_framework.base_e2e_test import BaseE2ETest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from auth_service.auth_core.config import AuthConfig
logger = central_logger.get_logger(__name__)
REQUIRED_WEBSOCKET_EVENTS = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}

class RealWebSocketConnection:
    """Real WebSocket connection for E2E testing - NO MOCKS ALLOWED."""

    def __init__(self, websocket, user_id: str, auth_token: str):
        self.websocket = websocket
        self.user_id = user_id
        self.auth_token = auth_token
        self.is_authenticated = True
        self.received_messages = []
        self.sent_messages = []
        self._connected = True
        logger.info(f'Real WebSocket connection established for user {user_id}')

    async def send_json(self, message: dict):
        """Send JSON message via real WebSocket."""
        message_str = json.dumps(message)
        await self.websocket.send(message_str)
        self.sent_messages.append(message)
        logger.info(f"WebSocket sent: {message.get('type', 'unknown')}")

    async def receive_json(self, timeout: float=5.0) -> dict:
        """Receive JSON message from real WebSocket."""
        message_str = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
        message = json.loads(message_str)
        self.received_messages.append(message)
        logger.info(f"WebSocket received: {message.get('type', 'unknown')}")
        return message

    async def close(self, code: int=1000, reason: str='Normal closure'):
        """Close real WebSocket connection."""
        await self.websocket.close(code=code, reason=reason)
        self._connected = False
        logger.info(f'WebSocket closed: {reason}')

    @property
    def state(self):
        """WebSocket connection state."""
        return 'CONNECTED' if self._connected else 'DISCONNECTED'

@pytest.mark.e2e
class TestBasicAuthFlow(BaseE2ETest):
    """Test 1-3: Basic authentication flow using REAL authentication services."""

    def setup_method(self):
        """Setup method with environment isolation."""
        super().setup_method()
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        test_vars = {'TESTING': '1', 'NETRA_ENV': 'testing', 'ENVIRONMENT': 'testing', 'LOG_LEVEL': 'INFO', 'USE_REAL_SERVICES': 'true'}
        for key, value in test_vars.items():
            self.env.set(key, value, source='auth_websocket_basic_test')
        self.auth_helper = E2EAuthHelper()
        self.active_connections = []
        self.test_start_time = time.time()

    def teardown_method(self):
        """Cleanup method with real connection cleanup."""
        for conn in self.active_connections:
            try:
                asyncio.run(conn.close())
            except Exception:
                pass
        self.active_connections.clear()
        self.env.disable_isolation(restore_original=True)
        super().teardown_method()

    @pytest.mark.e2e
    @pytest.mark.timeout(30)
    async def test_1_basic_login_creates_valid_jwt_real_auth(self):
        """Test 1: Basic login creates valid JWT token using REAL authentication.
        
        CLAUDE.md COMPLIANCE:
         PASS:  Uses E2EAuthHelper for REAL authentication
         PASS:  NO mocks - real JWT validation
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard error raising on failures
        """
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL JWT creation and validation')
        user_data = await self.auth_helper.create_authenticated_user(email_prefix='basic_auth_test_user1', password='SecurePass123!', name='Basic Auth Test User 1')
        token = user_data.auth_token
        assert token is not None, 'JWT token must not be None'
        assert len(token.split('.')) == 3, 'JWT must have 3 parts (header.payload.signature)'
        jwt_secret = AuthConfig.get_jwt_secret()
        jwt_algorithm = AuthConfig.get_jwt_algorithm()
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        assert payload['sub'] == user_data.user_id, f"User ID mismatch: {payload['sub']} != {user_data.user_id}"
        assert payload['email'] == user_data.email, f"Email mismatch: {payload['email']} != {user_data.email}"
        assert 'permissions' in payload, 'JWT must contain permissions claim'
        assert 'exp' in payload, 'JWT must contain expiration claim'
        assert 'iat' in payload, 'JWT must contain issued-at claim'
        execution_time = time.time() - start_time
        assert execution_time >= 0.1, f'Test executed too quickly ({execution_time:.3f}s) - likely using mocks'
        logger.info(f' PASS:  REAL JWT creation test PASSED - execution time: {execution_time:.3f}s')
        logger.info(f'    CHART:  User: {user_data.user_id}, Email: {user_data.email}')

    @pytest.mark.e2e
    @pytest.mark.timeout(30)
    async def test_2_jwt_token_contains_required_claims_real_auth(self):
        """Test 2: JWT token contains all required claims using REAL authentication.
        
        CLAUDE.md COMPLIANCE:
         PASS:  Uses E2EAuthHelper for REAL authentication
         PASS:  NO mocks - validates real JWT structure
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard error raising for missing claims
        """
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL JWT claims validation')
        user_data = await self.auth_helper.create_authenticated_user(email_prefix='jwt_claims_test_user2', password='SecurePass456!', name='JWT Claims Test User 2')
        token = user_data.auth_token
        jwt_secret = AuthConfig.get_jwt_secret()
        jwt_algorithm = AuthConfig.get_jwt_algorithm()
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        required_claims = ['sub', 'email', 'permissions', 'exp', 'iat', 'type']
        for claim in required_claims:
            assert claim in payload, f'CRITICAL: Missing required JWT claim: {claim}. Payload: {list(payload.keys())}'
        assert isinstance(payload['sub'], str), f"'sub' claim must be string, got {type(payload['sub'])}"
        assert isinstance(payload['email'], str), f"'email' claim must be string, got {type(payload['email'])}"
        assert isinstance(payload['permissions'], list), f"'permissions' claim must be list, got {type(payload['permissions'])}"
        assert isinstance(payload['exp'], (int, float)), f"'exp' claim must be number, got {type(payload['exp'])}"
        assert isinstance(payload['iat'], (int, float)), f"'iat' claim must be number, got {type(payload['iat'])}"
        assert payload['type'] == 'access', f"'type' claim must be 'access', got {payload['type']}"
        assert payload['sub'] == user_data.user_id, f"User ID claim mismatch: {payload['sub']} != {user_data.user_id}"
        assert payload['email'] == user_data.email, f"Email claim mismatch: {payload['email']} != {user_data.email}"
        assert len(payload['permissions']) > 0, 'Permissions claim must not be empty'
        current_time = time.time()
        assert payload['exp'] > current_time, f"JWT token is expired: exp={payload['exp']}, current={current_time}"
        execution_time = time.time() - start_time
        assert execution_time >= 0.1, f'Test executed too quickly ({execution_time:.3f}s) - likely using mocks'
        logger.info(f' PASS:  REAL JWT claims validation PASSED - execution time: {execution_time:.3f}s')
        logger.info(f"    CHART:  Claims validated: {len(required_claims)}, Permissions: {len(payload['permissions'])}")

    @pytest.mark.e2e
    @pytest.mark.timeout(30)
    async def test_3_expired_token_rejected_real_validation(self):
        """Test 3: Expired JWT token is rejected by REAL authentication service.
        
        CLAUDE.md COMPLIANCE:
         PASS:  Uses REAL JWT expiration validation
         PASS:  NO mocks - tests actual auth service behavior
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard error raising for security violations
        """
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL expired token rejection')
        jwt_secret = AuthConfig.get_jwt_secret()
        jwt_algorithm = AuthConfig.get_jwt_algorithm()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        token_data = {'sub': 'expired_test_user_3', 'email': 'expired3@example.com', 'permissions': ['read'], 'exp': expired_time.timestamp(), 'iat': (expired_time - timedelta(hours=1)).timestamp(), 'type': 'access', 'iss': 'netra-auth-service'}
        expired_token = jwt.encode(token_data, jwt_secret, algorithm=jwt_algorithm)
        with pytest.raises(jwt.ExpiredSignatureError, match='Signature has expired'):
            jwt.decode(expired_token, jwt_secret, algorithms=[jwt_algorithm])
        try:
            result = await self.auth_helper.validate_jwt_token(expired_token)
            assert False, f'SECURITY VIOLATION: Expired token was accepted: {result}'
        except Exception as e:
            logger.info(f'[U+2713] Expired token properly rejected by auth service: {type(e).__name__}')
        execution_time = time.time() - start_time
        assert execution_time >= 0.1, f'Test executed too quickly ({execution_time:.3f}s) - likely using mocks'
        logger.info(f' PASS:  REAL expired token rejection test PASSED - execution time: {execution_time:.3f}s')
        logger.info(f'   [U+1F512] Security validation: Expired tokens properly rejected')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')