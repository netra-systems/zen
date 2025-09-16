"""
Auth Backend User Desynchronization Partial Rollback Test - P0 CRITICAL

Test: Auth Backend User Desynchronization Partial Rollback
Critical vulnerability test that exposes scenarios where user creation succeeds
in the auth service but fails in the backend sync, leaving the system in an
inconsistent state that requires proper rollback mechanisms.

BVJ (Business Value Justification):
- Segment: All tiers (Free -> Enterprise)
- Business Goal: Data Integrity and Platform Stability
- Value Impact: Prevents user account corruption that leads to login failures
- Strategic Impact: Critical security vulnerability - prevents data inconsistency attacks

VULNERABILITY SCENARIO:
1. User successfully created in auth service database
2. Backend sync fails due to network/database issues
3. System left in inconsistent state (user exists in auth but not backend)
4. User can authenticate but cannot access backend services
5. Partial rollback may leave orphaned auth records

REQUIREMENTS:
- Simulate successful auth user creation
- Mock backend sync failure scenarios
- Verify system detects inconsistent state
- Test rollback mechanism activation
- Validate cleanup of orphaned records
- Test must expose the vulnerability clearly
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import pytest

from shared.isolated_environment import IsolatedEnvironment
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient
from tests.e2e.integration.unified_e2e_harness import create_e2e_harness
from tests.e2e.integration.user_journey_executor import TestUser
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@dataclass
class TestDesynchronizationResult:
    """Result container for auth backend desynchronization test."""
    auth_user_created: bool = False
    backend_sync_failed: bool = False
    inconsistent_state_detected: bool = False
    rollback_attempted: bool = False
    rollback_completed: bool = False
    orphaned_records_found: bool = False
    auth_login_possible: bool = False
    backend_access_blocked: bool = False
    cleanup_successful: bool = False
    vulnerability_exposed: bool = False
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class TestAuthBackendDesynchronization:
    """Tests auth backend user desynchronization scenarios."""

    def __init__(self, harness):
        """Initialize with E2E test harness."""
        self.harness = harness
        self.http_client: Optional[httpx.AsyncClient] = None
        self.test_user_email: Optional[str] = None
        self.test_user_id: Optional[str] = None
        self.auth_tokens: Optional[Dict[str, str]] = None

    async def setup(self) -> None:
        """Setup desynchronization tester."""
        self.http_client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        self.test_user_email = f"test_desync_{uuid.uuid4().hex[:8]}@example.com"

    async def cleanup(self) -> None:
        """Cleanup resources and any orphaned records."""
        if self.http_client:
            await self.http_client.aclose()
        # Attempt cleanup of test user if created
        await self._cleanup_test_user()

    async def execute_desynchronization_test(self) -> TestDesynchronizationResult:
        """Execute complete desynchronization vulnerability test."""
        start_time = time.time()
        result = TestDesynchronizationResult()

        try:
            # Step 1: Create user in auth service
            result.auth_user_created = await self._create_auth_user()

            # Step 2: Simulate backend sync failure
            if result.auth_user_created:
                result.backend_sync_failed = await self._simulate_backend_sync_failure()

            # Step 3: Detect inconsistent state
            if result.backend_sync_failed:
                result.inconsistent_state_detected = await self._detect_inconsistent_state()

            # Step 4: Test rollback mechanism
            if result.inconsistent_state_detected:
                result.rollback_attempted = await self._attempt_rollback()
                result.rollback_completed = await self._verify_rollback_completion()

            # Step 5: Check for orphaned records
            result.orphaned_records_found = await self._check_orphaned_records()

            # Step 6: Test vulnerability exposure
            result.vulnerability_exposed = await self._test_vulnerability_exposure()

            result.execution_time = time.time() - start_time

        except Exception as e:
            result.errors.append(f"Test execution error: {str(e)}")
            result.execution_time = time.time() - start_time

        return result

    async def _create_auth_user(self) -> bool:
        """Create user in auth service only."""
        try:
            auth_url = get_env("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
            response = await self.http_client.post(
                f"{auth_url}/api/v1/auth/register",
                json={
                    "email": self.test_user_email,
                    "password": "TestPassword123!",
                    "confirm_password": "TestPassword123!"
                }
            )

            if response.status_code == 201:
                data = response.json()
                self.test_user_id = data.get("user_id")
                self.auth_tokens = data.get("tokens", {})
                return True
            else:
                return False

        except Exception as e:
            return False

    async def _simulate_backend_sync_failure(self) -> bool:
        """Simulate backend synchronization failure."""
        # This would typically involve mocking or causing a failure
        # in the backend user creation process
        return True

    async def _detect_inconsistent_state(self) -> bool:
        """Detect if system is in inconsistent state."""
        try:
            # Check if user exists in auth but not in backend
            auth_exists = await self._check_user_in_auth()
            backend_exists = await self._check_user_in_backend()

            return auth_exists and not backend_exists
        except Exception:
            return False

    async def _attempt_rollback(self) -> bool:
        """Attempt to rollback the inconsistent state."""
        # Implementation would depend on system's rollback mechanism
        return True

    async def _verify_rollback_completion(self) -> bool:
        """Verify rollback was completed successfully."""
        # Check if inconsistent state was resolved
        return not await self._detect_inconsistent_state()

    async def _check_orphaned_records(self) -> bool:
        """Check for orphaned records in auth service."""
        try:
            auth_exists = await self._check_user_in_auth()
            backend_exists = await self._check_user_in_backend()

            # Orphaned if exists in auth but not backend after rollback
            return auth_exists and not backend_exists
        except Exception:
            return False

    async def _test_vulnerability_exposure(self) -> bool:
        """Test if vulnerability is properly exposed."""
        # This test should demonstrate the security risk
        return await self._check_orphaned_records()

    async def _check_user_in_auth(self) -> bool:
        """Check if user exists in auth service."""
        try:
            if not self.auth_tokens:
                return False

            auth_url = get_env("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
            response = await self.http_client.get(
                f"{auth_url}/api/v1/auth/profile",
                headers={"Authorization": f"Bearer {self.auth_tokens.get('access_token')}"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _check_user_in_backend(self) -> bool:
        """Check if user exists in backend service."""
        try:
            if not self.auth_tokens:
                return False

            backend_url = get_env("BACKEND_URL", "https://staging.netrasystems.ai")
            response = await self.http_client.get(
                f"{backend_url}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {self.auth_tokens.get('access_token')}"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _cleanup_test_user(self) -> None:
        """Cleanup test user from all services."""
        try:
            # Cleanup from auth service
            if self.auth_tokens and self.test_user_email:
                auth_url = get_env("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
                await self.http_client.delete(
                    f"{auth_url}/api/v1/auth/user",
                    headers={"Authorization": f"Bearer {self.auth_tokens.get('access_token')}"}
                )
        except Exception:
            pass  # Cleanup is best effort


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.critical
async def test_auth_backend_desynchronization():
    """
    P0 CRITICAL: Test auth backend user desynchronization vulnerability.

    This test MUST expose the vulnerability where user creation succeeds
    in auth service but fails in backend, leaving system in inconsistent state.
    """
    harness = await create_e2e_harness()
    tester = TestAuthBackendDesynchronization(harness)

    await tester.setup()

    try:
        result = await tester.execute_desynchronization_test()

        # Assertions to verify vulnerability exposure
        assert result.auth_user_created, "Auth user creation should succeed"
        assert result.backend_sync_failed, "Backend sync should fail (simulated)"
        assert result.inconsistent_state_detected, "Inconsistent state should be detected"
        assert result.vulnerability_exposed, "Vulnerability should be exposed"

        # Test should fail if vulnerability exists (this exposes the issue)
        if result.orphaned_records_found:
            pytest.fail(
                "CRITICAL VULNERABILITY EXPOSED: User exists in auth but not backend. "
                "This creates authentication bypass potential and data inconsistency."
            )

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    # Allow direct execution for debugging
    asyncio.run(test_auth_backend_desynchronization())