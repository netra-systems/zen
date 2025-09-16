"""
Issue #1017 Security Vulnerability Tests: Serialization Security - FIXED VERSION

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the DeepAgentState to_dict() method and related
serialization processes.

ENHANCEMENTS OVER ORIGINAL:
1. Proper SSOT inheritance with unittest compatibility for subTest functionality
2. Fixed test infrastructure issues
3. Clear vulnerability demonstration with failing assertions
4. Real services only - NO MOCKS in vulnerability testing

These tests specifically target:
1. Sensitive data exposure in to_dict() method serialization
2. Internal credentials leak prevention validation
3. JWT secret protection in serialized output
4. Database credential protection in state serialization
5. API key exposure through serialization
6. Environment variable leakage detection
7. Cross-user data contamination through serialization

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure from test_framework/ with unittest compatibility
- Real services only - NO MOCKS in vulnerability testing
- Follows testing best practices from reports/testing/TEST_CREATION_GUIDE.md

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import os
import uuid
import unittest
from typing import Any, Dict, List

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState, AgentMetadata
from netra_backend.app.models.agent_execution import AgentExecution


class TestIssue1017SerializationSecurityFixed(SSotBaseTestCase, unittest.TestCase):
    """
    FIXED VERSION: Comprehensive serialization security vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in the DeepAgentState serialization and to_dict() methods.

    INFRASTRUCTURE FIXES:
    - Inherits from both SSotBaseTestCase and unittest.TestCase for full functionality
    - Provides subTest() functionality from unittest
    - Maintains SSOT environment isolation and metrics
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
        # Create test context for vulnerability testing
        self.test_user_id = f"ser_vuln_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"ser_vuln_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"ser_vuln_run_{uuid.uuid4().hex[:8]}"

        # Create fake sensitive data that should NEVER appear in serialization
        self.sensitive_secrets = {
            "database_password": "super_secret_db_pass_12345",
            "jwt_secret": "ultra_secret_jwt_key_67890",
            "api_key": "sk-secret_openai_key_abcdef123456789",
            "aws_secret": "aws_secret_access_key_xyz789",
            "stripe_secret": "sk_live_secret_stripe_key_123",
            "internal_auth_token": "internal_auth_token_should_never_leak",
            "encryption_key": "aes256_encryption_key_private_data",
            "webhook_secret": "webhook_signing_secret_protected"
        }

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "serialization_security")

    def test_deepagentstate_to_dict_sensitive_data_exposure(self):
        """
        Test DeepAgentState.model_dump() for sensitive data exposure.

        EXPECTS TO FAIL: This test should demonstrate that sensitive data
        injected into DeepAgentState fields gets exposed in serialization.
        """
        self.record_metric("vulnerability_subtype", "deepagentstate_serialization")

        # Test each sensitive secret individually to isolate vulnerabilities
        for secret_name, secret_value in self.sensitive_secrets.items():
            with self.subTest(secret_type=secret_name):

                # Inject sensitive data into multiple fields
                agent_metadata = AgentMetadata()
                agent_metadata.execution_context = {
                    "internal_config": secret_value,
                    "debug_info": f"Debug: {secret_value}",
                    "credentials": secret_value
                }
                agent_metadata.custom_fields = {
                    "auth_token": secret_value,
                    "api_endpoint": f"https://api.service.com?key={secret_value}"
                }

                # Create state with sensitive data in various locations
                vulnerable_state = DeepAgentState(
                    user_request=f"Request with {secret_value} embedded",
                    user_id=self.test_user_id,
                    chat_thread_id=self.test_thread_id,
                    run_id=f"{self.test_run_id}_{secret_name}",
                    agent_input={
                        "config": {
                            "database_url": f"postgresql://user:{secret_value}@localhost/db",
                            "secret_key": secret_value,
                            "internal_token": secret_value
                        },
                        "credentials": secret_value,
                        "auth_header": f"Bearer {secret_value}"
                    },
                    metadata=agent_metadata,
                    quality_metrics={
                        "internal_debug": secret_value,
                        "performance_token": secret_value
                    },
                    context_tracking={
                        "session_secret": secret_value,
                        "trace_data": {
                            "internal_id": secret_value,
                            "debug_token": secret_value
                        }
                    },
                    final_report=f"Report containing sensitive {secret_value} data"
                )

                # Serialize using model_dump (Pydantic serialization)
                serialized_dict = vulnerable_state.model_dump()
                serialized_json = json.dumps(serialized_dict, indent=2)

                # VULNERABILITY CHECK: If this passes, sensitive data is being exposed
                # These assertions should FAIL to prove vulnerability exists
                self.assertNotIn(secret_value, serialized_json,
                    f"VULNERABILITY: Sensitive {secret_name} value '{secret_value}' was exposed in model_dump() serialization")

                # Check specific fields that commonly leak sensitive data
                sensitive_fields = ["agent_input", "metadata", "quality_metrics", "context_tracking", "final_report"]
                for field_name in sensitive_fields:
                    if field_name in serialized_dict:
                        field_json = json.dumps(serialized_dict[field_name])
                        self.assertNotIn(secret_value, field_json,
                            f"VULNERABILITY: Sensitive {secret_name} value '{secret_value}' was exposed in '{field_name}' field")

                # Check for partial secret exposure (first/last chars)
                if len(secret_value) > 8:
                    # Allow for proper masking patterns like "sk-****" or "***xyz789"
                    # But catch full or near-full exposure
                    full_secret_indicators = [
                        secret_value[:-1],  # Missing only last char
                        secret_value[1:],   # Missing only first char
                        secret_value[:-2],  # Missing only last 2 chars
                        secret_value[2:],   # Missing only first 2 chars
                    ]

                    for indicator in full_secret_indicators:
                        if len(indicator) > 6:  # Only check for meaningful lengths
                            self.assertNotIn(indicator, serialized_json,
                                f"VULNERABILITY: Near-complete {secret_name} value '{indicator}' was exposed (insufficient masking)")

    def test_agentexecution_to_dict_credential_exposure(self):
        """
        Test AgentExecution.to_dict() for credential exposure vulnerability.

        EXPECTS TO FAIL: This test should demonstrate that sensitive credentials
        in AgentExecution model get exposed through to_dict() serialization.
        """
        self.record_metric("vulnerability_subtype", "agentexecution_serialization")

        for secret_name, secret_value in self.sensitive_secrets.items():
            with self.subTest(secret_type=secret_name):

                # Create AgentExecution with sensitive data
                execution = AgentExecution.create_execution_record(
                    user_id=self.test_user_id,
                    agent_id="vulnerable_agent",
                    input_data={
                        "api_credentials": {
                            "key": secret_value,
                            "token": secret_value,
                            "secret": secret_value
                        },
                        "database_config": {
                            "password": secret_value,
                            "connection_string": f"Server=localhost;Database=test;User Id=admin;Password={secret_value};"
                        },
                        "service_auth": secret_value
                    },
                    thread_id=self.test_thread_id,
                    workflow_id=f"workflow_{secret_name}",
                    execution_context={
                        "internal_auth": secret_value,
                        "system_token": secret_value,
                        "debug_credentials": {
                            "admin_key": secret_value,
                            "service_secret": secret_value
                        }
                    }
                )

                # Mark as completed with sensitive output data
                execution.mark_completed(
                    output_data={
                        "result": "Success",
                        "internal_data": {
                            "auth_token": secret_value,
                            "refresh_token": secret_value,
                            "session_key": secret_value
                        },
                        "debug_info": f"Processed with key: {secret_value}"
                    }
                )

                # Serialize using to_dict()
                execution_dict = execution.to_dict()
                execution_json = json.dumps(execution_dict, indent=2)

                # VULNERABILITY CHECK: If this passes, credentials are being exposed
                # These assertions should FAIL to prove vulnerability exists
                self.assertNotIn(secret_value, execution_json,
                    f"VULNERABILITY: Sensitive {secret_name} credential '{secret_value}' was exposed in AgentExecution.to_dict()")

                # Check specific sensitive fields
                sensitive_execution_fields = ["input_data", "output_data", "execution_context"]
                for field_name in sensitive_execution_fields:
                    if field_name in execution_dict and execution_dict[field_name]:
                        field_json = json.dumps(execution_dict[field_name])
                        self.assertNotIn(secret_value, field_json,
                            f"VULNERABILITY: Sensitive {secret_name} credential '{secret_value}' was exposed in AgentExecution.{field_name}")

    def test_environment_variable_leakage_in_serialization(self):
        """
        Test for environment variable leakage through state serialization.

        EXPECTS TO FAIL: This test should demonstrate that environment variables
        containing sensitive data can leak through agent state serialization.
        """
        self.record_metric("vulnerability_subtype", "environment_leakage")

        # Set temporary environment variables with sensitive data
        env_secrets = {
            "SECRET_DATABASE_URL": "postgresql://admin:super_secret_pass@prod-db:5432/sensitive_db",
            "OPENAI_API_KEY": "sk-super_secret_openai_key_that_should_not_leak_12345",
            "JWT_SECRET_KEY": "ultra_secret_jwt_signing_key_for_production_67890",
            "AWS_SECRET_ACCESS_KEY": "aws_secret_access_key_production_environment_xyz789",
            "STRIPE_WEBHOOK_SECRET": "whsec_stripe_webhook_secret_that_must_be_protected_abc123"
        }

        with self.temp_env_vars(**env_secrets):

            for env_name, env_value in env_secrets.items():
                with self.subTest(env_var=env_name):

                    # Create state that might inadvertently capture environment variables
                    potentially_leaky_state = DeepAgentState(
                        user_request="Process environment configuration",
                        user_id=self.test_user_id,
                        chat_thread_id=self.test_thread_id,
                        run_id=f"{self.test_run_id}_env_{env_name}",
                        agent_input={
                            "environment_config": {
                                "load_env": True,
                                "debug_mode": True,
                                "include_system_vars": True
                            },
                            # Simulate code that might capture env vars
                            "system_info": {
                                "env_dump": str(dict(os.environ)),  # DANGEROUS: dumps all env vars
                                "process_env": os.environ.copy(),    # DANGEROUS: captures env
                                "config_vars": {
                                    "database_url": os.environ.get("SECRET_DATABASE_URL", ""),
                                    "api_key": os.environ.get("OPENAI_API_KEY", ""),
                                    "jwt_secret": os.environ.get("JWT_SECRET_KEY", "")
                                }
                            }
                        },
                        metadata=AgentMetadata(),
                        context_tracking={
                            "system_context": {
                                "environment_snapshot": dict(os.environ),
                                "runtime_config": {
                                    key: value for key, value in os.environ.items()
                                    if key.startswith(('SECRET_', 'API_', 'JWT_', 'AWS_', 'STRIPE_'))
                                }
                            }
                        }
                    )

                    # Serialize the state
                    serialized_state = potentially_leaky_state.model_dump()
                    serialized_json = json.dumps(serialized_state, indent=2)

                    # VULNERABILITY CHECK: If this passes, environment variables are leaking
                    # These assertions should FAIL to prove vulnerability exists
                    self.assertNotIn(env_value, serialized_json,
                        f"VULNERABILITY: Environment variable {env_name} value '{env_value}' was exposed in state serialization")

                    # Check for environment variable names that might indicate structure leakage
                    self.assertNotIn(env_name, serialized_json,
                        f"VULNERABILITY: Environment variable name '{env_name}' was exposed, indicating potential structure leakage")

    def test_cross_user_data_contamination_in_serialization(self):
        """
        Test for cross-user data contamination through shared serialization.

        EXPECTS TO FAIL: This test should demonstrate that data from one user
        can contaminate another user's serialized state.
        """
        self.record_metric("vulnerability_subtype", "cross_user_contamination")

        # Create two different users with sensitive data
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"

        user1_secret = f"user1_private_data_{uuid.uuid4().hex[:12]}"
        user2_secret = f"user2_private_data_{uuid.uuid4().hex[:12]}"

        # Create state for user 1 with their private data
        user1_state = DeepAgentState(
            user_request="User 1 private request",
            user_id=user1_id,
            chat_thread_id=f"thread_{user1_id}",
            run_id=f"run_{user1_id}",
            agent_input={
                "private_data": user1_secret,
                "user_specific_config": {
                    "personal_api_key": user1_secret,
                    "private_settings": user1_secret
                }
            },
            context_tracking={
                "user_session": {
                    "private_token": user1_secret,
                    "sensitive_context": user1_secret
                }
            }
        )

        # Create state for user 2 with their private data
        user2_state = DeepAgentState(
            user_request="User 2 private request",
            user_id=user2_id,
            chat_thread_id=f"thread_{user2_id}",
            run_id=f"run_{user2_id}",
            agent_input={
                "private_data": user2_secret,
                "user_specific_config": {
                    "personal_api_key": user2_secret,
                    "private_settings": user2_secret
                }
            },
            context_tracking={
                "user_session": {
                    "private_token": user2_secret,
                    "sensitive_context": user2_secret
                }
            }
        )

        # Simulate potential shared serialization or caching scenario
        states_list = [user1_state, user2_state]

        for i, state in enumerate(states_list):
            current_user = user1_id if i == 0 else user2_id
            other_user = user2_id if i == 0 else user1_id
            current_secret = user1_secret if i == 0 else user2_secret
            other_secret = user2_secret if i == 0 else user1_secret

            with self.subTest(user=current_user):

                # Serialize the current user's state
                serialized_state = state.model_dump()
                serialized_json = json.dumps(serialized_state, indent=2)

                # VULNERABILITY CHECK: Other user's data should NEVER appear in this user's serialization
                # These assertions should FAIL to prove vulnerability exists
                self.assertNotIn(other_secret, serialized_json,
                    f"VULNERABILITY: User {other_user}'s private data '{other_secret}' contaminated user {current_user}'s serialization")

                self.assertNotIn(other_user, serialized_json,
                    f"VULNERABILITY: Other user ID '{other_user}' appeared in user {current_user}'s serialization")

                # Verify current user's data is present (sanity check)
                self.assertIn(current_user, serialized_json,
                    f"INTERNAL ERROR: Current user ID '{current_user}' missing from their own serialization")

    def test_json_serialization_information_disclosure(self):
        """
        Test for information disclosure through JSON serialization methods.

        EXPECTS TO FAIL: This test should demonstrate that internal system
        information gets disclosed through various serialization methods.
        """
        self.record_metric("vulnerability_subtype", "json_serialization_disclosure")

        # Create state with internal system information that should be filtered
        internal_secrets = {
            "internal_database_config": {
                "admin_password": "internal_admin_pass_123",
                "maintenance_key": "maint_key_xyz789",
                "backup_credentials": "backup_creds_abc456"
            },
            "system_debugging": {
                "internal_api_endpoint": "http://internal.netra.com/admin/api",
                "debug_token": "debug_token_should_not_be_exposed",
                "system_health_key": "health_check_secret_key"
            },
            "service_mesh_config": {
                "inter_service_auth": "service_mesh_auth_token_secret",
                "monitoring_endpoint": "http://internal-prometheus.netra.com/metrics?token=secret",
                "trace_collector_key": "trace_collector_secret_key"
            }
        }

        system_state = DeepAgentState(
            user_request="System analysis request",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_input={
                "system_config": internal_secrets,
                "internal_state": internal_secrets,
                "debug_mode": True,
                "expose_internals": internal_secrets
            },
            metadata=AgentMetadata(),
            quality_metrics={
                "internal_performance": internal_secrets,
                "system_metrics": internal_secrets
            },
            context_tracking={
                "system_context": internal_secrets,
                "internal_traces": internal_secrets
            }
        )

        # Test multiple serialization methods
        serialization_methods = [
            ("model_dump", lambda s: s.model_dump()),
            ("model_dump_json", lambda s: s.model_dump_json()),
            ("json_dumps", lambda s: json.dumps(s.model_dump())),
            ("dict_conversion", lambda s: dict(s.model_dump()))
        ]

        for method_name, serialization_func in serialization_methods:
            with self.subTest(serialization_method=method_name):

                # Serialize using the current method
                try:
                    serialized_result = serialization_func(system_state)
                    if isinstance(serialized_result, (dict, list)):
                        serialized_json = json.dumps(serialized_result)
                    else:
                        serialized_json = str(serialized_result)
                except Exception as e:
                    # If serialization fails, that might be a security feature
                    continue

                # Check for exposure of internal secrets
                for category, secrets_dict in internal_secrets.items():
                    for secret_key, secret_value in secrets_dict.items():

                        # VULNERABILITY CHECK: Internal secrets should not be exposed
                        # These assertions should FAIL to prove vulnerability exists
                        self.assertNotIn(secret_value, serialized_json,
                            f"VULNERABILITY: Internal secret '{secret_key}' value '{secret_value}' exposed via {method_name} serialization")

                        # Check for internal endpoint exposure
                        if "internal" in secret_value and "http" in secret_value:
                            self.assertNotIn("internal.", serialized_json,
                                f"VULNERABILITY: Internal endpoint domain exposed via {method_name} serialization")

    def tearDown(self):
        """Cleanup after each test method - unittest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_serialization_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("serialization_test_execution_time", self.get_metrics().execution_time)

        finally:
            super().tearDown()  # Calls SSOT teardown_method automatically

    def teardown_method(self, method):
        """Cleanup after each test method - pytest style."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_serialization_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("serialization_test_execution_time", self.get_metrics().execution_time)

        finally:
            super().teardown_method(method)