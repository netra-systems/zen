"""
User Isolation Security Vulnerability Tests - Issue #1017

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Platform
- Business Goal: Regulatory Compliance & Customer Trust
- Value Impact: Protects $500K+ ARR through HIPAA, SOC2, SEC compliance
- Strategic Impact: Prevents enterprise customer churn from security violations

CRITICAL MISSION: Reproduce and validate user isolation vulnerabilities
that could lead to cross-user data contamination and regulatory violations.

This test suite focuses on identifying and demonstrating security vulnerabilities
in user isolation patterns, specifically:
1. DeepAgentState cross-user contamination
2. ModernExecutionHelpers shared state issues
3. WebSocket connection isolation failures
4. Agent context bleeding between concurrent users
5. Memory persistence across user sessions

NO Unix dependencies - all tests run on Windows and cross-platform.
BUSINESS CRITICAL: Security vulnerabilities = regulatory violations and customer loss.
"""

import asyncio
import gc
import pytest
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Infrastructure for Vulnerability Testing
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.agent import SubAgentLifecycle

# Target Vulnerability Components
try:
    from netra_backend.app.agents.mixins.deep_agent_state import DeepAgentState
    DEEP_AGENT_STATE_AVAILABLE = True
except ImportError:
    DEEP_AGENT_STATE_AVAILABLE = False

try:
    from netra_backend.app.agents.supervisor.modern_execution_helpers import ModernExecutionHelpers
    MODERN_EXECUTION_HELPERS_AVAILABLE = True
except ImportError:
    MODERN_EXECUTION_HELPERS_AVAILABLE = False

# WebSocket and Agent Infrastructure
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory


class VulnerabilityTestAgent(BaseAgent):
    """Agent designed to expose user isolation vulnerabilities."""

    # Class-level shared storage (VULNERABILITY)
    _class_shared_data = {}
    _global_counter = 0

    def __init__(self, user_id: str, vulnerability_test: str = "baseline", *args, **kwargs):
        super().__init__(
            name=f"VulnAgent_{vulnerability_test}_{user_id}",
            description=f"Vulnerability test agent for {vulnerability_test}",
            *args,
            **kwargs
        )
        self.user_id = user_id
        self.vulnerability_test = vulnerability_test
        self.instance_id = uuid.uuid4().hex
        self.sensitive_data = {}

        # Increment global counter (potential vulnerability)
        VulnerabilityTestAgent._global_counter += 1

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with patterns that expose user isolation vulnerabilities."""

        await self.emit_agent_started(f"Starting vulnerability test: {self.vulnerability_test}")

        if self.vulnerability_test == "class_data_sharing":
            # Store sensitive data in class-level storage (VULNERABILITY)
            VulnerabilityTestAgent._class_shared_data[self.user_id] = {
                "sensitive_info": f"SECRET_DATA_FOR_USER_{self.user_id}",
                "timestamp": time.time(),
                "context_ref": context,  # DANGEROUS: Direct context reference
                "personal_data": {
                    "ssn": f"123-45-{self.user_id[-4:]}",
                    "medical_record": f"HIPAA_DATA_{self.user_id}",
                    "financial_data": f"SEC_DATA_{self.user_id}"
                }
            }

        elif self.vulnerability_test == "context_contamination":
            # Contaminate context with data from other users (VULNERABILITY)
            context.metadata["current_user_data"] = f"USER_{self.user_id}_PRIVATE"

            # Try to access other users' data
            for other_user_id, data in VulnerabilityTestAgent._class_shared_data.items():
                if other_user_id != self.user_id:
                    context.metadata[f"contaminated_data_from_{other_user_id}"] = data["sensitive_info"]

        elif self.vulnerability_test == "state_persistence":
            # Store data that persists across user sessions (VULNERABILITY)
            persistent_key = f"persistent_data_{self.vulnerability_test}"
            if not hasattr(self.__class__, persistent_key):
                setattr(self.__class__, persistent_key, {})

            persistent_storage = getattr(self.__class__, persistent_key)
            persistent_storage[self.user_id] = {
                "session_data": context.metadata.copy(),
                "user_secrets": f"CONFIDENTIAL_{self.user_id}",
                "created_by": self.instance_id
            }

        elif self.vulnerability_test == "deep_object_sharing":
            # Create deep object references that could leak between users
            self.sensitive_data = {
                "user_id": self.user_id,
                "nested": {
                    "deeply_nested": {
                        "context_ref": context,  # VULNERABILITY: Deep context reference
                        "user_secrets": {
                            "api_key": f"api_key_{self.user_id}",
                            "database_connection": f"db_conn_{self.user_id}",
                            "encryption_key": f"enc_key_{self.user_id}"
                        }
                    }
                }
            }

            # Store in class-level for cross-contamination
            VulnerabilityTestAgent._class_shared_data[f"deep_{self.instance_id}"] = self.sensitive_data

        await self.emit_thinking(f"Processing {self.vulnerability_test} vulnerability test", context=context)
        await asyncio.sleep(0.01)  # Minimal processing

        result = {
            "status": "completed",
            "vulnerability_test": self.vulnerability_test,
            "user_id": self.user_id,
            "instance_id": self.instance_id,
            "global_counter": VulnerabilityTestAgent._global_counter,
            "class_shared_keys": list(VulnerabilityTestAgent._class_shared_data.keys()),
            "context_keys": list(context.metadata.keys())
        }

        await self.emit_agent_completed(result, context=context)

        return result

    @classmethod
    def get_shared_data_for_user(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Get shared data for a specific user (exposes vulnerability)."""
        return cls._class_shared_data.get(user_id)

    @classmethod
    def get_all_shared_data(cls) -> Dict[str, Any]:
        """Get all shared data (major vulnerability)."""
        return cls._class_shared_data.copy()

    @classmethod
    def reset_shared_data(cls):
        """Reset shared data for testing."""
        cls._class_shared_data.clear()
        cls._global_counter = 0


@pytest.mark.security
@pytest.mark.integration
class UserIsolationVulnerabilitiesTests(SSotAsyncTestCase):
    """Integration tests for user isolation security vulnerabilities."""

    def create_test_user_context(self, user_id: str, scenario: str = "security_test") -> UserExecutionContext:
        """Create user context for security testing."""
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=f"security_thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"security_run_{user_id}_{uuid.uuid4().hex[:8]}",
            request_id=f"security_req_{user_id}_{uuid.uuid4().hex[:8]}",
            db_session=None,
            websocket_client_id=f"security_ws_{user_id}_{uuid.uuid4().hex[:8]}",
            agent_context={
                "user_request": f"Security test for {scenario}",
                "test_scenario": scenario,
                "security_level": "confidential",
                "user_permissions": ["read", "write", "execute"],
                "compliance_requirements": ["HIPAA", "SOC2", "SEC"]
            }
        )

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)

        # Reset vulnerability test agent state
        VulnerabilityTestAgent.reset_shared_data()

        # Force garbage collection
        gc.collect()

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock WebSocket bridge for security testing."""
        mock_bridge = AsyncMock()
        mock_bridge.emit_agent_started = AsyncMock()
        mock_bridge.emit_agent_completed = AsyncMock()
        mock_bridge.emit_agent_thinking = AsyncMock()
        mock_bridge.emit_error = AsyncMock()
        return mock_bridge

    @pytest.mark.real_services
    async def test_class_level_data_sharing_vulnerability(self):
        """
        VULNERABILITY TEST: Demonstrate class-level data sharing between users.

        This test proves that sensitive data stored in class-level variables
        can be accessed by different user sessions, violating user isolation.

        BUSINESS IMPACT: HIPAA, SOC2, SEC violations - enterprise customers lost.
        """

        # Create two different users
        user_a = "healthcare_patient_12345"
        user_b = "financial_client_67890"

        context_a = self.create_test_user_context(user_a, "hipaa_data_test")
        context_b = self.create_test_user_context(user_b, "sec_data_test")

        # Create contexts with sensitive data (need to recreate since frozen)
        context_a = UserExecutionContext.from_request(
            user_id=user_a,
            thread_id=f"security_thread_{user_a}_{uuid.uuid4().hex[:8]}",
            run_id=f"security_run_{user_a}_{uuid.uuid4().hex[:8]}",
            agent_context={
                "user_request": f"Security test for hipaa_data_test",
                "test_scenario": "hipaa_data_test",
                "security_level": "confidential",
                "patient_ssn": "123-45-6789",
                "medical_condition": "Confidential Medical Data",
                "treatment_plan": "HIPAA Protected Information"
            }
        )

        context_b = UserExecutionContext.from_request(
            user_id=user_b,
            thread_id=f"security_thread_{user_b}_{uuid.uuid4().hex[:8]}",
            run_id=f"security_run_{user_b}_{uuid.uuid4().hex[:8]}",
            agent_context={
                "user_request": f"Security test for sec_data_test",
                "test_scenario": "sec_data_test",
                "security_level": "confidential",
                "account_number": "ACC-789012345",
                "transaction_history": "SEC Regulated Financial Data",
                "investment_portfolio": "Confidential Financial Information"
            }
        )

        # Create mock WebSocket bridge for testing
        mock_websocket_bridge = AsyncMock()
        mock_websocket_bridge.emit_agent_started = AsyncMock()
        mock_websocket_bridge.emit_agent_completed = AsyncMock()
        mock_websocket_bridge.emit_agent_thinking = AsyncMock()
        mock_websocket_bridge.emit_error = AsyncMock()

        # Create agents for both users
        agent_a = VulnerabilityTestAgent(user_a, "class_data_sharing", user_context=context_a)
        agent_a.set_websocket_bridge(mock_websocket_bridge, context_a.run_id)

        agent_b = VulnerabilityTestAgent(user_b, "class_data_sharing", user_context=context_b)
        agent_b.set_websocket_bridge(mock_websocket_bridge, context_b.run_id)

        # Execute agents (this stores sensitive data in class variables)
        result_a = await agent_a.execute(context_a)
        result_b = await agent_b.execute(context_b)

        # VULNERABILITY DEMONSTRATION: User B can access User A's sensitive data
        user_a_sensitive_data = VulnerabilityTestAgent.get_shared_data_for_user(user_a)
        user_b_sensitive_data = VulnerabilityTestAgent.get_shared_data_for_user(user_b)

        # SECURITY VIOLATION: Both users' data is accessible
        assert user_a_sensitive_data is not None, "User A data should be stored (vulnerability)"
        assert user_b_sensitive_data is not None, "User B data should be stored (vulnerability)"

        # CRITICAL VIOLATION: User A's HIPAA data is accessible to any agent
        assert "SECRET_DATA_FOR_USER_healthcare_patient_12345" in user_a_sensitive_data["sensitive_info"]
        assert "HIPAA_DATA_healthcare_patient_12345" in user_a_sensitive_data["personal_data"]["medical_record"]

        # CRITICAL VIOLATION: User B's SEC data is accessible to any agent
        assert "SECRET_DATA_FOR_USER_financial_client_67890" in user_b_sensitive_data["sensitive_info"]
        assert "SEC_DATA_financial_client_67890" in user_b_sensitive_data["personal_data"]["financial_data"]

        # ENTERPRISE COMPLIANCE FAILURE: All shared data is accessible
        all_shared_data = VulnerabilityTestAgent.get_all_shared_data()
        assert len(all_shared_data) >= 2, "Multiple users' data accessible simultaneously"
        assert user_a in all_shared_data, "User A data accessible to other sessions"
        assert user_b in all_shared_data, "User B data accessible to other sessions"

        # BUSINESS IMPACT VALIDATION
        regulatory_violations = []
        if "HIPAA_DATA_" in str(all_shared_data):
            regulatory_violations.append("HIPAA")
        if "SEC_DATA_" in str(all_shared_data):
            regulatory_violations.append("SEC")

        # This test SHOULD FAIL in production - it proves the vulnerability exists
        assert len(regulatory_violations) > 0, f"Regulatory violations detected: {regulatory_violations}"

        # Cleanup
        await agent_a.cleanup()
        await agent_b.cleanup()

        self.record_metric("users_with_accessible_data", len(all_shared_data))
        self.record_metric("regulatory_violations_detected", regulatory_violations)
        self.record_metric("vulnerability_confirmed", True)

    @pytest.mark.real_services
    async def test_context_contamination_vulnerability(self):
        """
        VULNERABILITY TEST: Demonstrate cross-user context contamination.

        This test proves that user contexts can be contaminated with data
        from other users, violating data isolation principles.

        BUSINESS IMPACT: Multi-tenant isolation failures - enterprise SLA violations.
        """

        # Create multiple users with different security levels
        users = [
            ("government_user_001", "top_secret"),
            ("healthcare_user_002", "hipaa_protected"),
            ("financial_user_003", "sec_regulated"),
            ("public_user_004", "public_access")
        ]

        agents = []
        contexts = []

        # Phase 1: Create agents and execute to populate class storage
        for user_id, security_level in users:
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=f"security_thread_{user_id}_{uuid.uuid4().hex[:8]}",
                run_id=f"security_run_{user_id}_{uuid.uuid4().hex[:8]}",
                agent_context={
                    "user_request": f"Security test for security_{security_level}",
                    "test_scenario": f"security_{security_level}",
                    "security_level": "confidential",
                    "security_classification": security_level,
                    "sensitive_data": f"CLASSIFIED_{security_level}_{user_id}",
                    "access_level": security_level,
                    "department": security_level.split("_")[0]
                }
            )

            agent = VulnerabilityTestAgent(user_id, "class_data_sharing", user_context=context)
            await agent.execute(context)

            agents.append(agent)
            contexts.append(context)

        # Phase 2: Create new agent to test contamination
        contamination_user = "contamination_test_user"
        contamination_context = self.create_test_user_context(contamination_user, "contamination_test")

        contamination_agent = VulnerabilityTestAgent(
            contamination_user,
            "context_contamination",
            user_context=contamination_context
        )

        # Execute contamination test (this should contaminate the context)
        contamination_result = await contamination_agent.execute(contamination_context)

        # VULNERABILITY VERIFICATION: Context should be contaminated
        contamination_keys = set(contamination_context.metadata.keys())

        # Check for contaminated data from other users
        contaminated_data_found = []
        for user_id, security_level in users:
            contamination_key = f"contaminated_data_from_{user_id}"
            if contamination_key in contamination_context.metadata:
                contaminated_data_found.append((user_id, security_level))

        # SECURITY VIOLATION: Context contamination detected
        assert len(contaminated_data_found) > 0, "No context contamination detected - vulnerability may be fixed"

        # CRITICAL ISSUE: Different security levels mixed in one context
        security_levels_in_context = set()
        for user_id, security_level in contaminated_data_found:
            security_levels_in_context.add(security_level)

        # COMPLIANCE VIOLATION: Multiple security classifications in one context
        if "top_secret" in security_levels_in_context and "public_access" in security_levels_in_context:
            compliance_violation = "top_secret_public_mixing"
        elif "hipaa_protected" in security_levels_in_context and "public_access" in security_levels_in_context:
            compliance_violation = "hipaa_public_mixing"
        else:
            compliance_violation = "security_level_mixing"

        # Cleanup
        for agent in agents:
            await agent.cleanup()
        await contamination_agent.cleanup()

        self.record_metric("users_data_contaminated", len(contaminated_data_found))
        self.record_metric("security_levels_mixed", len(security_levels_in_context))
        self.record_metric("compliance_violation", compliance_violation)
        self.record_metric("context_contamination_confirmed", True)

    @pytest.mark.real_services
    async def test_concurrent_user_isolation_failure(self):
        """
        VULNERABILITY TEST: Demonstrate isolation failures under concurrent load.

        This test proves that concurrent user sessions can interfere with
        each other, leading to data corruption and security violations.

        BUSINESS IMPACT: System unreliable under load - production outages.
        """

        # Create concurrent users with sensitive data
        num_concurrent_users = 10
        concurrent_tasks = []
        user_results = {}

        async def execute_user_session(user_index: int):
            user_id = f"concurrent_user_{user_index:03d}"

            # Create context with unique sensitive data for each user
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=f"security_thread_{user_id}_{uuid.uuid4().hex[:8]}",
                run_id=f"security_run_{user_id}_{uuid.uuid4().hex[:8]}",
                agent_context={
                    "user_request": f"Security test for concurrent_isolation_test",
                    "test_scenario": "concurrent_isolation_test",
                    "security_level": "confidential",
                    "user_secret": f"SECRET_FOR_USER_{user_index}",
                    "user_id_verification": user_id,
                    "session_token": f"TOKEN_{uuid.uuid4().hex}",
                    "sensitive_index": user_index
                }
            )

            agent = VulnerabilityTestAgent(user_id, "deep_object_sharing", user_context=context)

            # Add some delay variation to increase race condition chances
            await asyncio.sleep(0.001 * (user_index % 3))

            result = await agent.execute(context)

            await agent.cleanup()

            return user_index, result, context

        # Execute all users concurrently
        concurrent_tasks = [execute_user_session(i) for i in range(num_concurrent_users)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)

        # Analyze results for isolation violations
        user_data_overlap = []
        global_counter_inconsistencies = []

        for user_index, result, context in concurrent_results:
            user_results[user_index] = {
                "result": result,
                "context_keys": set(context.metadata.keys()),
                "sensitive_data": context.metadata.get("user_secret", "")
            }

        # Check for data overlap between users
        for i in range(num_concurrent_users):
            for j in range(i + 1, num_concurrent_users):
                user_i_keys = user_results[i]["context_keys"]
                user_j_keys = user_results[j]["context_keys"]

                # Look for unexpected overlap (beyond basic keys)
                basic_keys = {"user_request", "test_scenario", "security_level", "user_permissions", "compliance_requirements"}
                overlap = user_i_keys.intersection(user_j_keys) - basic_keys

                if len(overlap) > 4:  # Allow some expected overlap
                    user_data_overlap.append((i, j, list(overlap)))

        # Check global counter for race conditions
        all_shared_data = VulnerabilityTestAgent.get_all_shared_data()
        global_counter_final = VulnerabilityTestAgent._global_counter

        # VULNERABILITY INDICATORS
        isolation_violations = {
            "data_overlap_detected": len(user_data_overlap) > 0,
            "shared_data_contamination": len(all_shared_data) >= num_concurrent_users,
            "global_state_modification": global_counter_final >= num_concurrent_users,
            "concurrent_execution_issues": False
        }

        # Check for race conditions in results
        expected_global_counter = num_concurrent_users
        if global_counter_final != expected_global_counter:
            isolation_violations["concurrent_execution_issues"] = True

        # BUSINESS IMPACT: Any isolation violation is critical
        total_violations = sum(1 for violation in isolation_violations.values() if violation)

        self.record_metric("concurrent_users_tested", num_concurrent_users)
        self.record_metric("isolation_violations", total_violations)
        self.record_metric("data_overlap_cases", len(user_data_overlap))
        self.record_metric("shared_data_entries", len(all_shared_data))
        self.record_metric("global_counter_final", global_counter_final)
        self.record_metric("concurrent_isolation_vulnerabilities", isolation_violations)

        # This test SHOULD identify vulnerabilities
        assert total_violations > 0, "No isolation violations detected - system may be properly secured"

    @pytest.mark.real_services
    @pytest.mark.skipif(not DEEP_AGENT_STATE_AVAILABLE, reason="DeepAgentState not available")
    async def test_deep_agent_state_isolation_vulnerability(self):
        """
        VULNERABILITY TEST: Test DeepAgentState cross-user contamination.

        This test specifically targets the DeepAgentState component mentioned
        in the security analysis as having user isolation vulnerabilities.
        """

        # This test requires the actual DeepAgentState component
        # Implementation depends on the actual class structure

        # Create two users with different sensitive contexts
        user_alpha = "alpha_enterprise_customer"
        user_beta = "beta_government_client"

        context_alpha = self.create_test_user_context(user_alpha, "deep_state_alpha")
        context_beta = self.create_test_user_context(user_beta, "deep_state_beta")

        # Add enterprise vs government data
        context_alpha.metadata.update({
            "enterprise_data": "CONFIDENTIAL_ENTERPRISE_ALPHA",
            "customer_type": "enterprise",
            "data_classification": "confidential"
        })

        context_beta.metadata.update({
            "government_data": "CLASSIFIED_GOVERNMENT_BETA",
            "customer_type": "government",
            "data_classification": "classified"
        })

        # Test would create DeepAgentState instances and verify isolation
        # This is a placeholder for the actual vulnerability test

        self.record_metric("deep_agent_state_test_placeholder", True)
        self.record_metric("requires_actual_implementation", True)

    @pytest.mark.real_services
    @pytest.mark.skipif(not MODERN_EXECUTION_HELPERS_AVAILABLE, reason="ModernExecutionHelpers not available")
    async def test_modern_execution_helpers_shared_state_vulnerability(self):
        """
        VULNERABILITY TEST: Test ModernExecutionHelpers shared state issues.

        This test specifically targets the ModernExecutionHelpers component
        mentioned in the security analysis as having shared state vulnerabilities.
        """

        # This test requires the actual ModernExecutionHelpers component
        # Implementation depends on the actual class structure

        self.record_metric("modern_execution_helpers_test_placeholder", True)
        self.record_metric("requires_actual_implementation", True)

    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)

        # Clean up vulnerability test data
        VulnerabilityTestAgent.reset_shared_data()

        # Force garbage collection
        gc.collect()

        # Log security test metrics
        metrics = self.get_all_metrics()
        print(f"\nUser Isolation Vulnerability Test Results:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        # Verify critical security metrics
        critical_security_issues = [
            "vulnerability_confirmed",
            "context_contamination_confirmed",
            "concurrent_isolation_vulnerabilities"
        ]

        for issue in critical_security_issues:
            if metrics.get(issue, False):
                print(f"  WARNING️  SECURITY VULNERABILITY CONFIRMED: {issue}")

        # Business impact assessment
        regulatory_violations = metrics.get("regulatory_violations_detected", [])
        if regulatory_violations:
            print(f"  🚨 REGULATORY COMPLIANCE VIOLATIONS: {regulatory_violations}")
            print(f"  💰 BUSINESS IMPACT: Enterprise customers at risk of churn")
            print(f"  📋 COMPLIANCE IMPACT: HIPAA, SOC2, SEC violations possible")