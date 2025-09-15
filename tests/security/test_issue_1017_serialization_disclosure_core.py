"""
Issue #1017 Security Vulnerability Tests: Serialization Information Disclosure - CORE VULNERABILITIES

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the serialization methods, specifically:
1. DeepAgentState.model_dump() exposing sensitive data
2. to_dict() methods leaking internal information

FOCUS: Core serialization vulnerabilities without complex dependencies
1. Serialization information disclosure (secrets exposed in to_dict())
2. Internal system information leakage
3. API key and credential exposure through serialization

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure with unittest compatibility
- Focuses on serialization methods specifically
- Simple test structure for clear vulnerability demonstration

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import uuid
import unittest
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState


class TestIssue1017SerializationDisclosureCore(SSotBaseTestCase, unittest.TestCase):
    """
    Core serialization information disclosure vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in serialization methods.

    FOCUS: Demonstrating that sensitive data placed in model fields
    gets exposed through serialization methods without proper filtering.
    """

    def setUp(self):
        """Setup for each test method - unittest style."""
        super().setUp()  # Calls SSOT setup_method automatically
        self._setup_vulnerability_test_context()

    def setup_method(self, method):
        """Setup for each test method - pytest style."""
        super().setup_method(method)
        self._setup_vulnerability_test_context()

    def _setup_vulnerability_test_context(self):
        """Common setup for vulnerability testing."""
        self.test_user_id = f"serial_vuln_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"serial_vuln_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"serial_vuln_run_{uuid.uuid4().hex[:8]}"

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "serialization_disclosure")

    def test_deepagentstate_model_dump_api_key_exposure(self):
        """
        Test that API keys in DeepAgentState are exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that API keys
        placed in various fields of DeepAgentState are exposed in
        model_dump() serialization without masking or filtering.
        """
        self.record_metric("vulnerability_subtype", "api_key_exposure")

        # Sensitive API keys that should be masked in serialization
        api_keys = [
            "sk-super_secret_openai_key_12345_should_not_leak",
            "xoxb-slack-token-that-should-be-protected-67890",
            "ghp_github_personal_access_token_abc123def456"
        ]

        for i, api_key in enumerate(api_keys):
            with self.subTest(api_key_index=i, key_type=api_key[:10]):

                # Create DeepAgentState with API key in various fields
                state_with_api_key = DeepAgentState(
                    user_request="Process API configuration",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_api_{i}",
                    agent_input={
                        "api_key": api_key,
                        "auth_config": {
                            "token": api_key,
                            "secret": api_key
                        },
                        "credentials": api_key
                    },
                    final_report=f"Analysis completed using API key: {api_key}"
                )

                # Use model_dump() to get serialized representation
                serialized_state = state_with_api_key.model_dump()

                # VULNERABILITY CHECK: API key should be masked/filtered
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(api_key, str(serialized_state),
                    f"VULNERABILITY: API key '{api_key}' was exposed in model_dump() serialization")

                # Check specific fields that might contain the API key
                sensitive_fields = ["agent_input", "final_report"]
                for field_name in sensitive_fields:
                    if field_name in serialized_state:
                        field_content = str(serialized_state[field_name])
                        self.assertNotIn(api_key, field_content,
                            f"VULNERABILITY: API key '{api_key}' was exposed in {field_name} field")

    def test_deepagentstate_model_dump_database_credential_exposure(self):
        """
        Test that database credentials in DeepAgentState are exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that database credentials
        placed in DeepAgentState fields are exposed in serialization.
        """
        self.record_metric("vulnerability_subtype", "database_credential_exposure")

        # Database credentials that should be masked
        db_credentials = [
            "postgresql://admin:super_secret_pass@prod-db:5432/sensitive_db",
            "mongodb://user:ultra_secret_mongo@cluster.mongodb.net/prod",
            "mysql://root:database_password_123@localhost:3306/production"
        ]

        for i, db_cred in enumerate(db_credentials):
            with self.subTest(db_index=i, db_type=db_cred.split("://")[0]):

                # Create DeepAgentState with database credentials
                state_with_db = DeepAgentState(
                    user_request="Connect to database",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_db_{i}",
                    agent_input={
                        "database_url": db_cred,
                        "connection_string": db_cred,
                        "db_config": {
                            "url": db_cred,
                            "connection": db_cred
                        }
                    }
                )

                # Serialize the state
                serialized_state = state_with_db.model_dump()

                # VULNERABILITY CHECK: Database credentials should be masked
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(db_cred, str(serialized_state),
                    f"VULNERABILITY: Database credential '{db_cred}' was exposed in model_dump() serialization")

                # Check for password patterns specifically
                if ":" in db_cred and "@" in db_cred:
                    # Extract potential password from connection string
                    try:
                        # Basic pattern: protocol://user:password@host
                        password_part = db_cred.split("://")[1].split("@")[0].split(":")[1]
                        if len(password_part) > 3:  # Only check meaningful passwords
                            self.assertNotIn(password_part, str(serialized_state),
                                f"VULNERABILITY: Database password '{password_part}' was exposed in serialization")
                    except IndexError:
                        pass  # Skip if pattern doesn't match

    def test_deepagentstate_model_dump_jwt_secret_exposure(self):
        """
        Test that JWT secrets in DeepAgentState are exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that JWT secrets
        are exposed in serialization without proper protection.
        """
        self.record_metric("vulnerability_subtype", "jwt_secret_exposure")

        # JWT secrets that should be protected
        jwt_secrets = [
            "jwt_signing_secret_key_that_should_never_leak_12345",
            "HS256_secret_for_production_jwt_tokens_67890",
            "ultra_secure_jwt_secret_for_enterprise_abc123"
        ]

        for i, jwt_secret in enumerate(jwt_secrets):
            with self.subTest(jwt_index=i):

                # Create DeepAgentState with JWT secret
                state_with_jwt = DeepAgentState(
                    user_request="Validate JWT token",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_jwt_{i}",
                    agent_input={
                        "jwt_secret": jwt_secret,
                        "auth_config": {
                            "secret_key": jwt_secret,
                            "signing_key": jwt_secret
                        },
                        "security": {
                            "jwt": {
                                "secret": jwt_secret
                            }
                        }
                    }
                )

                # Serialize the state
                serialized_state = state_with_jwt.model_dump()

                # VULNERABILITY CHECK: JWT secret should be masked
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(jwt_secret, str(serialized_state),
                    f"VULNERABILITY: JWT secret '{jwt_secret}' was exposed in model_dump() serialization")

    def test_deepagentstate_model_dump_internal_system_exposure(self):
        """
        Test that internal system information is exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that internal system
        details placed in DeepAgentState are exposed without filtering.
        """
        self.record_metric("vulnerability_subtype", "internal_system_exposure")

        # Internal system information that should be filtered
        internal_data = {
            "internal_api_endpoint": "http://internal-admin.netra.com/secret-api",
            "debug_token": "debug_access_token_for_internal_systems_only",
            "system_key": "internal_system_coordination_key_xyz789",
            "monitoring_secret": "prometheus_internal_scraping_secret_abc123"
        }

        for secret_type, secret_value in internal_data.items():
            with self.subTest(secret_type=secret_type):

                # Create DeepAgentState with internal system data
                state_with_internal = DeepAgentState(
                    user_request="System diagnostic request",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_internal",
                    agent_input={
                        "system_config": {
                            secret_type: secret_value
                        },
                        "internal_data": secret_value,
                        "debug_info": {
                            "internal_endpoint": secret_value,
                            "system_token": secret_value
                        }
                    }
                )

                # Serialize the state
                serialized_state = state_with_internal.model_dump()

                # VULNERABILITY CHECK: Internal system data should be filtered
                # This assertion should FAIL to prove vulnerability exists
                self.assertNotIn(secret_value, str(serialized_state),
                    f"VULNERABILITY: Internal system data '{secret_type}': '{secret_value}' was exposed in model_dump() serialization")

                # Check for internal endpoint patterns
                if "internal" in secret_value and "http" in secret_value:
                    self.assertNotIn("internal-admin", str(serialized_state),
                        f"VULNERABILITY: Internal admin endpoint pattern exposed in serialization")

    def test_deepagentstate_model_dump_environment_variable_exposure(self):
        """
        Test that environment variables are exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that environment variables
        containing sensitive data can be exposed through state serialization.
        """
        self.record_metric("vulnerability_subtype", "environment_variable_exposure")

        # Simulate environment variables with sensitive data
        env_sensitive_data = {
            "DATABASE_PASSWORD": "env_db_password_should_not_leak_123",
            "API_SECRET_KEY": "env_api_secret_should_be_protected_456",
            "ENCRYPTION_KEY": "env_encryption_key_private_data_789"
        }

        with self.temp_env_vars(**env_sensitive_data):

            for env_name, env_value in env_sensitive_data.items():
                with self.subTest(env_var=env_name):

                    # Create state that might capture environment variables
                    state_with_env = DeepAgentState(
                        user_request="Process environment configuration",
                        user_id=self.test_user_id,
                        chat_thread_id=self.test_thread_id,
                        run_id=f"{self.test_run_id}_env",
                        agent_input={
                            "env_config": {
                                "captured_env": env_value,  # Direct capture
                                "env_reference": f"Using {env_name}: {env_value}"  # Indirect capture
                            },
                            "system_vars": {
                                env_name: env_value
                            }
                        }
                    )

                    # Serialize the state
                    serialized_state = state_with_env.model_dump()

                    # VULNERABILITY CHECK: Environment variable values should not be exposed
                    # This assertion should FAIL to prove vulnerability exists
                    self.assertNotIn(env_value, str(serialized_state),
                        f"VULNERABILITY: Environment variable {env_name} value '{env_value}' was exposed in model_dump() serialization")

    def test_deepagentstate_model_dump_nested_secret_exposure(self):
        """
        Test that secrets in deeply nested structures are exposed through model_dump().

        EXPECTS TO FAIL: This test should demonstrate that secrets in nested
        data structures within DeepAgentState are exposed without filtering.
        """
        self.record_metric("vulnerability_subtype", "nested_secret_exposure")

        # Nested secret that should be protected at any depth
        nested_secret = "deeply_nested_secret_that_must_be_protected_xyz789"

        # Create deeply nested structure with secret
        nested_structure = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret_data": nested_secret,
                        "credentials": {
                            "api_key": nested_secret,
                            "token": nested_secret
                        }
                    }
                }
            },
            "config": {
                "auth": {
                    "secrets": {
                        "primary": nested_secret,
                        "backup": nested_secret
                    }
                }
            }
        }

        # Create DeepAgentState with nested secret
        state_with_nested = DeepAgentState(
            user_request="Process nested configuration",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_nested",
            agent_input=nested_structure
        )

        # Serialize the state
        serialized_state = state_with_nested.model_dump()

        # VULNERABILITY CHECK: Nested secret should be filtered regardless of depth
        # This assertion should FAIL to prove vulnerability exists
        self.assertNotIn(nested_secret, str(serialized_state),
            f"VULNERABILITY: Deeply nested secret '{nested_secret}' was exposed in model_dump() serialization")

        # Check that the nested structure was preserved (but secret filtered)
        self.assertIn("level1", str(serialized_state),
            "INTERNAL ERROR: Nested structure not found - test may be invalid")

    def test_deepagentstate_multiple_serialization_methods_exposure(self):
        """
        Test that secrets are exposed through multiple serialization methods.

        EXPECTS TO FAIL: This test should demonstrate that secrets are exposed
        through various serialization methods (model_dump, model_dump_json, etc.).
        """
        self.record_metric("vulnerability_subtype", "multiple_serialization_methods")

        secret_value = "multi_method_secret_should_be_protected_abc123"

        # Create DeepAgentState with secret
        state_with_secret = DeepAgentState(
            user_request="Test multiple serialization methods",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=f"{self.test_run_id}_multi",
            agent_input={
                "secret": secret_value,
                "config": {
                    "auth_token": secret_value
                }
            }
        )

        # Test different serialization methods
        serialization_methods = [
            ("model_dump", lambda: state_with_secret.model_dump()),
            ("model_dump_json", lambda: state_with_secret.model_dump_json()),
            ("dict_conversion", lambda: dict(state_with_secret.model_dump()))
        ]

        for method_name, method_func in serialization_methods:
            with self.subTest(serialization_method=method_name):

                try:
                    # Get serialized result
                    serialized_result = method_func()
                    result_str = str(serialized_result)

                    # VULNERABILITY CHECK: Secret should be masked in all methods
                    # This assertion should FAIL to prove vulnerability exists
                    self.assertNotIn(secret_value, result_str,
                        f"VULNERABILITY: Secret '{secret_value}' was exposed via {method_name} serialization method")

                except Exception as e:
                    # If serialization fails, that might be a security feature
                    # But we should still be able to test the basic methods
                    if method_name in ["model_dump"]:  # Core methods should work
                        self.fail(f"Core serialization method {method_name} failed: {e}")

    def tearDown(self):
        """Cleanup after each test method - unittest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_serialization_disclosure_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))

        finally:
            super().tearDown()  # Calls SSOT teardown_method automatically

    def teardown_method(self, method):
        """Cleanup after each test method - pytest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_serialization_disclosure_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))

        finally:
            super().teardown_method(method)