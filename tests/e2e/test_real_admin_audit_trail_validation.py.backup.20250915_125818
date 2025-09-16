"""REAL Admin Audit Trail E2E Test - NO MOCKS, NO CHEATING

BVJ (Business Value Justification):
1. Segment: Enterprise ($100K+ MRR)
2. Business Goal: Ensure audit trail compliance for Enterprise security
3. Value Impact: Required for regulatory compliance and security audits
4. Revenue Impact: Mandatory for Enterprise contracts and compliance certifications

REAL E2E TESTING APPROACH:
- Uses REAL database connections to auth_audit_logs table
- Performs REAL admin operations via HTTP API calls
- Validates ACTUAL audit entries created by admin operations
- FAILS HARD if any audit entries are missing or incorrect
- NO mocks, NO fake data, NO hardcoded success results

COMPLIANCE WITH CLAUDE.MD:
- "CHEATING ON TESTS = ABOMINATION" - This test is 100% real
- "Mocks in E2E = Abomination" - Zero mocks used
- "TESTS MUST RAISE ERRORS" - Hard failures for any audit problems
- Real authentication using SSOT e2e_auth_helper.py
- Real database queries to validate actual audit trail creation
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from auth_service.auth_core.database.models import AuthAuditLog, AuthUser
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
class TestRealAdminAuditTrailValidation:
    """REAL E2E Admin Audit Trail Validation - Zero Mocks, Zero Cheating.
    
    This test validates that ALL admin operations create proper audit entries
    in the REAL auth_audit_logs database table. It performs actual admin
    operations and verifies the audit trail using real database queries.
    """

    @pytest.fixture(scope='class', autouse=True)
    async def setup_docker_services(self):
        """Start REAL Docker services for audit trail testing."""
        print('[U+1F433] Starting Docker services for REAL audit trail tests...')
        services = ['backend', 'auth', 'postgres', 'redis']
        try:
            await docker_manager.start_services_async(services=services, health_check=True, timeout=120)
            await asyncio.sleep(5)
            print(' PASS:  Docker services ready for REAL audit trail tests')
            yield
        except Exception as e:
            raise Exception(f' FAIL:  HARD FAILURE: Failed to start Docker services for audit trail tests: {e}')
        finally:
            print('[U+1F9F9] Cleaning up Docker services after audit trail tests...')
            await docker_manager.cleanup_async()

    @pytest.fixture
    async def real_db_session(self) -> AsyncSession:
        """Get REAL database session for audit log queries."""
        async for session in get_request_scoped_db_session_for_fastapi():
            yield session

    @pytest.fixture
    async def auth_helper(self) -> E2EAuthHelper:
        """Get REAL authentication helper for admin operations."""
        return E2EAuthHelper()

    @pytest.fixture
    async def authenticated_admin(self, auth_helper: E2EAuthHelper) -> AuthenticatedUser:
        """Create REAL authenticated admin user for audit trail testing."""
        admin_user = await auth_helper.create_authenticated_user(email=f'admin_audit_test_{int(time.time())}@netra.ai', permissions=['admin', 'read', 'write'], user_id=f'admin-{int(time.time())}')
        return admin_user

    @pytest.fixture
    async def test_target_user(self, auth_helper: E2EAuthHelper) -> AuthenticatedUser:
        """Create REAL target user for admin operations."""
        target_user = await auth_helper.create_authenticated_user(email=f'audit_target_{int(time.time())}@netra.ai', permissions=['read', 'write'], user_id=f'target-{int(time.time())}')
        return target_user

    async def test_admin_users_view_creates_audit_entry(self, authenticated_admin: AuthenticatedUser, real_db_session: AsyncSession):
        """Test that admin viewing users creates REAL audit entry in database."""
        print(f' SEARCH:  Testing admin users view audit trail for admin: {authenticated_admin.email}')
        baseline_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        print(f' CHART:  Baseline audit entries for admin: {baseline_count}')
        async with httpx.AsyncClient() as client:
            backend_url = env.get_env_var('BACKEND_URL', 'http://localhost:8000')
            response = await client.get(f'{backend_url}/admin/users', headers={'Authorization': f'Bearer {authenticated_admin.jwt_token}'})
        if response.status_code != 200:
            raise Exception(f'HARD FAILURE: Admin users view failed with {response.status_code}: {response.text}')
        print(f' PASS:  Admin users view successful: {response.status_code}')
        await asyncio.sleep(2)
        new_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        if new_count <= baseline_count:
            raise Exception(f'HARD FAILURE: No audit entry created for admin users view. Before: {baseline_count}, After: {new_count}')
        audit_entry = await self._get_latest_audit_entry_for_user(real_db_session, authenticated_admin.user_id)
        if not audit_entry:
            raise Exception('HARD FAILURE: Could not retrieve latest audit entry from database')
        self._validate_audit_entry_structure(audit_entry, 'ADMIN_USERS_VIEWED')
        print(f' PASS:  REAL audit entry validated: {audit_entry.event_type} at {audit_entry.created_at}')

    async def test_admin_user_suspend_creates_audit_entry(self, authenticated_admin: AuthenticatedUser, test_target_user: AuthenticatedUser, real_db_session: AsyncSession):
        """Test that admin suspending user creates REAL audit entry in database."""
        print(f'[U+23F8][U+FE0F] Testing admin user suspend audit trail for admin: {authenticated_admin.email}')
        baseline_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        async with httpx.AsyncClient() as client:
            backend_url = env.get_env_var('BACKEND_URL', 'http://localhost:8000')
            response = await client.post(f'{backend_url}/admin/users/suspend', json={'user_id': test_target_user.user_id}, headers={'Authorization': f'Bearer {authenticated_admin.jwt_token}'})
        if response.status_code not in [200, 201]:
            raise Exception(f'HARD FAILURE: Admin user suspend failed with {response.status_code}: {response.text}')
        print(f' PASS:  Admin user suspend successful: {response.status_code}')
        await asyncio.sleep(2)
        new_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        if new_count <= baseline_count:
            raise Exception(f'HARD FAILURE: No audit entry created for admin user suspend. Before: {baseline_count}, After: {new_count}')
        audit_entry = await self._get_latest_audit_entry_for_user(real_db_session, authenticated_admin.user_id)
        self._validate_audit_entry_structure(audit_entry, 'ADMIN_USER_SUSPENDED')
        if audit_entry.event_metadata:
            metadata = audit_entry.event_metadata
            if 'target_user_id' not in metadata:
                raise Exception('HARD FAILURE: Audit entry missing target_user_id in metadata')
        print(f' PASS:  REAL audit entry validated for user suspend: {audit_entry.event_type}')

    async def test_admin_user_reactivate_creates_audit_entry(self, authenticated_admin: AuthenticatedUser, test_target_user: AuthenticatedUser, real_db_session: AsyncSession):
        """Test that admin reactivating user creates REAL audit entry in database."""
        print(f'[U+25B6][U+FE0F] Testing admin user reactivate audit trail for admin: {authenticated_admin.email}')
        baseline_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        async with httpx.AsyncClient() as client:
            backend_url = env.get_env_var('BACKEND_URL', 'http://localhost:8000')
            response = await client.post(f'{backend_url}/admin/users/reactivate', json={'user_id': test_target_user.user_id}, headers={'Authorization': f'Bearer {authenticated_admin.jwt_token}'})
        if response.status_code not in [200, 201]:
            raise Exception(f'HARD FAILURE: Admin user reactivate failed with {response.status_code}: {response.text}')
        print(f' PASS:  Admin user reactivate successful: {response.status_code}')
        await asyncio.sleep(2)
        new_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        if new_count <= baseline_count:
            raise Exception(f'HARD FAILURE: No audit entry created for admin user reactivate. Before: {baseline_count}, After: {new_count}')
        audit_entry = await self._get_latest_audit_entry_for_user(real_db_session, authenticated_admin.user_id)
        self._validate_audit_entry_structure(audit_entry, 'ADMIN_USER_REACTIVATED')
        print(f' PASS:  REAL audit entry validated for user reactivate: {audit_entry.event_type}')

    async def test_complete_admin_audit_trail_validation(self, authenticated_admin: AuthenticatedUser, test_target_user: AuthenticatedUser, real_db_session: AsyncSession):
        """Test complete admin audit trail by performing multiple operations."""
        print(f' CYCLE:  Testing complete admin audit trail validation for: {authenticated_admin.email}')
        baseline_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        backend_url = env.get_env_var('BACKEND_URL', 'http://localhost:8000')
        headers = {'Authorization': f'Bearer {authenticated_admin.jwt_token}'}
        operations = [('GET', f'{backend_url}/admin/users', None, 'ADMIN_USERS_VIEWED'), ('POST', f'{backend_url}/admin/users/suspend', {'user_id': test_target_user.user_id}, 'ADMIN_USER_SUSPENDED'), ('POST', f'{backend_url}/admin/users/reactivate', {'user_id': test_target_user.user_id}, 'ADMIN_USER_REACTIVATED')]
        async with httpx.AsyncClient() as client:
            for method, url, json_data, expected_event in operations:
                if method == 'GET':
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, json=json_data, headers=headers)
                if response.status_code not in [200, 201]:
                    raise Exception(f'HARD FAILURE: Operation {method} {url} failed with {response.status_code}: {response.text}')
                print(f' PASS:  Operation successful: {method} {url} -> {response.status_code}')
                await asyncio.sleep(1)
        await asyncio.sleep(3)
        final_count = await self._count_audit_entries_for_user(real_db_session, authenticated_admin.user_id)
        expected_new_entries = len(operations)
        actual_new_entries = final_count - baseline_count
        if actual_new_entries < expected_new_entries:
            raise Exception(f'HARD FAILURE: Not all admin operations created audit entries. Expected: {expected_new_entries}, Actual: {actual_new_entries}')
        recent_entries = await self._get_recent_audit_entries_for_user(real_db_session, authenticated_admin.user_id, expected_new_entries)
        expected_event_types = [op[3] for op in operations]
        actual_event_types = [entry.event_type for entry in recent_entries]
        for expected_type in expected_event_types:
            if expected_type not in actual_event_types:
                raise Exception(f'HARD FAILURE: Missing audit entry for {expected_type} - admin operation was not logged!')
        print(f' PASS:  Complete admin audit trail validated: {len(recent_entries)} entries created')
        print(f'   Event types: {actual_event_types}')
        return {'success': True, 'operations_performed': len(operations), 'audit_entries_created': len(recent_entries), 'event_types_logged': actual_event_types}

    async def test_audit_trail_performance_validation(self, authenticated_admin: AuthenticatedUser, real_db_session: AsyncSession):
        """Test REAL audit trail performance with database timing."""
        print(f'[U+23F1][U+FE0F] Testing audit trail performance for admin: {authenticated_admin.email}')
        start_time = time.time()
        try:
            result = await real_db_session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == authenticated_admin.user_id).order_by(AuthAuditLog.created_at.desc()).limit(100))
            audit_entries = list(result.scalars().all())
            query_time = time.time() - start_time
            if query_time > 2.0:
                raise Exception(f'HARD FAILURE: Audit query too slow: {query_time:.3f}s (max: 2.0s)')
            print(f' PASS:  Audit query performance validated: {query_time:.3f}s for {len(audit_entries)} entries')
            return {'success': True, 'query_time_seconds': query_time, 'entries_queried': len(audit_entries), 'performance_acceptable': query_time < 2.0}
        except Exception as e:
            if 'HARD FAILURE' in str(e):
                raise
            else:
                raise Exception(f'HARD FAILURE: Audit performance test failed: {e}')

    async def _count_audit_entries_for_user(self, session: AsyncSession, user_id: str) -> int:
        """Count REAL audit entries for a user in the database."""
        try:
            result = await session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == user_id))
            entries = result.scalars().all()
            return len(entries)
        except Exception as e:
            raise Exception(f'HARD FAILURE: Failed to count audit entries: {e}')

    async def _get_latest_audit_entry_for_user(self, session: AsyncSession, user_id: str) -> Optional[AuthAuditLog]:
        """Get the latest REAL audit entry for a user from database."""
        try:
            result = await session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == user_id).order_by(AuthAuditLog.created_at.desc()).limit(1))
            return result.scalar_one_or_none()
        except Exception as e:
            raise Exception(f'HARD FAILURE: Failed to get latest audit entry: {e}')

    async def _get_recent_audit_entries_for_user(self, session: AsyncSession, user_id: str, limit: int) -> List[AuthAuditLog]:
        """Get recent REAL audit entries for a user from database."""
        try:
            result = await session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == user_id).order_by(AuthAuditLog.created_at.desc()).limit(limit))
            return list(result.scalars().all())
        except Exception as e:
            raise Exception(f'HARD FAILURE: Failed to get recent audit entries: {e}')

    def _validate_audit_entry_structure(self, audit_entry: AuthAuditLog, expected_event_type: str) -> None:
        """Validate REAL audit entry structure - HARD FAILURE if invalid."""
        if not audit_entry.id:
            raise Exception("HARD FAILURE: Audit entry missing required 'id' field")
        if not audit_entry.event_type:
            raise Exception("HARD FAILURE: Audit entry missing required 'event_type' field")
        if not audit_entry.user_id:
            raise Exception("HARD FAILURE: Audit entry missing required 'user_id' field")
        if not audit_entry.created_at:
            raise Exception("HARD FAILURE: Audit entry missing required 'created_at' field")
        if audit_entry.event_type != expected_event_type:
            raise Exception(f'HARD FAILURE: Audit entry event type mismatch. Expected: {expected_event_type}, Actual: {audit_entry.event_type}')
        time_since_creation = datetime.now(timezone.utc) - audit_entry.created_at.replace(tzinfo=timezone.utc)
        if time_since_creation.total_seconds() > 300:
            raise Exception(f'HARD FAILURE: Audit entry timestamp too old: {audit_entry.created_at}')
        print(f' PASS:  Audit entry structure validated: {audit_entry.event_type} at {audit_entry.created_at}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')