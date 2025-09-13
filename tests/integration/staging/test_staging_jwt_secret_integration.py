"""
Integration Tests for Staging JWT Secret Integration

This test suite validates real staging environment JWT secret integration
including Google Secret Manager interaction, Cloud Run secret mounting,
and end-to-end authentication flow.

These tests use REAL SERVICES (no Docker) and are designed to FAIL initially.

EXPECTED FAILURE MODES:
- GSM secret retrieval failures in staging environment
- Missing secret mounting in Cloud Run deployment
- Authentication pipeline failures due to secret unavailability
- Cross-service JWT validation failures

Business Value: $500K+ ARR depends on staging authentication working
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
import os
import time

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# System under test imports
from shared.jwt_secret_manager import get_jwt_secret_manager, JWTSecretManager
from shared.isolated_environment import get_env
from deployment.secrets_config import SecretConfig

logger = logging.getLogger(__name__)


class TestStagingJWTSecretIntegration(SSotAsyncTestCase):
    """
    Integration tests for staging JWT secret management.

    These tests validate real staging environment interaction
    without Docker containers, focusing on GCP staging environment.
    """

    def setUp(self):
        """Set up integration test environment."""
        super().setUp()

        # Real staging environment configuration
        self.staging_env = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT': 'netra-staging',
            'K_SERVICE': 'netra-backend-staging',
            'K_REVISION': 'netra-backend-staging-00001-abc',
            'K_CONFIGURATION': 'netra-backend-staging',
            'PORT': '8080'
        }

        # Clear any cached JWT secrets
        jwt_manager = get_jwt_secret_manager()
        jwt_manager.clear_cache()

    async def test_staging_gsm_secret_retrieval_real_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Real GSM secret retrieval in staging.

        This test validates that JWT secrets can actually be retrieved
        from Google Secret Manager in a real staging environment.

        BUSINESS IMPACT: Without GSM integration, staging authentication
        will fail and block $500K+ ARR validation.
        """
        with self.patch_environment(self.staging_env):
            jwt_manager = get_jwt_secret_manager()

            # Clear cache to force fresh GSM lookup
            jwt_manager.clear_cache()

            try:
                # This should trigger GSM lookup via get_staging_secret
                secret = jwt_manager.get_jwt_secret()

                # If this succeeds, validate it's from GSM, not fallback
                self.assertIsNotNone(secret, "Should retrieve JWT secret from GSM")
                self.assertGreaterEqual(len(secret), 32,
                                      "GSM secret should meet length requirements")

                # Validate it's not a fallback value
                self.assertNotIn("emergency", secret.lower(),
                                "Should not use emergency fallback in staging")
                self.assertNotIn("fallback", secret.lower(),
                                "Should not use fallback secret in staging")
                self.assertNotIn("deterministic", secret.lower(),
                                "Should not use deterministic secret in staging")

                # Test secret validation
                is_valid, validation_context = jwt_manager.validate_jwt_secret_for_environment(
                    secret, "staging"
                )
                self.assertTrue(is_valid,
                              f"GSM secret should be valid for staging: {validation_context}")

                logger.warning(f"Unexpected GSM integration success in staging")

            except ImportError as e:
                # Expected failure - get_staging_secret function missing
                logger.error(f"EXPECTED FAILURE: GSM integration missing: {e}")
                self.assertIn("get_staging_secret", str(e),
                            "Should fail on missing get_staging_secret function")
                raise

            except ValueError as e:
                # Expected failure - staging configuration invalid
                logger.error(f"EXPECTED FAILURE: Staging JWT configuration invalid: {e}")
                self.assertIn("staging", str(e).lower(),
                            "Error should mention staging environment")
                raise

    async def test_cloud_run_environment_detection_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Cloud Run environment detection and configuration.

        This test validates that the system properly detects Cloud Run
        environment and applies staging-specific JWT configuration.
        """
        # Test with full Cloud Run environment
        cloud_run_env = {
            **self.staging_env,
            'K_REVISION': 'netra-backend-staging-00042-def',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }

        with self.patch_environment(cloud_run_env):
            env = get_env()

            # Validate Cloud Run detection
            self.assertEqual(env.get('ENVIRONMENT'), 'staging',
                           "Should detect staging environment")
            self.assertIsNotNone(env.get('K_SERVICE'),
                               "Should detect Cloud Run service")
            self.assertIsNotNone(env.get('K_REVISION'),
                               "Should detect Cloud Run revision")

            jwt_manager = get_jwt_secret_manager()
            jwt_manager.clear_cache()

            debug_info = jwt_manager.get_debug_info()
            self.assertEqual(debug_info['environment'], 'staging',
                           "JWT manager should detect staging")

            try:
                # This should work in Cloud Run with proper secret mounting
                secret = jwt_manager.get_jwt_secret()

                # Validate staging-specific behavior
                validation_result = jwt_manager.validate_jwt_configuration()
                self.assertTrue(validation_result['valid'],
                              f"Cloud Run JWT config should be valid: {validation_result}")

                logger.warning(f"Unexpected Cloud Run environment success")

            except (ImportError, ValueError) as e:
                # Expected failure - Cloud Run secrets not mounted
                logger.error(f"EXPECTED FAILURE: Cloud Run environment failed: {e}")
                self.assertTrue(
                    "staging" in str(e).lower() or
                    "secret" in str(e).lower() or
                    "get_staging_secret" in str(e),
                    f"Error should mention staging/secrets/GSM: {e}"
                )
                raise

    async def test_cross_service_jwt_validation_staging_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Cross-service JWT validation in staging.

        This test validates that JWT tokens created by one service
        can be validated by another service in staging environment.
        """
        with self.patch_environment(self.staging_env):
            # Test both backend and auth service JWT managers
            backend_manager = JWTSecretManager()
            auth_manager = JWTSecretManager()

            backend_manager.clear_cache()
            auth_manager.clear_cache()

            try:
                # Both should use the same JWT secret from GSM
                backend_secret = backend_manager.get_jwt_secret()
                auth_secret = auth_manager.get_jwt_secret()

                # Critical: Secrets must match for cross-service validation
                self.assertEqual(backend_secret, auth_secret,
                               "Backend and auth services must use same JWT secret")

                # Test JWT token cross-validation
                import jwt as pyjwt

                backend_algorithm = backend_manager.get_jwt_algorithm()
                auth_algorithm = auth_manager.get_jwt_algorithm()

                self.assertEqual(backend_algorithm, auth_algorithm,
                               "Services must use same JWT algorithm")

                # Create token with backend service
                test_payload = {
                    "user_id": "test_user_staging",
                    "service": "backend",
                    "exp": int(time.time()) + 3600
                }

                token = pyjwt.encode(test_payload, backend_secret, algorithm=backend_algorithm)

                # Validate with auth service
                decoded = pyjwt.decode(token, auth_secret, algorithms=[auth_algorithm])

                self.assertEqual(decoded["user_id"], "test_user_staging",
                               "Cross-service JWT validation should preserve payload")

                logger.warning(f"Unexpected cross-service JWT validation success")

            except (ImportError, ValueError) as e:
                # Expected failure - services can't get consistent JWT secrets
                logger.error(f"EXPECTED FAILURE: Cross-service JWT validation failed: {e}")
                raise

    async def test_staging_secret_mapping_validation_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Staging secret mapping validation.

        This test validates that secret mappings between environment
        variables and GSM secrets work correctly in staging.
        """
        # Test secret mappings from SecretConfig
        jwt_secrets = ["JWT_SECRET", "JWT_SECRET_KEY", "JWT_SECRET_STAGING"]

        for secret_name in jwt_secrets:
            gsm_mapping = SecretConfig.get_gsm_mapping(secret_name)
            self.assertEqual(gsm_mapping, "jwt-secret-staging",
                           f"{secret_name} should map to jwt-secret-staging in GSM")

        # Test deployment configuration
        backend_secrets_string = SecretConfig.generate_secrets_string("backend")
        auth_secrets_string = SecretConfig.generate_secrets_string("auth")

        # All JWT secrets should map to the same GSM secret
        expected_mappings = [
            "JWT_SECRET=jwt-secret-staging:latest",
            "JWT_SECRET_KEY=jwt-secret-staging:latest",
            "JWT_SECRET_STAGING=jwt-secret-staging:latest"
        ]

        for mapping in expected_mappings:
            self.assertIn(mapping, backend_secrets_string,
                         f"Backend should include mapping: {mapping}")
            self.assertIn(mapping, auth_secrets_string,
                         f"Auth should include mapping: {mapping}")

        # Test real environment with these mappings
        with self.patch_environment(self.staging_env):
            try:
                # This should fail because the mappings aren't actually mounted
                jwt_manager = get_jwt_secret_manager()
                jwt_manager.clear_cache()

                secret = jwt_manager.get_jwt_secret()

                # If it succeeds, validate the mapping worked
                debug_info = jwt_manager.get_debug_info()
                logger.warning(f"Unexpected secret mapping success: {debug_info}")

            except (ImportError, ValueError) as e:
                # Expected failure - secret mappings not working
                logger.error(f"EXPECTED FAILURE: Secret mapping validation failed: {e}")
                raise

    async def test_staging_authentication_pipeline_end_to_end_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: End-to-end authentication pipeline in staging.

        This test validates the complete authentication flow from
        JWT secret retrieval through token validation in staging.
        """
        with self.patch_environment(self.staging_env):
            jwt_manager = get_jwt_secret_manager()
            jwt_manager.clear_cache()

            try:
                # Complete authentication pipeline test
                # 1. Get JWT secret from staging GSM
                secret = jwt_manager.get_jwt_secret()
                algorithm = jwt_manager.get_jwt_algorithm()

                # 2. Validate configuration
                validation = jwt_manager.validate_jwt_configuration()
                self.assertTrue(validation['valid'],
                              f"Staging JWT config should be valid: {validation}")

                # 3. Create authentication token
                import jwt as pyjwt

                auth_payload = {
                    "user_id": "staging_test_user",
                    "email": "test@staging.netra.ai",
                    "roles": ["user"],
                    "environment": "staging",
                    "exp": int(time.time()) + 3600,
                    "iat": int(time.time())
                }

                auth_token = pyjwt.encode(auth_payload, secret, algorithm=algorithm)

                # 4. Validate authentication token
                decoded_payload = pyjwt.decode(auth_token, secret, algorithms=[algorithm])

                self.assertEqual(decoded_payload["environment"], "staging",
                               "Token should preserve staging environment")
                self.assertEqual(decoded_payload["user_id"], "staging_test_user",
                               "Token should preserve user identity")

                # 5. Test token refresh scenario
                refresh_payload = {**auth_payload, "iat": int(time.time())}
                refresh_token = pyjwt.encode(refresh_payload, secret, algorithm=algorithm)

                decoded_refresh = pyjwt.decode(refresh_token, secret, algorithms=[algorithm])
                self.assertEqual(decoded_refresh["user_id"], "staging_test_user",
                               "Refresh token should work with same secret")

                logger.warning(f"Unexpected end-to-end authentication success")

            except (ImportError, ValueError, Exception) as e:
                # Expected failure - authentication pipeline broken
                logger.error(f"EXPECTED FAILURE: End-to-end authentication failed: {e}")
                raise

    async def test_real_staging_deployment_environment_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Real staging deployment environment validation.

        This test attempts to validate JWT secrets in a real staging
        deployment environment, simulating actual GCP Cloud Run conditions.
        """
        # Simulate real staging deployment environment
        real_staging_env = {
            **self.staging_env,
            'GCLOUD_PROJECT': 'netra-staging',
            'GOOGLE_APPLICATION_CREDENTIALS': '/dev/null',  # Simulate no service account
            'DATABASE_URL': 'postgresql://staging-db',
            'REDIS_URL': 'redis://staging-redis:6379'
        }

        with self.patch_environment(real_staging_env):
            jwt_manager = get_jwt_secret_manager()
            jwt_manager.clear_cache()

            try:
                # This should work in real staging deployment
                secret = jwt_manager.get_jwt_secret()

                # Validate it meets production requirements
                is_valid, context = jwt_manager.validate_jwt_secret_for_environment(
                    secret, "staging"
                )
                self.assertTrue(is_valid,
                              f"Staging secret should be production-ready: {context}")

                # Test performance in deployment-like conditions
                start_time = time.time()
                for _ in range(10):
                    test_secret = jwt_manager.get_jwt_secret()
                    self.assertEqual(test_secret, secret,
                                   "Secret should be consistently cached")
                end_time = time.time()

                # Should be fast due to caching
                avg_time = (end_time - start_time) / 10
                self.assertLess(avg_time, 0.01,
                              f"Secret retrieval should be fast: {avg_time}s")

                logger.warning(f"Unexpected real staging deployment success")

            except (ImportError, ValueError) as e:
                # Expected failure - real staging environment not configured
                logger.error(f"EXPECTED FAILURE: Real staging deployment failed: {e}")
                raise

    def patch_environment(self, env_vars: Dict[str, str]):
        """Helper method to patch environment variables."""
        return self.patch('os.environ', env_vars)

    def tearDown(self):
        """Clean up after integration tests."""
        super().tearDown()

        # Clear any cached JWT secrets
        jwt_manager = get_jwt_secret_manager()
        jwt_manager.clear_cache()


if __name__ == '__main__':
    # Configure logging for integration test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run integration tests with detailed output
    pytest.main([__file__, '-v', '--tb=long'])