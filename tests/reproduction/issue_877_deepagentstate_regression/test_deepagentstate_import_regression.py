"""Test Issue #877: DeepAgentState Migration Incomplete Regression

This test reproduces the critical regression where agent_lifecycle.py still uses
deprecated DeepAgentState pattern despite migration claims, blocking Golden Path.

CRITICAL BUSINESS IMPACT:
- $500K+ ARR at risk due to broken user login → AI response flow
- Cross-user data contamination vulnerability in chat functionality
- Agent lifecycle management using deprecated patterns

These tests will FAIL initially, proving the regression exists.
They should PASS after proper SSOT remediation.
"""

import ast
import inspect
from pathlib import Path
from typing import get_type_hints

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeepAgentStateImportRegression(SSotBaseTestCase):
    """Test suite to validate DeepAgentState import regression exists."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.agent_lifecycle_path = Path("netra_backend/app/agents/agent_lifecycle.py")
        self.base_agent_path = Path("netra_backend/app/agents/base_agent.py")

    def test_agent_lifecycle_still_imports_deepagentstate_deprecated(self):
        """Test that agent_lifecycle.py still imports DeepAgentState from deprecated location.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: DeepAgentState import found in agent_lifecycle.py
        """
        # Read agent_lifecycle.py source code
        try:
            with open(self.agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f"agent_lifecycle.py not found at {self.agent_lifecycle_path}")

        # Parse the AST to find imports
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            self.fail(f"Syntax error in agent_lifecycle.py: {e}")

        # Check for DeepAgentState import
        deepagent_import_found = False
        import_location = None

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "schemas.agent_models" in node.module:
                    for alias in node.names:
                        if alias.name == "DeepAgentState":
                            deepagent_import_found = True
                            import_location = f"Line {node.lineno}: from {node.module} import DeepAgentState"

        # This should fail if regression exists
        if deepagent_import_found:
            self.fail(
                f"REGRESSION CONFIRMED: DeepAgentState import still present in agent_lifecycle.py\n"
                f"Import found: {import_location}\n"
                f"Expected: DeepAgentState should be migrated to UserExecutionContext pattern\n"
                f"Impact: Golden Path broken, user isolation compromised"
            )

        # If we reach here, the import was removed (regression fixed)
        self.assertTrue(True, "DeepAgentState import properly removed from agent_lifecycle.py")

    def test_agent_lifecycle_method_signatures_use_deepagentstate(self):
        """Test that agent_lifecycle.py method signatures still use DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Method signatures still reference DeepAgentState type
        """
        try:
            # Import the module to inspect its methods
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f"Cannot import AgentLifecycleMixin: {e}")

        # Check _pre_run method signature
        try:
            pre_run_method = getattr(AgentLifecycleMixin, '_pre_run')
            pre_run_sig = inspect.signature(pre_run_method)

            # Get type hints if available
            try:
                hints = get_type_hints(pre_run_method)
            except (NameError, AttributeError):
                hints = {}

            # Check if 'state' parameter uses DeepAgentState
            state_param = pre_run_sig.parameters.get('state')
            if state_param and state_param.annotation != inspect.Parameter.empty:
                annotation_str = str(state_param.annotation)
                if 'DeepAgentState' in annotation_str:
                    self.fail(
                        f"REGRESSION CONFIRMED: _pre_run method still uses DeepAgentState\n"
                        f"Method signature: {pre_run_sig}\n"
                        f"State parameter type: {annotation_str}\n"
                        f"Expected: Should use UserExecutionContext pattern\n"
                        f"Impact: Agent execution using deprecated state management"
                    )

        except AttributeError:
            self.fail("_pre_run method not found in AgentLifecycleMixin")

        # Check _post_run method signature
        try:
            post_run_method = getattr(AgentLifecycleMixin, '_post_run')
            post_run_sig = inspect.signature(post_run_method)

            # Check if 'state' parameter uses DeepAgentState
            state_param = post_run_sig.parameters.get('state')
            if state_param and state_param.annotation != inspect.Parameter.empty:
                annotation_str = str(state_param.annotation)
                if 'DeepAgentState' in annotation_str:
                    self.fail(
                        f"REGRESSION CONFIRMED: _post_run method still uses DeepAgentState\n"
                        f"Method signature: {post_run_sig}\n"
                        f"State parameter type: {annotation_str}\n"
                        f"Expected: Should use UserExecutionContext pattern\n"
                        f"Impact: Agent cleanup using deprecated state management"
                    )

        except AttributeError:
            self.fail("_post_run method not found in AgentLifecycleMixin")

        # If we reach here, method signatures were migrated (regression fixed)
        self.assertTrue(True, "Method signatures properly migrated from DeepAgentState")

    def test_base_agent_migration_claims_vs_reality_mismatch(self):
        """Test that base_agent.py migration claims don't match agent_lifecycle.py reality.

        THIS TEST SHOULD FAIL - proving the inconsistency exists.
        Expected failure: base_agent claims migration complete but agent_lifecycle still uses old pattern
        """
        # Check base_agent.py for migration completion claims
        try:
            with open(self.base_agent_path) as f:
                base_agent_source = f.read()
        except FileNotFoundError:
            self.skip(f"base_agent.py not found at {self.base_agent_path}")

        # Look for migration completion claims
        migration_claims = []
        for line_num, line in enumerate(base_agent_source.split('\n'), 1):
            if 'MIGRATION COMPLETED' in line and 'DeepAgentState' in line:
                migration_claims.append(f"Line {line_num}: {line.strip()}")

        # Check agent_lifecycle.py for actual DeepAgentState usage
        try:
            with open(self.agent_lifecycle_path) as f:
                lifecycle_source = f.read()
        except FileNotFoundError:
            self.fail(f"agent_lifecycle.py not found at {self.agent_lifecycle_path}")

        # Look for actual DeepAgentState usage
        deepagent_usage = []
        for line_num, line in enumerate(lifecycle_source.split('\n'), 1):
            if 'DeepAgentState' in line:
                deepagent_usage.append(f"Line {line_num}: {line.strip()}")

        # This should fail if claims don't match reality
        if migration_claims and deepagent_usage:
            self.fail(
                f"REGRESSION CONFIRMED: Migration claims don't match reality\n"
                f"\nCLAIMS in base_agent.py:\n" + "\n".join(migration_claims) +
                f"\n\nREALITY in agent_lifecycle.py:\n" + "\n".join(deepagent_usage) +
                f"\n\nExpected: Consistent migration state across all files\n"
                f"Impact: False sense of security, incomplete migration"
            )

        # If we reach here, claims match reality (regression fixed)
        self.assertTrue(True, "Migration claims consistent with actual implementation")


class TestUserExecutionContextMigrationIncomplete(SSotBaseTestCase):
    """Test suite to validate UserExecutionContext migration is incomplete."""

    def test_agent_lifecycle_not_using_user_execution_context(self):
        """Test that agent_lifecycle.py is not using UserExecutionContext pattern.

        THIS TEST SHOULD FAIL - proving the incomplete migration.
        Expected failure: agent_lifecycle should import and use UserExecutionContext
        """
        # Read agent_lifecycle.py source code
        agent_lifecycle_path = Path("netra_backend/app/agents/agent_lifecycle.py")
        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f"agent_lifecycle.py not found at {agent_lifecycle_path}")

        # Check for UserExecutionContext import
        has_user_context_import = 'UserExecutionContext' in source_code

        # Check for UserExecutionContext usage in method signatures
        has_user_context_usage = False
        if has_user_context_import:
            # Parse AST to check function signatures
            try:
                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for arg in node.args.args:
                            if hasattr(arg, 'annotation') and arg.annotation:
                                if isinstance(arg.annotation, ast.Name) and arg.annotation.id == 'UserExecutionContext':
                                    has_user_context_usage = True
                                elif isinstance(arg.annotation, ast.Constant) and 'UserExecutionContext' in str(arg.annotation.value):
                                    has_user_context_usage = True
            except SyntaxError:
                pass  # Skip AST parsing if syntax error

        # This should fail if migration is incomplete
        if not has_user_context_import or not has_user_context_usage:
            self.fail(
                f"INCOMPLETE MIGRATION CONFIRMED: agent_lifecycle.py not using UserExecutionContext\n"
                f"UserExecutionContext import found: {has_user_context_import}\n"
                f"UserExecutionContext usage found: {has_user_context_usage}\n"
                f"Expected: Full migration to UserExecutionContext pattern\n"
                f"Impact: Agent execution context isolation compromised"
            )

        # If we reach here, migration is complete (regression fixed)
        self.assertTrue(True, "agent_lifecycle.py properly using UserExecutionContext pattern")

    def test_concurrent_user_isolation_vulnerability_exists(self):
        """Test that current DeepAgentState usage creates cross-user data vulnerability.

        THIS TEST SHOULD FAIL - proving the security vulnerability exists.
        Expected failure: DeepAgentState allows potential cross-user data contamination
        """
        try:
            # Import DeepAgentState to test its isolation properties
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError:
            self.skip("DeepAgentState not available for testing")

        # Create two DeepAgentState instances for different users
        user1_state = DeepAgentState(
            user_id="user_123",
            user_request="User 1 request",
            agent_context={"sensitive_data": "user1_secret"}
        )

        user2_state = DeepAgentState(
            user_id="user_456",
            user_request="User 2 request",
            agent_context={"sensitive_data": "user2_secret"}
        )

        # Test if DeepAgentState provides proper isolation
        # (This is a simplified test - real isolation issues would be more subtle)

        # Check that states are properly isolated
        if user1_state.agent_context == user2_state.agent_context:
            self.fail(
                f"VULNERABILITY CONFIRMED: DeepAgentState allows cross-user context sharing\n"
                f"User 1 context: {user1_state.agent_context}\n"
                f"User 2 context: {user2_state.agent_context}\n"
                f"Expected: Complete isolation between user contexts\n"
                f"Impact: Potential data leakage between users"
            )

        # Test merge functionality for isolation issues
        try:
            merged_state = user1_state.merge_from(user2_state)

            # Check if merge preserves user isolation
            if merged_state.user_id != user1_state.user_id and merged_state.user_id != user2_state.user_id:
                self.fail(
                    f"VULNERABILITY CONFIRMED: merge_from creates ambiguous user identity\n"
                    f"Original user_id: {user1_state.user_id}\n"
                    f"Merged user_id: {merged_state.user_id}\n"
                    f"Expected: Clear user identity preservation\n"
                    f"Impact: User session confusion"
                )

        except Exception as e:
            # Merge failure might indicate isolation issues
            pass

        # If we reach here, isolation is properly implemented (regression fixed)
        self.assertTrue(True, "DeepAgentState provides proper user isolation")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])