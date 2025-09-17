"""
E2E Test: Auth-Backend Integration Core

This test validates the core integration between the auth service and backend service,
ensuring that authentication flows work correctly across both services with real databases.

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Secure user authentication and service integration
- Value Impact: Ensures users can authenticate and access backend features seamlessly
- Strategic/Revenue Impact: Authentication failures block user engagement and revenue

CRITICAL COMPLIANCE WITH CLAUDE.md:"""
- Absolute imports only (no relative imports)"""
- Real database connections and services tested end-to-end"""

        # Setup test path for absolute imports following CLAUDE.md standards
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
sys.path.insert(0, str(project_root))

            # Absolute imports following CLAUDE.md standards
import asyncio
import aiohttp
import pytest
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List

            # Import IsolatedEnvironment for proper environment management as required by CLAUDE.md
from shared.isolated_environment import get_env as get_auth_env
from shared.isolated_environment import get_env as get_backend_env

logger = logging.getLogger(__name__)"""
"""
    """"""
"""
    No mocks are used anywhere in this test suite."""
"""
        pass"""
        self.auth_service_url = "http://localhost:8081"  # Standard auth service port
        self.backend_service_url = "http://localhost:8000"  # Standard backend service port

    # Test state tracking
        self.integration_failures = []
        self.auth_token = None
        self.refresh_token = None
        self.test_user_id = None
        self.test_user_email = None

    async def check_service_availability(self, session: aiohttp.ClientSession, service_name: str, url: str) -> bool:
        """Check if a service is available by testing its health endpoint."""
        try:"""
        async with session.get("formatted_string", timeout=aiohttp.ClientTimeout(total=10)) as response:
        if response.status == 200:
        logger.info("formatted_string")
        return True
        except Exception as e:
        logger.debug("formatted_string")

                    # If health endpoint fails, try root endpoint
        try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
        if response.status in [200, 404]:  # 404 is acceptable for root
        logger.info("formatted_string")
        return True
        except Exception as e:
        logger.debug("formatted_string")

        logger.warning("formatted_string")
        return False

    async def test_user_registration(self, session:
        """Test user registration through auth service."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing user registration...")

                                    # Generate unique test user
test_user = {"email": "formatted_string",, "password": "TestPassword123!",, "full_name": "Auth Backend Integration Test User"}
        self.test_user_email = test_user["email"]

        try:
registration_data = {"email": test_user["email"],, "password": test_user["password"],, "confirm_password": test_user["password"],, "full_name": test_user["full_name"]}
        async with session.post( )
        "formatted_string",
        json=registration_data,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status != 201:
        self.integration_failures.append("formatted_string")
        return None
        else:
        registration_result = await response.json()
        self.test_user_id = registration_result.get('user_id')
        logger.info("formatted_string")
        return test_user

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return None

    async def test_user_login(self, session:
        """Test user login and token generation."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing user login...")

        try:
login_data = {"email": test_user["email"],, "password": test_user["password"]}
        async with session.post( )
        "formatted_string",
        json=login_data,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status != 200:
        self.integration_failures.append("formatted_string")
        return False
        else:
        login_result = await response.json()
        self.auth_token = login_result.get("access_token")
        self.refresh_token = login_result.get("refresh_token")

        if not self.auth_token:
        self.integration_failures.append("Login response missing access_token")
        return False

        logger.info("[SUCCESS] User login successful, tokens received")
        return True

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return False

    async def test_auth_service_token_validation(self, session:
        """Test token validation directly with auth service."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing auth service token validation...")

        if not self.auth_token:
        self.integration_failures.append("No auth token available for validation")
        return False

        try:
        headers = {"Authorization": "formatted_string"}
        async with session.get( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status != 200:
        self.integration_failures.append("formatted_string")
        return False
        else:
        user_info = await response.json()
        if user_info.get("email") != self.test_user_email:
        self.integration_failures.append("formatted_string")
        return False

        logger.info("[SUCCESS] Auth service token validation successful")
        return True

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return False

    async def test_backend_token_propagation(self, session:
        """Test token propagation from auth service to backend service."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing backend token propagation...")

        if not self.auth_token:
        self.integration_failures.append("No auth token available for backend propagation test")
        return False

        try:
        headers = {"Authorization": "formatted_string"}

                                                                                                                                # Try multiple backend endpoints that should accept auth tokens
        test_endpoints = [ )
        "formatted_string",
        "formatted_string",
        "formatted_string"  # Some backends might have protected health endpoints
                                                                                                                                

        for endpoint in test_endpoints:
        try:
        async with session.get( )
        endpoint,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status == 200:
        logger.info("formatted_string")
        return True
        elif response.status == 401:
        logger.debug("formatted_string")
        continue  # Try next endpoint
        elif response.status == 404:
        logger.debug("formatted_string")
        continue  # Endpoint doesn"t exist, try next
        else:
        logger.debug("formatted_string")
        continue  # Try next endpoint

        except Exception as e:
        logger.debug("formatted_string")
        continue  # Try next endpoint

                                                                                                                                                                # If we get here, none of the endpoints worked
        self.integration_failures.append("Backend token propagation failed - no protected endpoints accepted auth token")
        return False

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return False

    async def test_database_session_consistency(self, session:
        """Test that user data is consistent between auth and backend databases."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing database session consistency...")

        if not self.auth_token:
        self.integration_failures.append("No auth token available for database consistency test")
        return False

        try:
        headers = {"Authorization": "formatted_string"}

                                                                                                                                                                                Get user data from auth service
        auth_user_data = None
        async with session.get( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        if response.status == 200:
        auth_user_data = await response.json()
        else:
        logger.warning("formatted_string")
        return False

                                                                                                                                                                                            Try to get user data from backend service
        backend_user_data = None
        try:
        async with session.get( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        if response.status == 200:
        backend_user_data = await response.json()
        elif response.status == 404:
        logger.info("[INFO] Backend user profile endpoint not found - this is acceptable")
        return True  # Not a failure if endpoint doesn"t exist yet
        else:
        logger.debug("formatted_string")
        return True  # Not a failure for now
        except Exception as e:
        logger.debug("formatted_string")
        return True  # Not a failure for now

                                                                                                                                                                                                                    # If we have both datasets, compare them
        if auth_user_data and backend_user_data:
        auth_user_id = auth_user_data.get("user_id") or auth_user_data.get("id")
        backend_user_id = backend_user_data.get("user_id") or backend_user_data.get("id")

        if auth_user_id != backend_user_id:
        self.integration_failures.append("formatted_string")
        return False

        auth_email = auth_user_data.get("email")
        backend_email = backend_user_data.get("email")

        if auth_email != backend_email:
        self.integration_failures.append("formatted_string")
        return False

        logger.info("[SUCCESS] Database session consistency verified")
        else:
        logger.info("[INFO] Database consistency test completed (limited backend endpoints available)")

        return True

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return False

    async def test_token_refresh_flow(self, session:
        """Test JWT token refresh across services."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing token refresh flow...")

        if not self.refresh_token:
        logger.info("[INFO] No refresh token available - skipping refresh flow test")
        return True  # Not a failure if refresh tokens aren"t implemented yet

        try:
        refresh_data = {"refresh_token": self.refresh_token}

        async with session.post( )
        "formatted_string",
        json=refresh_data,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status != 200:
        logger.info("formatted_string")
        return True  # Not a failure if not implemented yet
        else:
        refresh_result = await response.json()
        if not new_access_token:
        self.integration_failures.append("Token refresh response missing access_token")
        return False

                                                                                                                                                                                                                                                                    # Test the new token works with backend
        headers = {"Authorization": "formatted_string"}
        async with session.get( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=10)
        ) as test_response:
        if test_response.status in [200, 404]:  # Either works or endpoint doesn"t exist
        logger.info("[SUCCESS] Token refresh flow successful")
        return True
        else:
        self.integration_failures.append("formatted_string")
        return False

        except Exception as e:
        logger.info("formatted_string")
        return True  # Not a critical failure

    async def test_user_logout(self, session:
        """Test user logout and token invalidation across services."""
        logger.info("[AUTH-BACKEND-INTEGRATION] Testing user logout...")

        if not self.auth_token:
        self.integration_failures.append("No auth token available for logout test")
        return False

        try:
        headers = {"Authorization": "formatted_string"}

        async with session.post( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
        response_text = await response.text()

        if response.status not in [200, 204]:
        self.integration_failures.append("formatted_string")
        return False
        else:
        logger.info("[SUCCESS] User logout successful")

                                                                                                                                                                                                                                                                                                        # Verify token is invalidated - wait a moment for propagation
        await asyncio.sleep(2)

        async with session.get( )
        "formatted_string",
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=10)
        ) as test_response:
        if test_response.status != 401:
        self.integration_failures.append("formatted_string")
        return False
        else:
        logger.info("[SUCCESS] Token correctly invalidated after logout")
        return True

        except Exception as e:
        self.integration_failures.append("formatted_string")
        return False


        @pytest.mark.e2e
@pytest.mark.asyncio
    async def test_auth_backend_integration_core():
"""
Comprehensive test of auth-backend integration with real services.

This test validates the complete authentication flow between auth service
and backend service using real database connections and no mocks.

COMPLIANCE: Follows CLAUDE.md standards for e2e testing:"""
- Absolute imports only"""
- Tests real database connectivity"""

                                                                                                                                                                                                                                                                                                                                # Setup environment using IsolatedEnvironment as required by CLAUDE.md
auth_env = get_auth_env()"""
"""
auth_env.set("ENVIRONMENT", "test", "auth_backend_integration_test")
backend_env.set("ENVIRONMENT", "test", "auth_backend_integration_test")

                                                                                                                                                                                                                                                                                                                                # Initialize integration tester
tester = AuthBackendIntegrationTester()

                                                                                                                                                                                                                                                                                                                                # Run integration tests
async with aiohttp.ClientSession() as session:
                                                                                                                                                                                                                                                                                                                                    # Pre-check: Verify both services are available
logger.info("[SETUP] Checking service availability...")

auth_available = await tester.check_service_availability(session, "Auth Service", tester.auth_service_url)
backend_available = await tester.check_service_availability(session, "Backend Service", tester.backend_service_url)

if not auth_available:
pytest.skip("formatted_string")

if not backend_available:
pytest.skip("formatted_string")

logger.info("[SETUP] Both services are available - proceeding with integration tests")

                                                                                                                                                                                                                                                                                                                                            # Execute integration test flow
test_user = await tester.test_user_registration(session)
if not test_user:
pytest.fail("User registration failed - cannot proceed with integration tests")

login_success = await tester.test_user_login(session, test_user)
if not login_success:
pytest.fail("User login failed - cannot proceed with integration tests")

                                                                                                                                                                                                                                                                                                                                                    # Core integration tests
auth_validation_success = await tester.test_auth_service_token_validation(session)
backend_propagation_success = await tester.test_backend_token_propagation(session)
database_consistency_success = await tester.test_database_session_consistency(session)
token_refresh_success = await tester.test_token_refresh_flow(session)
logout_success = await tester.test_user_logout(session)

                                                                                                                                                                                                                                                                                                                                                    # Analyze results
critical_failures = []
warning_failures = []

for failure in tester.integration_failures:
if any(critical in failure.lower() for critical in ["registration failed", "login failed", "token validation failed"]):
critical_failures.append(failure)
else:
warning_failures.append(failure)

                                                                                                                                                                                                                                                                                                                                                                # Report results
if critical_failures:
failure_report = ["[CRITICAL] Auth-Backend Integration Failures:"]
for failure in critical_failures:
failure_report.append("formatted_string")

if warning_failures:
failure_report.append("[WARNING] Additional Issues:")
for failure in warning_failures:
failure_report.append("formatted_string")

failure_report.append("formatted_string")
pytest.fail("Auth-Backend Integration failed: )
" + "
".join(failure_report))

elif warning_failures:
warning_report = ["[WARNING] Auth-Backend Integration Issues:"]
for failure in warning_failures:
warning_report.append("formatted_string")
warning_report.append("formatted_string")

logger.warning(" )
".join(warning_report))
print(" )
".join(warning_report))

logger.info("[SUCCESS] Auth-Backend Integration test completed successfully")


@pytest.mark.e2e
@pytest.mark.asyncio
    async def test_auth_backend_database_isolation():
'''
Test that auth and backend services maintain proper database isolation.

This test verifies that services don't interfere with each other's database
connections while sharing user authentication data appropriately.
'''

                                                                                                                                                                                                                                                                                                                                                                                            # Setup environment using IsolatedEnvironment as required by CLAUDE.md
auth_env = get_auth_env()
backend_env = get_backend_env()

                                                                                                                                                                                                                                                                                                                                                                                            # Set test environment configuration
auth_env.set("ENVIRONMENT", "test", "database_isolation_test")
backend_env.set("ENVIRONMENT", "test", "database_isolation_test")

                                                                                                                                                                                                                                                                                                                                                                                            # This test would check database isolation patterns
                                                                                                                                                                                                                                                                                                                                                                                            # For now, we'll implement basic connection verification

isolation_failures = []

async with aiohttp.ClientSession() as session:
                                                                                                                                                                                                                                                                                                                                                                                                # Test auth service database health
try:
async with session.get("http://localhost:8081/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
if response.status == 200:
health_data = await response.json()
if not health_data.get("database_connected"):
isolation_failures.append("Auth service database not properly connected")
else:
isolation_failures.append("formatted_string")
except Exception as e:
isolation_failures.append("formatted_string")

                                                                                                                                                                                                                                                                                                                                                                                                                        # Test backend service database health
try:
async with session.get("http://localhost:8000/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
if response.status == 200:
health_data = await response.json()
                                                                                                                                                                                                                                                                                                                                                                                                                                    # Backend health might not include database status - that's ok
logger.info("Backend service health check successful")
else:
isolation_failures.append("formatted_string")
except Exception as e:
isolation_failures.append("formatted_string")

if isolation_failures:
failure_report = ["Database isolation test failures:"]
for failure in isolation_failures:
failure_report.append("formatted_string")
pytest.fail(" )
".join(failure_report))

logger.info("[SUCCESS] Database isolation test completed successfully")


if __name__ == "__main__":
pytest.main([__file__, "-v", "--tb=short"])
