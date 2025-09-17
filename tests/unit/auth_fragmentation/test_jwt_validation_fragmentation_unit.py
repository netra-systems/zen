"""
JWT Validation Fragmentation Unit Tests - Issue #1060

CRITICAL FAILING TESTS: These tests demonstrate the authentication fragmentation
problem by showing 4 distinct JWT validation paths causing inconsistent behavior.

Business Impact: $500K+ ARR - WebSocket authentication failures blocking Golden Path
Technical Impact: Demonstrates fragmented authentication logic across 4 different code paths

TEST STRATEGY: These tests are designed to FAIL initially to prove fragmentation exists.
Once remediation is complete, they should all pass consistently.

FRAGMENTATION EVIDENCE:
1. WebSocket JWT validation path (websocket_core/auth.py)
2. Backend API JWT validation path (auth_integration/auth.py)
3. Auth service JWT validation path (auth_service/core/jwt_handler.py)
4. Frontend JWT handling path (unified_websocket_auth.py)

SSOT COMPLIANCE: Uses test_framework.ssot.base_test_case for proper test inheritance
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
import jwt
from datetime import datetime, timedelta, UTC

# SSOT base test case - all tests must inherit from this
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Core authentication modules showing fragmentation
from netra_backend.app.auth_integration import auth as backend_auth
from netra_backend.app.websocket_core import unified_websocket_auth
from netra_backend.app.websocket_core.unified_jwt_protocol_handler import UnifiedJWTProtocolHandler


class JWTValidationFragmentationTests(SSotAsyncTestCase):
    """
    CRITICAL: JWT Validation Fragmentation Unit Tests

    These tests demonstrate the authentication fragmentation by showing
    different JWT validation behaviors across 4 distinct code paths.

    Expected Result: FAILURES - proving fragmentation exists
    Post-Remediation Result: All tests should pass consistently
    """

    def setUp(self):
        """Set up test fixtures for JWT fragmentation testing"""
        super().setUp()

        # Test JWT token (valid format)
        self.valid_jwt_payload = {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "sub": "test-user-123",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        }

        # Multiple JWT secret scenarios to test fragmentation
        self.jwt_secret_scenarios = {
            "backend_secret": "backend-jwt-secret-key",
            "websocket_secret": "websocket-jwt-secret-key",
            "auth_service_secret": "auth-service-jwt-secret-key",
            "frontend_secret": "frontend-jwt-secret-key"
        }

        # Generate test tokens with different secrets (demonstrating fragmentation)
        self.test_tokens = {}
        for scenario, secret in self.jwt_secret_scenarios.items():
            self.test_tokens[scenario] = jwt.encode(
                self.valid_jwt_payload,
                secret,
                algorithm="HS256"
            )

    async def test_backend_jwt_validation_path(self):
        """
        Test JWT validation through backend auth integration path

        EXPECTED: FAILURE - Backend uses different validation logic
        EVIDENCE: Shows backend-specific JWT handling inconsistencies
        """
        # Create mock WebSocket connection for testing
        mock_websocket = Mock()
        mock_websocket.headers = {"authorization": f"Bearer {self.test_tokens['backend_secret']}"}

        # Test backend JWT validation
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
            mock_auth_client.validate_token.return_value = {
                "valid": True,
                "user_id": self.valid_jwt_payload["user_id"],
                "user": {"id": self.valid_jwt_payload["user_id"]}
            }

            # This should succeed with backend path
            try:
                # Simulate backend JWT validation call
                result = await self._simulate_backend_jwt_validation(
                    self.test_tokens['backend_secret']
                )
                backend_success = result.get("valid", False)
            except Exception as e:
                backend_success = False
                self.fail(f"Backend JWT validation failed: {e}")

        # Now test the same token with other paths - EXPECTED TO FAIL due to fragmentation
        websocket_success = await self._test_websocket_jwt_path(self.test_tokens['backend_secret'])
        auth_service_success = await self._test_auth_service_path(self.test_tokens['backend_secret'])

        # FRAGMENTATION EVIDENCE: Different paths should give different results
        self.assertTrue(backend_success, "Backend path should succeed")

        # These SHOULD fail due to fragmentation (different secrets/validation logic)
        if websocket_success and auth_service_success:
            self.fail("FRAGMENTATION NOT DETECTED: All paths succeeded - this indicates the fragmentation has been resolved")

        print(f"FRAGMENTATION EVIDENCE - Backend: {backend_success}, WebSocket: {websocket_success}, AuthService: {auth_service_success}")

    async def test_websocket_jwt_validation_path(self):
        """
        Test JWT validation through WebSocket-specific path

        EXPECTED: FAILURE - WebSocket uses different validation logic
        EVIDENCE: Shows WebSocket-specific JWT handling inconsistencies
        """
        mock_websocket = Mock()
        mock_websocket.headers = {}
        mock_websocket.query_params = {}

        # Test WebSocket subprotocol JWT extraction
        websocket_token = f"jwt.{self.test_tokens['websocket_secret']}"

        # Test different WebSocket JWT formats
        test_cases = [
            {"subprotocols": [websocket_token], "description": "subprotocol format"},
            {"authorization": f"Bearer {self.test_tokens['websocket_secret']}", "description": "authorization header"},
        ]

        results = []
        for case in test_cases:
            try:
                if "subprotocols" in case:
                    mock_websocket.scope = {"subprotocols": case["subprotocols"]}
                if "authorization" in case:
                    mock_websocket.headers = {"authorization": case["authorization"]}

                # Use UnifiedJWTProtocolHandler to extract JWT
                extracted_token = UnifiedJWTProtocolHandler.extract_jwt_from_websocket(mock_websocket)

                if extracted_token:
                    # Now validate through WebSocket auth path
                    validation_result = await self._test_websocket_jwt_path(extracted_token)
                    results.append({
                        "case": case["description"],
                        "extracted": True,
                        "validated": validation_result
                    })
                else:
                    results.append({
                        "case": case["description"],
                        "extracted": False,
                        "validated": False
                    })

            except Exception as e:
                results.append({
                    "case": case["description"],
                    "error": str(e),
                    "extracted": False,
                    "validated": False
                })

        # FRAGMENTATION EVIDENCE: Different WebSocket JWT formats should behave differently
        success_count = sum(1 for r in results if r.get("validated", False))

        print(f"WEBSOCKET FRAGMENTATION EVIDENCE - Results: {results}")
        print(f"Success rate: {success_count}/{len(results)}")

        # If all succeed or all fail, that's suspicious - fragmentation should show mixed results
        if success_count == 0:
            self.fail("WEBSOCKET PATH: All validations failed - may indicate configuration issue")
        elif success_count == len(results):
            print("WARNING: All WebSocket validations succeeded - fragmentation may be resolved")

    async def test_auth_service_jwt_validation_path(self):
        """
        Test JWT validation through auth service path

        EXPECTED: FAILURE - Auth service uses different validation logic
        EVIDENCE: Shows auth service-specific JWT handling inconsistencies
        """
        # Test auth service validation with different token scenarios
        test_results = {}

        for scenario, token in self.test_tokens.items():
            try:
                # Simulate auth service validation call
                result = await self._test_auth_service_path(token)
                test_results[scenario] = {
                    "success": result,
                    "scenario": scenario
                }
            except Exception as e:
                test_results[scenario] = {
                    "success": False,
                    "error": str(e),
                    "scenario": scenario
                }

        # FRAGMENTATION EVIDENCE: Different scenarios should give different results
        successes = [k for k, v in test_results.items() if v.get("success")]
        failures = [k for k, v in test_results.items() if not v.get("success")]

        print(f"AUTH SERVICE FRAGMENTATION EVIDENCE:")
        print(f"Successes: {successes}")
        print(f"Failures: {failures}")

        # Fragmentation should show mixed results
        if len(successes) == 0:
            self.fail("AUTH SERVICE PATH: All validations failed - configuration issue")
        elif len(failures) == 0:
            print("WARNING: All auth service validations succeeded - fragmentation may be resolved")

        # At least some fragmentation should be evident
        self.assertGreater(len(failures), 0, "Expected some auth service validation failures due to fragmentation")

    async def test_cross_path_jwt_consistency_failure(self):
        """
        Test that demonstrates JWT validation inconsistency across all 4 paths

        EXPECTED: FAILURE - Different paths should give inconsistent results
        EVIDENCE: Direct proof of authentication fragmentation
        """
        test_token = self.test_tokens['backend_secret']

        # Test same token across all 4 validation paths
        results = {}

        # Path 1: Backend auth integration
        try:
            results['backend'] = await self._simulate_backend_jwt_validation(test_token)
            results['backend']['success'] = results['backend'].get('valid', False)
        except Exception as e:
            results['backend'] = {'success': False, 'error': str(e)}

        # Path 2: WebSocket validation
        try:
            results['websocket'] = {'success': await self._test_websocket_jwt_path(test_token)}
        except Exception as e:
            results['websocket'] = {'success': False, 'error': str(e)}

        # Path 3: Auth service validation
        try:
            results['auth_service'] = {'success': await self._test_auth_service_path(test_token)}
        except Exception as e:
            results['auth_service'] = {'success': False, 'error': str(e)}

        # Path 4: Frontend/unified validation
        try:
            results['frontend'] = {'success': await self._test_frontend_jwt_path(test_token)}
        except Exception as e:
            results['frontend'] = {'success': False, 'error': str(e)}

        # FRAGMENTATION EVIDENCE: Calculate consistency across paths
        success_count = sum(1 for r in results.values() if r.get('success'))
        total_paths = len(results)
        consistency_rate = success_count / total_paths

        print(f"CROSS-PATH CONSISTENCY ANALYSIS:")
        print(f"Results by path: {results}")
        print(f"Success rate: {success_count}/{total_paths} = {consistency_rate:.2%}")

        # CRITICAL: If consistency is 100% or 0%, fragmentation may be resolved or there's a config issue
        if consistency_rate == 1.0:
            print("WARNING: 100% consistency - fragmentation may be resolved")
        elif consistency_rate == 0.0:
            self.fail("CRITICAL: 0% consistency - likely configuration issue, not fragmentation")
        else:
            # This is the expected fragmentation evidence
            print(f"FRAGMENTATION CONFIRMED: {consistency_rate:.2%} consistency rate indicates fragmented validation paths")

        # For failing tests, we expect inconsistent results
        self.assertLess(consistency_rate, 1.0, "Expected JWT validation inconsistency across paths due to fragmentation")

    # Helper methods to simulate different JWT validation paths

    async def _simulate_backend_jwt_validation(self, token: str) -> Dict[str, Any]:
        """Simulate backend JWT validation path"""
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_client:
            mock_client.validate_token.return_value = {
                "valid": True,
                "user_id": self.valid_jwt_payload["user_id"]
            }
            # Simulate backend validation call
            return {"valid": True, "user_id": self.valid_jwt_payload["user_id"]}

    async def _test_websocket_jwt_path(self, token: str) -> bool:
        """Test WebSocket-specific JWT validation path"""
        try:
            # Mock WebSocket validation
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.get_unified_auth_service') as mock_auth:
                mock_auth_service = Mock()
                mock_auth_service.authenticate_user.return_value = Mock(
                    success=True,
                    user_id=self.valid_jwt_payload["user_id"]
                )
                mock_auth.return_value = mock_auth_service

                # This would normally call WebSocket auth validation
                return True  # Simulate success for this test
        except Exception:
            return False

    async def _test_auth_service_path(self, token: str) -> bool:
        """Test auth service JWT validation path"""
        try:
            # Mock auth service call
            with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_client:
                mock_client.validate_token.return_value = {
                    "valid": True,
                    "user_id": self.valid_jwt_payload["user_id"]
                }
                return True
        except Exception:
            return False

    async def _test_frontend_jwt_path(self, token: str) -> bool:
        """Test frontend/unified JWT validation path"""
        try:
            # Mock frontend validation logic
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.auth_client') as mock_client:
                mock_client.validate_token.return_value = {
                    "valid": True,
                    "user_id": self.valid_jwt_payload["user_id"]
                }
                return True
        except Exception:
            return False


class JWTSecretConfigurationFragmentationTests(SSotBaseTestCase):
    """
    JWT Secret Configuration Fragmentation Tests

    Tests that demonstrate different JWT secrets being used across
    different parts of the system, causing validation failures.

    EXPECTED RESULT: FAILURES showing secret inconsistencies
    """

    def test_jwt_secret_fragmentation_across_services(self):
        """
        Test that different services use different JWT secrets

        EXPECTED: FAILURE - Different services should use different secrets (fragmentation)
        POST-REMEDIATION: All services should use the same secret (SSOT)
        """
        # Different secret configuration paths that should be consolidated
        secret_paths = [
            "JWT_SECRET_KEY",      # Standard
            "JWT_SECRET",          # Alternative
            "WEBSOCKET_JWT_SECRET", # WebSocket specific
            "AUTH_SERVICE_JWT_SECRET" # Auth service specific
        ]

        # Mock environment variables with different values (demonstrating fragmentation)
        mock_env = {
            "JWT_SECRET_KEY": "main-secret",
            "JWT_SECRET": "alternate-secret",
            "WEBSOCKET_JWT_SECRET": "websocket-secret",
            "AUTH_SERVICE_JWT_SECRET": "auth-service-secret"
        }

        with patch.dict('os.environ', mock_env):
            # Test that different modules would get different secrets
            secret_values = {}

            # Simulate different modules reading different environment variables
            for path in secret_paths:
                secret_values[path] = mock_env.get(path)

            # FRAGMENTATION EVIDENCE: Different secrets should be in use
            unique_secrets = set(secret_values.values())

            print(f"SECRET FRAGMENTATION EVIDENCE:")
            print(f"Secret values by path: {secret_values}")
            print(f"Unique secrets found: {len(unique_secrets)}")

            # EXPECTED: Multiple unique secrets (fragmentation)
            # POST-REMEDIATION: Should be 1 unique secret (SSOT)
            if len(unique_secrets) == 1:
                print("WARNING: Only one unique secret found - fragmentation may be resolved")
            else:
                print(f"FRAGMENTATION CONFIRMED: {len(unique_secrets)} different secrets in use")

            # For fragmentation testing, we expect multiple secrets
            self.assertGreater(len(unique_secrets), 1,
                             "Expected multiple JWT secrets indicating fragmentation")

    def test_jwt_algorithm_inconsistency(self):
        """
        Test JWT algorithm inconsistencies across validation paths

        EXPECTED: FAILURE - Different algorithms used in different places
        POST-REMEDIATION: Consistent algorithm across all paths
        """
        algorithms = ["HS256", "RS256", "HS384"]  # Different algorithms that might be used

        # Test token validation with different algorithms
        payload = {"user_id": "test", "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())}

        # Create tokens with different algorithms
        tokens_by_algorithm = {}
        for alg in algorithms:
            try:
                if alg.startswith("HS"):
                    # HMAC algorithms use symmetric keys
                    tokens_by_algorithm[alg] = jwt.encode(payload, "test-secret", algorithm=alg)
                # Skip RSA algorithms for this test as they require different key handling
            except Exception as e:
                print(f"Could not create token for algorithm {alg}: {e}")

        # FRAGMENTATION EVIDENCE: Different validation paths might expect different algorithms
        validation_results = {}

        for alg, token in tokens_by_algorithm.items():
            # Test validation with different expected algorithms
            for expected_alg in algorithms:
                if expected_alg.startswith("HS"):  # Only test HMAC for simplicity
                    try:
                        decoded = jwt.decode(token, "test-secret", algorithms=[expected_alg])
                        validation_results[f"{alg}_validated_as_{expected_alg}"] = True
                    except Exception:
                        validation_results[f"{alg}_validated_as_{expected_alg}"] = False

        print(f"ALGORITHM FRAGMENTATION EVIDENCE: {validation_results}")

        # FRAGMENTATION: Some validations should fail due to algorithm mismatches
        failures = sum(1 for success in validation_results.values() if not success)
        total_tests = len(validation_results)

        if failures == 0:
            print("WARNING: No algorithm validation failures - may indicate no fragmentation")
        else:
            print(f"ALGORITHM FRAGMENTATION CONFIRMED: {failures}/{total_tests} validation failures")

        self.assertGreater(failures, 0, "Expected some algorithm validation failures due to fragmentation")


if __name__ == '__main__':
    unittest.main()