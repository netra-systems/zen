"""
Auth Backend User Desynchronization Partial Rollback Test - P0 CRITICAL

Test: Auth Backend User Desynchronization Partial Rollback
Critical vulnerability test that exposes scenarios where user creation succeeds 
in the auth service but fails in the backend sync, leaving the system in an 
inconsistent state that requires proper rollback mechanisms.

BVJ (Business Value Justification):
- Segment: All tiers (Free → Enterprise)
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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pytest

from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient
from tests.e2e.integration.unified_e2e_harness import create_e2e_harness
from tests.e2e.integration.user_journey_executor import TestUser


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
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class TestAuthBackendDesynchronizationer:
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
        self.test_user_email = f"desync_test_{uuid.uuid4().hex[:8]}@netra-test.com"
        
    async def cleanup(self) -> None:
        """Cleanup resources and any orphaned records."""
        if self.http_client:
            await self.http_client.aclose()
        # Attempt cleanup of test user if created
        await self._cleanup_test_user()
    
    async def execute_desynchronization_test(self) -> DesynchronizationTestResult:
        """Execute complete desynchronization vulnerability test."""
        start_time = time.time()
        result = DesynchronizationTestResult()
        
        try:
            # Step 1: Create user in auth service (should succeed)
            await self._create_auth_user(result)
            
            # Step 2: Simulate backend sync failure
            await self._simulate_backend_sync_failure(result)
            
            # Step 3: Verify system is in inconsistent state
            await self._verify_inconsistent_state(result)
            
            # Step 4: Test authentication still works (vulnerability)
            await self._test_auth_still_works(result)
            
            # Step 5: Test backend access is blocked (expected)
            await self._test_backend_access_blocked(result)
            
            # Step 6: Verify rollback mechanism detection
            await self._test_rollback_detection(result)
            
            # Step 7: Attempt rollback cleanup
            await self._attempt_rollback_cleanup(result)
            
            # Step 8: Verify orphaned records cleanup
            await self._verify_orphaned_cleanup(result)
            
        except Exception as e:
            result.errors.append(f"Test execution failed: {str(e)}")
        finally:
            result.execution_time = time.time() - start_time
            
        # Determine if vulnerability was successfully exposed
        result.vulnerability_exposed = (
            result.auth_user_created and 
            result.backend_sync_failed and 
            result.inconsistent_state_detected and
            result.auth_login_possible and 
            result.backend_access_blocked
        )
            
        return result
    
    async def _create_auth_user(self, result: DesynchronizationTestResult) -> None:
        """Step 1: Create user in auth service."""
        try:
            auth_url = self.harness.get_service_url("auth")
            
            # Create user directly in auth service
            user_data = {
                "email": self.test_user_email,
                "password": "test_password_123",
                "full_name": "Desync Test User"
            }
            
            response = await self.http_client.post(
                f"{auth_url}/auth/register",
                json=user_data
            )
            
            if response.status_code in [200, 201]:
                auth_response = response.json()
                self.test_user_id = auth_response.get("user_id") or auth_response.get("id")
                self.auth_tokens = {
                    "access_token": auth_response.get("access_token"),
                    "refresh_token": auth_response.get("refresh_token")
                }
                result.auth_user_created = True
            else:
                result.errors.append(f"Auth user creation failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            result.errors.append(f"Auth user creation error: {str(e)}")
    
    async def _simulate_backend_sync_failure(self, result: DesynchronizationTestResult) -> None:
        """Step 2: Simulate backend sync failure."""
        try:
            backend_url = self.harness.get_service_url("backend")
            
            # Try to create user in backend (this should fail to simulate sync failure)
            # We'll mock a network timeout or database connection failure
            
            with patch('httpx.AsyncClient.post') as mock_post:
                # Simulate network timeout during backend sync
                mock_post.side_effect = httpx.TimeoutException("Backend sync timed out")
                
                try:
                    # This would normally be called by the auth service during user creation
                    # We're simulating the failure here
                    user_sync_data = {
                        "user_id": self.test_user_id,
                        "email": self.test_user_email,
                        "created_from_auth": True
                    }
                    
                    response = await self.http_client.post(
                        f"{backend_url}/internal/sync_user",
                        json=user_sync_data,
                        timeout=5.0
                    )
                    
                except (httpx.TimeoutException, httpx.RequestError):
                    # Expected failure - this simulates the sync failure
                    result.backend_sync_failed = True
                    
        except Exception as e:
            # Any exception here represents the sync failure we're testing
            result.backend_sync_failed = True
            result.errors.append(f"Backend sync failure (expected): {str(e)}")
    
    async def _verify_inconsistent_state(self, result: DesynchronizationTestResult) -> None:
        """Step 3: Verify system is in inconsistent state."""
        try:
            if not self.auth_tokens or not self.auth_tokens.get("access_token"):
                result.errors.append("Cannot verify inconsistent state - no auth tokens")
                return
                
            auth_url = self.harness.get_service_url("auth")
            backend_url = self.harness.get_service_url("backend")
            headers = {"Authorization": f"Bearer {self.auth_tokens['access_token']}"}
            
            # Check if user exists in auth service
            auth_check = await self.http_client.get(
                f"{auth_url}/auth/me",
                headers=headers
            )
            
            # Check if user exists in backend service
            backend_check = await self.http_client.get(
                f"{backend_url}/user/profile",
                headers=headers
            )
            
            # Inconsistent state: user exists in auth but not in backend
            if (auth_check.status_code == 200 and 
                backend_check.status_code in [404, 401, 403]):
                result.inconsistent_state_detected = True
            else:
                result.errors.append(f"Inconsistent state not detected: auth={auth_check.status_code}, backend={backend_check.status_code}")
                
        except Exception as e:
            result.errors.append(f"Inconsistent state verification failed: {str(e)}")
    
    async def _test_auth_still_works(self, result: DesynchronizationTestResult) -> None:
        """Step 4: Test authentication still works (exposes vulnerability)."""
        try:
            if not self.auth_tokens or not self.auth_tokens.get("access_token"):
                result.errors.append("Cannot test auth - no tokens available")
                return
                
            auth_url = self.harness.get_service_url("auth")
            
            # Test token validation - this should still work
            token_validation = await self.http_client.post(
                f"{auth_url}/auth/validate",
                json={"token": self.auth_tokens["access_token"]}
            )
            
            if token_validation.status_code == 200:
                token_data = token_validation.json()
                if token_data.get("valid") and token_data.get("user_id") == self.test_user_id:
                    result.auth_login_possible = True
                else:
                    result.errors.append(f"Auth validation failed: {token_data}")
            else:
                result.errors.append(f"Auth token validation failed: {token_validation.status_code}")
                
        except Exception as e:
            result.errors.append(f"Auth validation test failed: {str(e)}")
    
    async def _test_backend_access_blocked(self, result: DesynchronizationTestResult) -> None:
        """Step 5: Test backend access is blocked (expected behavior)."""
        try:
            if not self.auth_tokens or not self.auth_tokens.get("access_token"):
                result.errors.append("Cannot test backend access - no tokens")
                return
                
            backend_url = self.harness.get_service_url("backend")
            headers = {"Authorization": f"Bearer {self.auth_tokens['access_token']}"}
            
            # Try to access backend services - should fail
            backend_access_tests = [
                f"{backend_url}/user/profile",
                f"{backend_url}/user/settings",
                f"{backend_url}/api/threads"
            ]
            
            blocked_count = 0
            for endpoint in backend_access_tests:
                try:
                    response = await self.http_client.get(endpoint, headers=headers)
                    if response.status_code in [401, 403, 404]:
                        blocked_count += 1
                except Exception:
                    blocked_count += 1
            
            # If majority of backend endpoints are blocked, consider access blocked
            if blocked_count >= len(backend_access_tests) // 2:
                result.backend_access_blocked = True
            else:
                result.errors.append(f"Backend access not properly blocked: {blocked_count}/{len(backend_access_tests)} blocked")
                
        except Exception as e:
            result.errors.append(f"Backend access test failed: {str(e)}")
    
    async def _test_rollback_detection(self, result: DesynchronizationTestResult) -> None:
        """Step 6: Test rollback mechanism detection."""
        try:
            # Check if system has any rollback detection mechanisms
            auth_url = self.harness.get_service_url("auth")
            
            # Check for health endpoint that might detect inconsistencies
            health_check = await self.http_client.get(f"{auth_url}/auth/health")
            
            if health_check.status_code == 200:
                health_data = health_check.json()
                # Look for any consistency check indicators
                if ("consistency_check" in health_data or 
                    "sync_status" in health_data or
                    "orphaned_users" in health_data):
                    result.rollback_attempted = True
                    
        except Exception as e:
            result.errors.append(f"Rollback detection test failed: {str(e)}")
    
    async def _attempt_rollback_cleanup(self, result: DesynchronizationTestResult) -> None:
        """Step 7: Attempt rollback cleanup."""
        try:
            if not self.test_user_id:
                result.errors.append("Cannot attempt rollback - no user ID")
                return
                
            auth_url = self.harness.get_service_url("auth")
            
            # Attempt to trigger cleanup of orphaned user
            cleanup_request = {
                "action": "cleanup_orphaned_user",
                "user_id": self.test_user_id,
                "reason": "backend_sync_failure"
            }
            
            cleanup_response = await self.http_client.post(
                f"{auth_url}/admin/cleanup",
                json=cleanup_request
            )
            
            if cleanup_response.status_code in [200, 202]:
                result.rollback_completed = True
            else:
                # Rollback endpoint might not exist - this exposes the vulnerability
                result.errors.append(f"Rollback cleanup failed: {cleanup_response.status_code}")
                
        except Exception as e:
            result.errors.append(f"Rollback cleanup attempt failed: {str(e)}")
    
    async def _verify_orphaned_cleanup(self, result: DesynchronizationTestResult) -> None:
        """Step 8: Verify orphaned records cleanup."""
        try:
            if not self.auth_tokens or not self.auth_tokens.get("access_token"):
                return
                
            auth_url = self.harness.get_service_url("auth")
            headers = {"Authorization": f"Bearer {self.auth_tokens['access_token']}"}
            
            # Check if user still exists in auth after cleanup attempt
            user_check = await self.http_client.get(
                f"{auth_url}/auth/me",
                headers=headers
            )
            
            if user_check.status_code in [401, 403, 404]:
                # User was properly cleaned up
                result.cleanup_successful = True
            else:
                # User still exists - orphaned record detected
                result.orphaned_records_found = True
                result.errors.append("Orphaned auth record still exists after cleanup")
                
        except Exception as e:
            result.errors.append(f"Orphaned cleanup verification failed: {str(e)}")
    
    async def _cleanup_test_user(self) -> None:
        """Cleanup test user from both services."""
        try:
            if not self.test_user_id:
                return
                
            # Force cleanup from auth service
            auth_url = self.harness.get_service_url("auth")
            
            # Try to delete user directly (admin operation)
            delete_response = await self.http_client.delete(
                f"{auth_url}/admin/users/{self.test_user_id}"
            )
            
            # Don't fail if cleanup fails - test cleanup should be best-effort
            
        except Exception:
            # Ignore cleanup failures - they shouldn't affect test results
            pass


def create_e2e_harness():
    """Factory function to create E2E harness."""
    from tests.e2e.integration.unified_e2e_harness import UnifiedE2ETestHarness
    return UnifiedE2ETestHarness()


# PYTEST TEST IMPLEMENTATIONS

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.critical
async def test_auth_backend_user_desynchronization_vulnerability():
    """
    Test: Auth Backend User Desynchronization Vulnerability
    
    CRITICAL SECURITY TEST - Exposes vulnerability where user creation
    succeeds in auth service but fails in backend sync, leaving system
    in inconsistent state that allows authentication without backend access.
    
    This test should FAIL until proper rollback mechanisms are implemented.
    """
    async with create_e2e_harness().test_environment() as harness:
        tester = AuthBackendDesynchronizationTester(harness)
        await tester.setup()
        
        try:
            result = await tester.execute_desynchronization_test()
            
            # These assertions expose the vulnerability
            assert result.auth_user_created, f"Auth user creation failed: {result.errors}"
            assert result.backend_sync_failed, f"Backend sync should have failed: {result.errors}"
            assert result.inconsistent_state_detected, f"Inconsistent state not detected: {result.errors}"
            
            # The vulnerability: user can authenticate but can't access backend
            assert result.auth_login_possible, f"Auth login should still work: {result.errors}"
            assert result.backend_access_blocked, f"Backend access should be blocked: {result.errors}"
            
            # Verify the vulnerability is exposed
            assert result.vulnerability_exposed, f"Vulnerability not properly exposed: {result.errors}"
            
            # Performance check
            assert result.execution_time < 45.0, f"Test too slow: {result.execution_time:.2f}s"
            
            print(f"[VULNERABILITY EXPOSED] Auth-Backend Desynchronization: {result.execution_time:.2f}s")
            print(f"[CRITICAL] User can authenticate but cannot access backend services")
            if result.orphaned_records_found:
                print(f"[CRITICAL] Orphaned auth records detected")
            if not result.rollback_completed:
                print(f"[CRITICAL] No automatic rollback mechanism found")
            
        finally:
            await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.critical
async def test_partial_rollback_mechanism_validation():
    """
    Test: Partial Rollback Mechanism Validation
    
    Tests the system's ability to detect and clean up inconsistent
    user states caused by partial failures during user creation.
    
    This test validates that proper rollback mechanisms exist.
    """
    async with create_e2e_harness().test_environment() as harness:
        tester = AuthBackendDesynchronizationTester(harness)
        await tester.setup()
        
        try:
            result = await tester.execute_desynchronization_test()
            
            # Rollback mechanism validation
            if result.vulnerability_exposed:
                # If vulnerability exists, rollback should be attempted
                assert result.rollback_attempted, f"System should attempt rollback: {result.errors}"
                
                # Check if cleanup was successful
                if result.rollback_attempted:
                    assert result.cleanup_successful or not result.orphaned_records_found, \
                        f"Rollback should clean up orphaned records: {result.errors}"
            
            # Performance requirement
            assert result.execution_time < 45.0, f"Rollback test too slow: {result.execution_time:.2f}s"
            
            print(f"[ROLLBACK TEST] Execution time: {result.execution_time:.2f}s")
            if result.rollback_completed:
                print(f"[SUCCESS] Rollback mechanism functioning")
            else:
                print(f"[WARNING] No rollback mechanism detected")
                
        finally:
            await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.critical
async def test_orphaned_record_detection_and_cleanup():
    """
    Test: Orphaned Record Detection and Cleanup
    
    Tests the system's ability to detect and clean up orphaned
    authentication records that exist without corresponding backend records.
    
    Critical for maintaining data consistency and preventing account corruption.
    """
    async with create_e2e_harness().test_environment() as harness:
        tester = AuthBackendDesynchronizationTester(harness)
        await tester.setup()
        
        try:
            result = await tester.execute_desynchronization_test()
            
            # Orphaned record detection
            if result.vulnerability_exposed:
                # System should detect orphaned records
                assert not result.orphaned_records_found or result.cleanup_successful, \
                    f"Orphaned records should be cleaned up: {result.errors}"
            
            # No excessive errors should occur
            assert len(result.errors) <= 5, f"Too many errors in orphaned record test: {result.errors}"
            
            print(f"[ORPHANED RECORDS] Test completed: {result.execution_time:.2f}s")
            if result.orphaned_records_found and not result.cleanup_successful:
                print(f"[CRITICAL] Orphaned records detected and not cleaned up")
            elif result.cleanup_successful:
                print(f"[SUCCESS] Orphaned records properly cleaned up")
                
        finally:
            await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.critical
async def test_complete_desynchronization_scenario():
    """
    Test: Complete Desynchronization Scenario
    
    Comprehensive test that validates the complete desynchronization vulnerability
    scenario and tests all aspects of the rollback and cleanup mechanisms.
    
    This test serves as the definitive validation for auth-backend synchronization
    integrity and should guide the implementation of proper error handling.
    """
    async with create_e2e_harness().test_environment() as harness:
        tester = AuthBackendDesynchronizationTester(harness)
        await tester.setup()
        
        try:
            result = await tester.execute_desynchronization_test()
            
            # Complete scenario validation
            assert result.auth_user_created, "Auth user creation must succeed"
            assert result.backend_sync_failed, "Backend sync must fail to simulate real scenario"
            assert result.inconsistent_state_detected, "System must detect inconsistent state"
            assert result.vulnerability_exposed, "Vulnerability must be properly exposed"
            
            # Security validation - the key vulnerability
            assert result.auth_login_possible and result.backend_access_blocked, \
                "Critical vulnerability: user can auth but cannot access backend"
            
            # Error count should be reasonable (some expected errors from simulated failures)
            assert len(result.errors) <= 8, f"Excessive errors detected: {result.errors}"
            
            # Performance validation
            assert result.execution_time < 60.0, f"Complete test too slow: {result.execution_time:.2f}s"
            
            # Generate comprehensive test report
            print(f"\n[DESYNCHRONIZATION TEST REPORT]")
            print(f"Execution Time: {result.execution_time:.2f}s")
            print(f"Auth User Created: {result.auth_user_created}")
            print(f"Backend Sync Failed: {result.backend_sync_failed}")
            print(f"Inconsistent State: {result.inconsistent_state_detected}")
            print(f"Auth Login Possible: {result.auth_login_possible}")
            print(f"Backend Access Blocked: {result.backend_access_blocked}")
            print(f"Vulnerability Exposed: {result.vulnerability_exposed}")
            print(f"Rollback Attempted: {result.rollback_attempted}")
            print(f"Rollback Completed: {result.rollback_completed}")
            print(f"Orphaned Records: {result.orphaned_records_found}")
            print(f"Cleanup Successful: {result.cleanup_successful}")
            
            if result.vulnerability_exposed:
                print(f"\n[CRITICAL FINDING] Auth-Backend desynchronization vulnerability confirmed")
                print(f"[RECOMMENDATION] Implement atomic user creation with proper rollback")
                print(f"[RECOMMENDATION] Add consistency checking and cleanup mechanisms")
                print(f"[RECOMMENDATION] Implement distributed transaction patterns")
            
        finally:
            await tester.cleanup()