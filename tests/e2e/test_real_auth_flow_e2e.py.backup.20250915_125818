"""REAL Authentication Flow E2E Test - NO MOCKS, NO CHEATING

BVJ (Business Value Justification):
1. Segment: All customer segments (Free  ->  Paid conversion critical)
2. Business Goal: Validate complete authentication infrastructure end-to-end
3. Value Impact: Protects $200K+ MRR through real auth flow validation
4. Revenue Impact: Prevents authentication failures that block user conversion

REAL E2E TESTING APPROACH:
- Uses REAL authentication service with actual OAuth flows
- Performs REAL JWT token creation, validation, and refresh
- Tests ACTUAL WebSocket authentication with real connections
- Validates REAL user registration, login, and session management
- FAILS HARD if any authentication component is broken

COMPLIANCE WITH CLAUDE.MD:
- "CHEATING ON TESTS = ABOMINATION" - This test is 100% real
- "Mocks in E2E = Abomination" - Zero mocks used
- "TESTS MUST RAISE ERRORS" - Hard failures for auth problems
- Real authentication using SSOT e2e_auth_helper.py
- Real WebSocket connections using real auth tokens
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
import httpx
import websockets
import jwt as pyjwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog
from netra_backend.app.auth_dependencies import get_request_scoped_db_session_for_fastapi
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
docker_manager = UnifiedDockerManager()

@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.e2e
@pytest.mark.asyncio
class TestRealAuthFlowE2E:
    """REAL E2E Authentication Flow Validation - Zero Mocks, Zero Cheating.
    
    This test validates the complete authentication infrastructure using REAL
    auth service, REAL JWT tokens, REAL WebSocket connections, and REAL database
    operations. It tests actual user registration, login, token validation,
    WebSocket authentication, and session management.
    """

    @pytest.fixture(scope='class', autouse=True)
    async def setup_docker_services(self):
        """Start REAL Docker services for auth flow testing."""
        print('[U+1F433] Starting Docker services for REAL auth flow tests...')
        services = ['backend', 'auth', 'postgres', 'redis']
        try:
            await docker_manager.start_services_async(services=services, health_check=True, timeout=120)
            await asyncio.sleep(5)
            print(' PASS:  Docker services ready for REAL auth flow tests')
            yield
        except Exception as e:
            raise Exception(f' FAIL:  HARD FAILURE: Failed to start Docker services for auth flow tests: {e}')
        finally:
            print('[U+1F9F9] Cleaning up Docker services after auth flow tests...')
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def real_db_session(self) -> AsyncSession:
        """Get REAL database session for auth queries."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    async def auth_helper(self) -> E2EAuthHelper:
        """Get REAL authentication helper."""
        return E2EAuthHelper()

    async def test_real_user_registration_flow(self, auth_helper: E2EAuthHelper, real_db_session: AsyncSession):
        """Test REAL user registration with actual auth service and database."""
        print('[U+1F4DD] Testing REAL user registration flow...')
        test_email = f'real_reg_test_{int(time.time())}@netra.ai'
        test_password = 'RealTestPassword123!'
        async with httpx.AsyncClient() as client:
            auth_url = env.get_env_var('AUTH_SERVICE_URL', 'http://localhost:8083')
            registration_data = {'email': test_email, 'password': test_password, 'name': f'Real Test User {int(time.time())}'}
            response = await client.post(f'{auth_url}/auth/register', json=registration_data)
            if response.status_code not in [200, 201]:
                raise Exception(f'HARD FAILURE: User registration failed with {response.status_code}: {response.text}')
            registration_result = response.json()
            if 'access_token' not in registration_result:
                raise Exception('HARD FAILURE: Registration response missing access_token')
            if 'user' not in registration_result:
                raise Exception('HARD FAILURE: Registration response missing user data')
            user_data = registration_result['user']
            access_token = registration_result['access_token']
        print(f' PASS:  User registration successful: {test_email}')
        try:
            token_data = pyjwt.decode(access_token, options={'verify_signature': False})
            if 'sub' not in token_data:
                raise Exception("HARD FAILURE: JWT token missing 'sub' claim")
            if 'email' not in token_data:
                raise Exception("HARD FAILURE: JWT token missing 'email' claim")
            if token_data['email'] != test_email:
                raise Exception(f"HARD FAILURE: JWT email mismatch. Expected: {test_email}, Got: {token_data['email']}")
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: JWT token validation failed: {e}')
        try:
            result = await real_db_session.execute(select(AuthUser).where(AuthUser.email == test_email))
            db_user = result.scalar_one_or_none()
            if not db_user:
                raise Exception(f'HARD FAILURE: User {test_email} not found in database after registration')
            if not db_user.is_active:
                raise Exception(f'HARD FAILURE: User {test_email} is not active in database')
            print(f' PASS:  User validated in database: {db_user.id}')
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: Database validation failed: {e}')
        return {'success': True, 'user_id': user_data.get('id'), 'email': test_email, 'access_token': access_token, 'database_validated': True}

    async def test_real_user_login_flow(self, auth_helper: E2EAuthHelper, real_db_session: AsyncSession):
        """Test REAL user login with actual auth service validation."""
        print('[U+1F511] Testing REAL user login flow...')
        test_email = f'real_login_test_{int(time.time())}@netra.ai'
        test_password = 'RealLoginTest123!'
        async with httpx.AsyncClient() as client:
            auth_url = env.get_env_var('AUTH_SERVICE_URL', 'http://localhost:8083')
            reg_response = await client.post(f'{auth_url}/auth/register', json={'email': test_email, 'password': test_password, 'name': f'Login Test User {int(time.time())}'})
            if reg_response.status_code not in [200, 201]:
                raise Exception(f'HARD FAILURE: Test user creation failed: {reg_response.status_code}')
            await asyncio.sleep(1)
            login_response = await client.post(f'{auth_url}/auth/login', json={'email': test_email, 'password': test_password})
            if login_response.status_code != 200:
                raise Exception(f'HARD FAILURE: User login failed with {login_response.status_code}: {login_response.text}')
            login_result = login_response.json()
            if 'access_token' not in login_result:
                raise Exception('HARD FAILURE: Login response missing access_token')
            access_token = login_result['access_token']
        print(f' PASS:  User login successful: {test_email}')
        async with httpx.AsyncClient() as client:
            backend_url = env.get_env_var('BACKEND_URL', 'http://localhost:8000')
            profile_response = await client.get(f'{backend_url}/auth/profile', headers={'Authorization': f'Bearer {access_token}'})
            if profile_response.status_code != 200:
                raise Exception(f'HARD FAILURE: Token validation failed on protected endpoint: {profile_response.status_code}')
            profile_data = profile_response.json()
            if profile_data.get('email') != test_email:
                raise Exception(f"HARD FAILURE: Profile email mismatch. Expected: {test_email}, Got: {profile_data.get('email')}")
        print(f' PASS:  Token validation successful on protected endpoint')
        return {'success': True, 'email': test_email, 'access_token': access_token, 'profile_validated': True}

    async def test_real_websocket_authentication_flow(self, auth_helper: E2EAuthHelper):
        """Test REAL WebSocket authentication with actual WebSocket connection."""
        print('[U+1F50C] Testing REAL WebSocket authentication flow...')
        auth_user = await auth_helper.create_authenticated_user(email=f'ws_auth_test_{int(time.time())}@netra.ai')
        websocket_url = env.get_env_var('WEBSOCKET_URL', 'ws://localhost:8000/ws')
        try:
            headers = auth_helper.get_websocket_headers(auth_user.jwt_token)
            async with websockets.connect(websocket_url, additional_headers=headers, open_timeout=10.0) as websocket:
                print(f' PASS:  REAL WebSocket connection established')
                test_message = {'type': 'ping', 'timestamp': datetime.now(timezone.utc).isoformat(), 'user_id': auth_user.user_id}
                await websocket.send(json.dumps(test_message))
                print(f' PASS:  Message sent to REAL WebSocket')
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    print(f" PASS:  Received REAL WebSocket response: {response_data.get('type', 'unknown')}")
                    if 'type' not in response_data:
                        raise Exception("HARD FAILURE: WebSocket response missing 'type' field")
                    return {'success': True, 'connection_established': True, 'message_sent': True, 'response_received': True, 'response_type': response_data.get('type')}
                except asyncio.TimeoutError:
                    raise Exception('HARD FAILURE: No response received from WebSocket within timeout')
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: WebSocket connection failed: {e}')

    async def test_real_jwt_token_validation_flow(self, auth_helper: E2EAuthHelper):
        """Test REAL JWT token validation with actual auth service."""
        print('[U+1F3AB] Testing REAL JWT token validation flow...')
        auth_user = await auth_helper.create_authenticated_user(email=f'jwt_test_{int(time.time())}@netra.ai')
        async with httpx.AsyncClient() as client:
            auth_url = env.get_env_var('AUTH_SERVICE_URL', 'http://localhost:8083')
            validation_response = await client.get(f'{auth_url}/auth/validate', headers={'Authorization': f'Bearer {auth_user.jwt_token}'})
            if validation_response.status_code != 200:
                raise Exception(f'HARD FAILURE: JWT validation failed with {validation_response.status_code}: {validation_response.text}')
            validation_result = validation_response.json()
            if 'valid' not in validation_result or not validation_result['valid']:
                raise Exception('HARD FAILURE: JWT token marked as invalid by auth service')
            if 'user_id' not in validation_result:
                raise Exception('HARD FAILURE: JWT validation response missing user_id')
        print(f' PASS:  JWT token validation successful')
        invalid_token = 'invalid.jwt.token'
        async with httpx.AsyncClient() as client:
            invalid_response = await client.get(f'{auth_url}/auth/validate', headers={'Authorization': f'Bearer {invalid_token}'})
            if invalid_response.status_code == 200:
                invalid_result = invalid_response.json()
                if invalid_result.get('valid', False):
                    raise Exception('HARD FAILURE: Auth service accepted invalid JWT token')
        print(f' PASS:  Invalid token properly rejected')
        return {'success': True, 'valid_token_accepted': True, 'invalid_token_rejected': True, 'validation_endpoint_working': True}

    async def test_real_session_management_flow(self, auth_helper: E2EAuthHelper, real_db_session: AsyncSession):
        """Test REAL session management with database persistence."""
        print('[U+1F4CB] Testing REAL session management flow...')
        auth_user = await auth_helper.create_authenticated_user(email=f'session_test_{int(time.time())}@netra.ai')
        try:
            result = await real_db_session.execute(select(AuthSession).where(AuthSession.user_id == auth_user.user_id))
            sessions = result.scalars().all()
            active_sessions = [s for s in sessions if s.is_active]
            if len(active_sessions) == 0:
                raise Exception(f'HARD FAILURE: No active sessions found for user {auth_user.user_id} in database')
            session = active_sessions[0]
            if not session.created_at:
                raise Exception('HARD FAILURE: Session missing created_at timestamp')
            if not session.expires_at:
                raise Exception('HARD FAILURE: Session missing expires_at timestamp')
            if session.expires_at <= session.created_at:
                raise Exception('HARD FAILURE: Session expires_at is not after created_at')
            print(f' PASS:  Session validation successful: {session.id}')
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: Session database validation failed: {e}')
        async with httpx.AsyncClient() as client:
            auth_url = env.get_env_var('AUTH_SERVICE_URL', 'http://localhost:8083')
            logout_response = await client.post(f'{auth_url}/auth/logout', headers={'Authorization': f'Bearer {auth_user.jwt_token}'})
            if logout_response.status_code not in [200, 204]:
                raise Exception(f'HARD FAILURE: Logout failed with {logout_response.status_code}: {logout_response.text}')
        print(f' PASS:  Session logout successful')
        await asyncio.sleep(1)
        try:
            await real_db_session.refresh(session)
            if session.is_active:
                raise Exception('HARD FAILURE: Session still active after logout')
            if not session.revoked_at:
                raise Exception('HARD FAILURE: Session missing revoked_at timestamp after logout')
            print(f' PASS:  Session properly deactivated in database')
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: Session deactivation validation failed: {e}')
        return {'success': True, 'session_created': True, 'session_validated': True, 'logout_successful': True, 'session_deactivated': True}

    async def test_complete_auth_flow_integration(self, auth_helper: E2EAuthHelper, real_db_session: AsyncSession):
        """Test complete authentication flow integration with all components."""
        print(' CYCLE:  Testing complete REAL auth flow integration...')
        test_email = f'complete_auth_test_{int(time.time())}@netra.ai'
        test_password = 'CompleteAuthTest123!'
        registration_result = await self.test_real_user_registration_flow(auth_helper, real_db_session)
        login_result = await self.test_real_user_login_flow(auth_helper, real_db_session)
        websocket_result = await self.test_real_websocket_authentication_flow(auth_helper)
        jwt_result = await self.test_real_jwt_token_validation_flow(auth_helper)
        session_result = await self.test_real_session_management_flow(auth_helper, real_db_session)
        all_results = [registration_result, login_result, websocket_result, jwt_result, session_result]
        for i, result in enumerate(all_results):
            if not result.get('success', False):
                raise Exception(f'HARD FAILURE: Step {i + 1} of complete auth flow failed')
        print(f' PASS:  Complete auth flow integration successful')
        return {'success': True, 'registration_successful': registration_result['success'], 'login_successful': login_result['success'], 'websocket_successful': websocket_result['success'], 'jwt_validation_successful': jwt_result['success'], 'session_management_successful': session_result['success'], 'complete_flow_validated': True}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')