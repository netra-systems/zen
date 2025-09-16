"""
Category 5: Security and Permissions Enforcement Test Suite

Comprehensive security testing for the Netra Apex platform covering:
1. Tenant isolation and IDOR prevention
2. Admin tool authorization
3. Tier-based feature gating
4. JWT security and token validation
5. PII and secret protection

Business Value Justification (BVJ):
- Segment: Enterprise, Mid, Early
- Business Goal: Risk Reduction, Compliance, Trust
- Value Impact: Prevents data breaches, ensures tenant isolation, enables enterprise adoption
- Revenue Impact: Critical for enterprise sales, compliance requirements, regulatory adherence
"""
import asyncio
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment
import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from netra_backend.app.agents.admin_tool_permissions import AdminToolPermissionManager
from netra_backend.app.db.models_postgres import Secret, ToolUsageLog, User
from netra_backend.app.services.permission_service import PermissionService
from tests.clients.auth_client import AuthTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient

@pytest.mark.e2e
class TestTenantIsolation:
    """Test 1: Tenant Isolation and IDOR Prevention
    
    Critical security test ensuring users cannot access data belonging to other tenants.
    Validates defense against Insecure Direct Object Reference (IDOR) attacks.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_user_data_isolation_comprehensive(self, db_session: Session, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test comprehensive user data isolation across all endpoints"""
        user1_data = {'email': f'tenant1_user_{uuid.uuid4()}@test.com', 'full_name': 'Tenant 1 User', 'plan_tier': 'pro', 'role': 'standard_user'}
        user2_data = {'email': f'tenant2_user_{uuid.uuid4()}@test.com', 'full_name': 'Tenant 2 User', 'plan_tier': 'enterprise', 'role': 'standard_user'}
        user1_token = await auth_client.create_test_user(user1_data)
        user2_token = await auth_client.create_test_user(user2_data)
        user1_headers = {'Authorization': f'Bearer {user1_token}'}
        user2_headers = {'Authorization': f'Bearer {user2_token}'}
        user1_id = jwt.decode(user1_token, options={'verify_signature': False})['sub']
        user2_id = jwt.decode(user2_token, options={'verify_signature': False})['sub']
        user1_profile = await backend_client.get('/api/users/profile', headers=user1_headers)
        assert user1_profile.status_code == 200
        idor_attempt = await backend_client.get(f'/api/users/{user2_id}', headers=user1_headers)
        assert idor_attempt.status_code in [403, 404], "IDOR vulnerability: User can access other user's data"
        thread_data = {'title': 'Confidential Project Data', 'type': 'analysis'}
        user1_thread = await backend_client.post('/api/threads', json=thread_data, headers=user1_headers)
        assert user1_thread.status_code == 201
        thread1_id = user1_thread.json()['id']
        thread_access_attempt = await backend_client.get(f'/api/threads/{thread1_id}', headers=user2_headers)
        assert thread_access_attempt.status_code in [403, 404], 'Thread isolation failure'
        message_data = {'content': 'Sensitive business information', 'role': 'user'}
        user1_message = await backend_client.post(f'/api/threads/{thread1_id}/messages', json=message_data, headers=user1_headers)
        assert user1_message.status_code == 201
        messages_attempt = await backend_client.get(f'/api/threads/{thread1_id}/messages', headers=user2_headers)
        assert messages_attempt.status_code in [403, 404], 'Message isolation failure'
        workspace_data = {'name': 'Private Workspace', 'description': 'Confidential'}
        user1_workspace = await backend_client.post('/api/workspaces', json=workspace_data, headers=user1_headers)
        if user1_workspace.status_code == 201:
            workspace_id = user1_workspace.json()['id']
            workspace_access_attempt = await backend_client.get(f'/api/workspaces/{workspace_id}', headers=user2_headers)
            assert workspace_access_attempt.status_code in [403, 404], 'Workspace isolation failure'
        search_response = await backend_client.get('/api/search?q=confidential', headers=user2_headers)
        if search_response.status_code == 200:
            results = search_response.json()
            for result in results.get('items', []):
                assert result.get('user_id') != user1_id, 'Search result isolation failure'
        audit_logs = await backend_client.get('/api/admin/audit-logs', headers=user1_headers)
        if audit_logs.status_code == 200:
            logs = audit_logs.json()
            for log in logs.get('items', []):
                assert log.get('user_id') == user1_id, 'Audit log isolation failure'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_tenant_isolation(self, auth_client: AuthTestClient, websocket_client: WebSocketTestClient):
        """Test tenant isolation in WebSocket connections"""
        user1_token = await auth_client.create_test_user({'email': f'ws_user1_{uuid.uuid4()}@test.com', 'plan_tier': 'pro'})
        user2_token = await auth_client.create_test_user({'email': f'ws_user2_{uuid.uuid4()}@test.com', 'plan_tier': 'enterprise'})
        ws1 = await websocket_client.connect(token=user1_token)
        ws2 = await websocket_client.connect(token=user2_token)
        await ws1.send_json({'type': 'agent_request', 'data': {'query': 'Confidential analysis request'}})
        await asyncio.sleep(1)
        messages_user2 = await websocket_client.get_received_messages(ws2)
        for message in messages_user2:
            assert 'Confidential analysis request' not in str(message), 'WebSocket tenant isolation failure'
        await ws1.close()
        await ws2.close()

@pytest.mark.e2e
class TestAdminToolAuthorization:
    """Test 2: Admin Tool Authorization
    
    Validates proper access control for administrative functions including
    role-based permissions and audit trail generation.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_admin_tool_permission_enforcement(self, db_session: Session, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test admin tool permission enforcement across different roles"""
        standard_user = await auth_client.create_test_user({'email': f'standard_{uuid.uuid4()}@test.com', 'role': 'standard_user', 'plan_tier': 'pro'})
        developer_user = await auth_client.create_test_user({'email': f'developer_{uuid.uuid4()}@test.com', 'role': 'developer', 'plan_tier': 'enterprise', 'is_developer': True})
        admin_user = await auth_client.create_test_user({'email': f'admin_{uuid.uuid4()}@test.com', 'role': 'admin', 'plan_tier': 'enterprise', 'permissions': {'system_admin': True, 'user_management': True}})
        standard_headers = {'Authorization': f'Bearer {standard_user}'}
        developer_headers = {'Authorization': f'Bearer {developer_user}'}
        admin_headers = {'Authorization': f'Bearer {admin_user}'}
        corpus_data = {'name': 'Test Corpus', 'description': 'Test data'}
        standard_corpus = await backend_client.post('/api/admin/corpus', json=corpus_data, headers=standard_headers)
        assert standard_corpus.status_code in [403, 401], 'Standard user should not access admin corpus tools'
        developer_corpus = await backend_client.post('/api/admin/corpus', json=corpus_data, headers=developer_headers)
        admin_corpus = await backend_client.post('/api/admin/corpus', json=corpus_data, headers=admin_headers)
        user_update_data = {'role': 'power_user'}
        test_user_id = str(uuid.uuid4())
        standard_user_mgmt = await backend_client.put(f'/api/admin/users/{test_user_id}', json=user_update_data, headers=standard_headers)
        assert standard_user_mgmt.status_code in [403, 401], 'Standard user should not access user management'
        system_config = {'feature_flags': {'new_ui': True}}
        standard_config = await backend_client.post('/api/admin/system/config', json=system_config, headers=standard_headers)
        assert standard_config.status_code in [403, 401], 'Standard user should not access system config'
        developer_config = await backend_client.post('/api/admin/system/config', json=system_config, headers=developer_headers)
        log_query = {'level': 'ERROR', 'last_hours': 24}
        standard_logs = await backend_client.post('/api/admin/logs/analyze', json=log_query, headers=standard_headers)
        assert standard_logs.status_code in [403, 401], 'Standard user should not access log analyzer'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_admin_permission_inheritance_and_delegation(self, db_session: Session):
        """Test complex permission inheritance and delegation scenarios"""
        user = User(id=str(uuid.uuid4()), email=f'mixed_perms_{uuid.uuid4()}@test.com', role='power_user', plan_tier='enterprise', permissions={'corpus_write': True, 'synthetic_generate': False, 'user_management': True, 'system_admin': False}, tool_permissions={'corpus_manager': {'enabled': True, 'max_size': 1000}, 'user_admin': {'enabled': True, 'scope': 'department'}})
        db_session.add(user)
        db_session.commit()
        permission_manager = AdminToolPermissionManager(db_session, user)
        available_tools = permission_manager.get_available_tools()
        assert 'corpus_manager' in available_tools, 'User should have corpus manager access'
        assert 'user_admin' in available_tools, 'User should have user admin access'
        assert 'synthetic_generator' not in available_tools, 'User should not have synthetic generator access'
        assert 'system_configurator' not in available_tools, 'User should not have system config access'
        corpus_access = permission_manager.validate_tool_access('corpus_manager')
        assert corpus_access, 'User should have corpus manager access'
        synthetic_access = permission_manager.validate_tool_access('synthetic_generator')
        assert not synthetic_access, 'User should not have synthetic generator access'
        permission_check = permission_manager.create_permission_check('user_admin')
        assert permission_check.has_access, 'User should have user admin access'
        assert 'user_management' in permission_check.required_permissions
        assert len(permission_check.missing_permissions) == 0
        tools_to_check = ['corpus_manager', 'user_admin', 'synthetic_generator', 'system_configurator']
        bulk_results = permission_manager.validate_bulk_access(tools_to_check)
        assert bulk_results['corpus_manager'] == True
        assert bulk_results['user_admin'] == True
        assert bulk_results['synthetic_generator'] == False
        assert bulk_results['system_configurator'] == False

class CustomerTierBasedFeatureGating:
    """Test 3: Tier-Based Feature Gating
    
    Ensures features are properly restricted by subscription tier and usage quotas
    are enforced according to business rules.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_feature_availability_by_subscription_tier(self, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test feature access based on subscription tier"""
        free_user = await auth_client.create_test_user({'email': f'free_{uuid.uuid4()}@test.com', 'plan_tier': 'free', 'role': 'standard_user'})
        pro_user = await auth_client.create_test_user({'email': f'pro_{uuid.uuid4()}@test.com', 'plan_tier': 'pro', 'role': 'standard_user'})
        enterprise_user = await auth_client.create_test_user({'email': f'enterprise_{uuid.uuid4()}@test.com', 'plan_tier': 'enterprise', 'role': 'standard_user'})
        free_headers = {'Authorization': f'Bearer {free_user}'}
        pro_headers = {'Authorization': f'Bearer {pro_user}'}
        enterprise_headers = {'Authorization': f'Bearer {enterprise_user}'}
        advanced_agent_request = {'query': 'Complex analysis request', 'options': {'use_advanced_models': True, 'enable_custom_tools': True, 'parallel_processing': True}}
        free_advanced = await backend_client.post('/api/agents/advanced', json=advanced_agent_request, headers=free_headers)
        assert free_advanced.status_code in [403, 402, 429], 'Free tier should not access advanced features'
        pro_advanced = await backend_client.post('/api/agents/advanced', json=advanced_agent_request, headers=pro_headers)
        enterprise_advanced = await backend_client.post('/api/agents/advanced', json=advanced_agent_request, headers=enterprise_headers)
        session_requests = []
        for i in range(5):
            session_data = {'type': 'analysis', 'title': f'Session {i}'}
            session_request = backend_client.post('/api/sessions', json=session_data, headers=free_headers)
            session_requests.append(session_request)
        session_responses = await asyncio.gather(*session_requests, return_exceptions=True)
        successful_sessions = [r for r in session_responses if hasattr(r, 'status_code') and r.status_code == 201]
        assert len(successful_sessions) <= 3, 'Free tier should have session limits'
        rapid_requests = []
        for i in range(20):
            rapid_request = backend_client.get('/api/agents/status', headers=free_headers)
            rapid_requests.append(rapid_request)
        rate_responses = await asyncio.gather(*rapid_requests, return_exceptions=True)
        rate_limited = [r for r in rate_responses if hasattr(r, 'status_code') and r.status_code == 429]
        assert len(rate_limited) > 0, 'Free tier should encounter rate limiting'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_usage_quota_enforcement_and_billing(self, db_session: Session, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test usage quota enforcement and accurate billing tracking"""
        pro_user_token = await auth_client.create_test_user({'email': f'quota_test_{uuid.uuid4()}@test.com', 'plan_tier': 'pro', 'feature_flags': {'monthly_agent_requests': 1000, 'monthly_tokens': 50000, 'concurrent_sessions': 3}})
        pro_headers = {'Authorization': f'Bearer {pro_user_token}'}
        user_id = jwt.decode(pro_user_token, options={'verify_signature': False})['sub']
        agent_request = {'query': 'Generate a detailed analysis report', 'options': {'detailed': True, 'include_sources': True}}
        for i in range(5):
            response = await backend_client.post('/api/agents/analyze', json=agent_request, headers=pro_headers)
        usage_logs = db_session.query(ToolUsageLog).filter(ToolUsageLog.user_id == user_id, ToolUsageLog.tool_name == 'agent_analyzer').all()
        total_tokens = sum((log.tokens_used or 0 for log in usage_logs))
        total_cost = sum((log.cost_cents or 0 for log in usage_logs))
        assert total_tokens > 0, 'Token usage should be tracked'
        assert total_cost > 0, 'Cost should be calculated'
        high_usage_log = ToolUsageLog(id=str(uuid.uuid4()), user_id=user_id, tool_name='agent_analyzer', tokens_used=45000, cost_cents=2250, status='success', plan_tier='pro', created_at=datetime.now(timezone.utc))
        db_session.add(high_usage_log)
        db_session.commit()
        quota_test_response = await backend_client.post('/api/agents/analyze', json=agent_request, headers=pro_headers)
        if quota_test_response.status_code == 429:
            error_data = quota_test_response.json()
            assert 'quota' in error_data.get('detail', '').lower()
        elif quota_test_response.status_code == 402:
            error_data = quota_test_response.json()
            assert 'upgrade' in error_data.get('detail', '').lower()

@pytest.mark.e2e
class TestJWTSecurity:
    """Test 4: JWT Security and Token Validation
    
    Validates JWT security implementation including signature validation,
    expiration enforcement, and tampering detection.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_tampering_detection_comprehensive(self, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test comprehensive JWT tampering detection"""
        valid_token = await auth_client.create_test_user({'email': f'jwt_test_{uuid.uuid4()}@test.com', 'plan_tier': 'pro'})
        header, payload, signature = valid_token.split('.')
        decoded_payload = json.loads(jwt.utils.base64url_decode(payload + '=='))
        decoded_payload['role'] = 'admin'
        decoded_payload['plan_tier'] = 'enterprise'
        tampered_payload = jwt.utils.base64url_encode(json.dumps(decoded_payload).encode())
        tampered_token = f'{header}.{tampered_payload}.{signature}'
        tampered_headers = {'Authorization': f'Bearer {tampered_token}'}
        tampered_response = await backend_client.get('/api/users/profile', headers=tampered_headers)
        assert tampered_response.status_code in [401, 403], 'Tampered JWT should be rejected'
        expired_payload = decoded_payload.copy()
        expired_payload['exp'] = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        expired_payload_encoded = jwt.utils.base64url_encode(json.dumps(expired_payload).encode())
        expired_token = f'{header}.{expired_payload_encoded}.{signature}'
        expired_headers = {'Authorization': f'Bearer {expired_token}'}
        expired_response = await backend_client.get('/api/users/profile', headers=expired_headers)
        assert expired_response.status_code in [401, 403], 'Expired JWT should be rejected'
        none_header = {'alg': 'none', 'typ': 'JWT'}
        none_header_encoded = jwt.utils.base64url_encode(json.dumps(none_header).encode())
        none_token = f'{none_header_encoded}.{payload}.'
        none_headers = {'Authorization': f'Bearer {none_token}'}
        none_response = await backend_client.get('/api/users/profile', headers=none_headers)
        assert none_response.status_code in [401, 403], "JWT with 'none' algorithm should be rejected"
        minimal_payload = {'sub': str(uuid.uuid4())}
        minimal_payload_encoded = jwt.utils.base64url_encode(json.dumps(minimal_payload).encode())
        minimal_token = f'{header}.{minimal_payload_encoded}.{signature}'
        minimal_headers = {'Authorization': f'Bearer {minimal_token}'}
        minimal_response = await backend_client.get('/api/users/profile', headers=minimal_headers)
        assert minimal_response.status_code in [401, 403], 'JWT with missing claims should be rejected'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_service_token_validation_consistency(self, auth_client: AuthTestClient):
        """Test token validation consistency across different services"""
        valid_token = await auth_client.create_test_user({'email': f'cross_service_{uuid.uuid4()}@test.com', 'plan_tier': 'enterprise'})
        services_to_test = [('auth_service', 'http://localhost:8001'), ('backend', 'http://localhost:8000'), ('websocket', 'ws://localhost:8000/ws')]
        validation_results = {}
        for service_name, base_url in services_to_test:
            if service_name == 'websocket':
                try:
                    import websockets
                    uri = f'{base_url}?token={valid_token}'
                    async with websockets.connect(uri) as websocket:
                        validation_results[service_name] = 'valid'
                        await websocket.close()
                except Exception:
                    validation_results[service_name] = 'invalid'
            else:
                headers = {'Authorization': f'Bearer {valid_token}'}
                try:
                    if service_name == 'auth_service':
                        async with httpx.AsyncClient(follow_redirects=True) as client:
                            response = await client.get(f'{base_url}/validate', headers=headers)
                            validation_results[service_name] = 'valid' if response.status_code == 200 else 'invalid'
                    else:
                        async with httpx.AsyncClient(follow_redirects=True) as client:
                            response = await client.get(f'{base_url}/api/users/profile', headers=headers)
                            validation_results[service_name] = 'valid' if response.status_code == 200 else 'invalid'
                except Exception:
                    validation_results[service_name] = 'invalid'
        unique_results = set(validation_results.values())
        assert len(unique_results) == 1, f'Inconsistent token validation across services: {validation_results}'

@pytest.mark.e2e
class TestPIISecretProtection:
    """Test 5: PII and Secret Protection
    
    Ensures sensitive data is properly encrypted, masked in logs,
    and transmitted securely according to compliance requirements.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sensitive_data_encryption_and_storage(self, db_session: Session, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test encryption of sensitive data at rest and in transit"""
        user_token = await auth_client.create_test_user({'email': f'pii_test_{uuid.uuid4()}@test.com', 'full_name': 'John Doe', 'plan_tier': 'enterprise'})
        user_headers = {'Authorization': f'Bearer {user_token}'}
        user_id = jwt.decode(user_token, options={'verify_signature': False})['sub']
        secret_data = {'key': 'api_key_openai', 'value': 'sk-1234567890abcdef1234567890abcdef', 'description': 'OpenAI API Key'}
        secret_response = await backend_client.post('/api/secrets', json=secret_data, headers=user_headers)
        assert secret_response.status_code == 201, 'Secret storage should succeed'
        stored_secret = db_session.query(Secret).filter(Secret.user_id == user_id, Secret.key == secret_data['key']).first()
        assert stored_secret is not None, 'Secret should be stored'
        assert stored_secret.encrypted_value != secret_data['value'], 'Secret should be encrypted'
        assert 'sk-' not in stored_secret.encrypted_value, 'Plaintext should not be visible'
        pii_update = {'full_name': 'Jane Smith', 'bio': 'Software engineer with SSN: 123-45-6789', 'phone': '+1-555-123-4567', 'address': '123 Main St, Anytown, USA 12345'}
        profile_response = await backend_client.put('/api/users/profile', json=pii_update, headers=user_headers)
        if profile_response.status_code == 200:
            updated_user = db_session.query(User).filter(User.id == user_id).first()
            if hasattr(updated_user, 'bio') and updated_user.bio:
                assert '123-45-6789' not in updated_user.bio, 'SSN should be masked or removed'
        profile_get = await backend_client.get('/api/users/profile', headers=user_headers)
        if profile_get.status_code == 200:
            profile_data = profile_get.json()
            if 'phone' in profile_data:
                phone = profile_data['phone']
                assert '*' in phone or phone.endswith('****'), 'Phone should be partially masked'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_logging_sanitization_and_audit_compliance(self, auth_client: AuthTestClient, backend_client: BackendTestClient):
        """Test PII masking in logs and audit trail compliance"""
        user_token = await auth_client.create_test_user({'email': f'audit_test_{uuid.uuid4()}@test.com', 'full_name': 'Test User', 'plan_tier': 'pro'})
        user_headers = {'Authorization': f'Bearer {user_token}'}
        sensitive_request = {'query': 'Analyze customer data for John Smith (SSN: 987-65-4321)', 'context': {'customer_email': 'john.smith@company.com', 'credit_card': '4111-1111-1111-1111', 'api_key': 'sk-sensitive123456789'}}
        log_response = await backend_client.post('/api/agents/analyze', json=sensitive_request, headers=user_headers)
        audit_response = await backend_client.get('/api/admin/audit-logs', headers=user_headers)
        if audit_response.status_code == 200:
            audit_logs = audit_response.json()
            for log_entry in audit_logs.get('entries', []):
                log_content = str(log_entry)
                assert '987-65-4321' not in log_content, 'SSN should be masked in logs'
                assert '4111-1111-1111-1111' not in log_content, 'Credit card should be masked in logs'
                assert 'sk-sensitive123456789' not in log_content, 'API key should be masked in logs'
                pii_patterns = ['***-**-****', '****-****-****', 'sk-***']
                has_masking = any((pattern in log_content for pattern in pii_patterns))
        malicious_input = {'query': "'; DROP TABLE users; SELECT * FROM secrets WHERE key LIKE '%api%';", 'ssn': '111-22-3333', 'password': 'supersecret123'}
        error_response = await backend_client.post('/api/agents/analyze', json=malicious_input, headers=user_headers)
        if error_response.status_code >= 400:
            error_data = error_response.json()
            error_message = str(error_data)
            assert 'supersecret123' not in error_message, 'Password should not appear in error messages'
            assert '111-22-3333' not in error_message, 'SSN should not appear in error messages'
            assert 'DROP TABLE' not in error_message, 'SQL injection attempts should be sanitized'
        compliance_actions = [('profile_update', {'full_name': 'Updated Name'}), ('secret_create', {'key': 'test_key'}), ('data_export', {'format': 'json'}), ('account_delete', {'confirm': True})]
        for action, data in compliance_actions:
            action_response = await backend_client.post(f'/api/users/{action}', json=data, headers=user_headers)
            assert action_response.status_code != 500, f'Action {action} should not cause server error'

@pytest.fixture
async def auth_client():
    """Create authenticated test client"""
    return AuthTestClient(base_url='http://localhost:8001')

@pytest.fixture
async def backend_client():
    """Create backend test client"""
    return BackendTestClient(base_url='http://localhost:8000')

@pytest.fixture
async def websocket_client():
    """Create WebSocket test client"""
    return WebSocketTestClient(base_url='ws://localhost:8000')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')