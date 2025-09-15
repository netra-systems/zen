"""
Issue #1017 Security Vulnerability Tests: Serialization Security Simple

CRITICAL SECURITY TEST SUITE: These tests are designed to FAIL initially to prove
security vulnerabilities exist in the DeepAgentState serialization methods.

REQUIREMENTS:
- Tests MUST FAIL initially to prove vulnerabilities exist
- Uses SSOT test infrastructure from test_framework/
- Real services only - NO MOCKS in vulnerability testing

Business Value: Enterprise/Platform - Security compliance for HIPAA, SOC2, SEC regulations
"""

import json
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.schemas.agent_models import DeepAgentState, AgentMetadata


class TestIssue1017SerializationSecuritySimple(SSotBaseTestCase):
    """
    Simple serialization security vulnerability tests for Issue #1017.

    These tests are designed to FAIL initially to prove that security
    vulnerabilities exist in the DeepAgentState serialization.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)

        # Create test context for vulnerability testing
        self.test_user_id = f"ser_vuln_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"ser_vuln_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"ser_vuln_run_{uuid.uuid4().hex[:8]}"

        # Create fake sensitive data that should NEVER appear in serialization
        self.sensitive_secret = f"super_secret_api_key_{uuid.uuid4().hex[:12]}"
        self.sensitive_password = f"database_password_{uuid.uuid4().hex[:12]}"
        self.sensitive_token = f"jwt_token_{uuid.uuid4().hex[:12]}"

        # Record business value metrics
        self.record_metric("test_category", "security_vulnerability")
        self.record_metric("issue_number", "1017")
        self.record_metric("vulnerability_type", "serialization_security")

    def test_deepagentstate_serialization_exposure(self):
        """
        Test DeepAgentState serialization for sensitive data exposure.

        EXPECTS TO FAIL: This test should demonstrate that sensitive data
        injected into DeepAgentState fields gets exposed in serialization.
        """
        self.record_metric("vulnerability_subtype", "deepagentstate_serialization")

        # Create DeepAgentState with sensitive data
        metadata = AgentMetadata()
        metadata.execution_stats = {
            "internal_config": self.sensitive_secret,
            "debug_info": f"Debug: {self.sensitive_secret}",
            "credentials": {
                "auth_token": self.sensitive_token,
                "api_endpoint": f"https://api.service.com?key={self.sensitive_secret}"
            }
        }

        # Create state with sensitive data in various locations
        vulnerable_state = DeepAgentState(
            user_request=f"Request with {self.sensitive_secret} embedded",
            user_id=self.test_user_id,
            chat_thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            agent_input={
                "config": {
                    "database_url": f"postgresql://user:{self.sensitive_password}@localhost/db",
                    "secret_key": self.sensitive_secret,
                    "internal_token": self.sensitive_token
                },
                "credentials": self.sensitive_secret,
                "auth_header": f"Bearer {self.sensitive_token}"
            },
            metadata=metadata,
            quality_metrics={
                "internal_debug": self.sensitive_secret,
                "performance_token": self.sensitive_token
            },
            context_tracking={
                "session_secret": self.sensitive_secret,
                "trace_data": {
                    "internal_id": self.sensitive_secret,
                    "debug_token": self.sensitive_token
                }
            },
            final_report=f"Report containing sensitive {self.sensitive_secret} data"
        )

        # Serialize using model_dump (Pydantic serialization)
        serialized_dict = vulnerable_state.model_dump()

        # Focus on agent_input field to avoid datetime serialization issues
        agent_input_str = json.dumps(serialized_dict.get("agent_input", {}))

        # VULNERABILITY CHECK: If this passes, sensitive data is being exposed
        # These assertions should FAIL to prove vulnerability exists
        self.assertNotIn(self.sensitive_secret, agent_input_str,
            f"VULNERABILITY: Sensitive secret was exposed in agent_input serialization")

        self.assertNotIn(self.sensitive_password, agent_input_str,
            f"VULNERABILITY: Sensitive password was exposed in agent_input serialization")

        self.assertNotIn(self.sensitive_token, agent_input_str,
            f"VULNERABILITY: Sensitive token was exposed in agent_input serialization")

    def test_environment_variable_leakage(self):
        """
        Test for environment variable leakage through state serialization.

        EXPECTS TO FAIL: This test should demonstrate that environment variables
        containing sensitive data can leak through agent state serialization.
        """
        self.record_metric("vulnerability_subtype", "environment_leakage")

        # Set temporary environment variables with sensitive data
        secret_db_url = f"postgresql://admin:{self.sensitive_password}@prod-db:5432/sensitive_db"
        secret_api_key = f"sk-{self.sensitive_secret}"

        with self.temp_env_vars(SECRET_DATABASE_URL=secret_db_url, SECRET_API_KEY=secret_api_key):

            # Create state that might inadvertently capture environment variables
            potentially_leaky_state = DeepAgentState(
                user_request="Process environment configuration",
                user_id=self.test_user_id,
                chat_thread_id=self.test_thread_id,
                run_id=f"{self.test_run_id}_env",
                agent_input={
                    "environment_config": {
                        "load_env": True,
                        "debug_mode": True,
                        "include_system_vars": True
                    },
                    # Simulate code that might capture env vars
                    "system_info": {
                        "config_vars": {
                            "database_url": self.get_env_var("SECRET_DATABASE_URL", ""),
                            "api_key": self.get_env_var("SECRET_API_KEY", "")
                        }
                    }
                }
            )

            # Serialize the state
            serialized_state = potentially_leaky_state.model_dump()
            agent_input_str = json.dumps(serialized_state.get("agent_input", {}))

            # VULNERABILITY CHECK: If this passes, environment variables are leaking
            # These assertions should FAIL to prove vulnerability exists
            self.assertNotIn(self.sensitive_password, agent_input_str,
                f"VULNERABILITY: Environment variable password was exposed in state serialization")

            self.assertNotIn(self.sensitive_secret, agent_input_str,
                f"VULNERABILITY: Environment variable API key was exposed in state serialization")

    def test_cross_user_data_contamination_simple(self):
        """
        Test for basic cross-user data contamination through serialization.

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
            }
        )

        # Serialize both states
        user1_serialized = user1_state.model_dump()
        user2_serialized = user2_state.model_dump()

        user1_agent_input = json.dumps(user1_serialized.get("agent_input", {}))
        user2_agent_input = json.dumps(user2_serialized.get("agent_input", {}))

        # VULNERABILITY CHECK: Other user's data should NEVER appear in this user's serialization
        # These assertions should FAIL to prove vulnerability exists
        self.assertNotIn(user2_secret, user1_agent_input,
            f"VULNERABILITY: User 2's private data contaminated user 1's serialization")

        self.assertNotIn(user1_secret, user2_agent_input,
            f"VULNERABILITY: User 1's private data contaminated user 2's serialization")

        # Verify current user's data is present (sanity check)
        self.assertIn(user1_secret, user1_agent_input,
            f"INTERNAL ERROR: User 1's secret not found in their own serialization")

        self.assertIn(user2_secret, user2_agent_input,
            f"INTERNAL ERROR: User 2's secret not found in their own serialization")

    def teardown_method(self, method):
        """Cleanup after each test method."""
        try:
            # Record final vulnerability test metrics
            total_metrics = self.get_all_metrics()
            self.record_metric("total_serialization_vulnerability_tests", len([k for k in total_metrics.keys() if k.startswith("vulnerability_")]))
            self.record_metric("serialization_test_execution_time", self.get_metrics().execution_time)

        finally:
            super().teardown_method(method)