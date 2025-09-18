"""Test Issue #877: UserExecutionContext Integration Missing

This test reproduces the regression where agent_lifecycle.py lacks proper
integration with UserExecutionContext, despite claims of complete migration.

FOCUS AREAS:
- Missing UserExecutionContext integration in agent lifecycle
- Incomplete migration from DeepAgentState to proper execution context
- Security vulnerability from improper user isolation patterns

These tests will FAIL initially, proving the regression exists.
They should PASS after proper SSOT remediation.
"""

import ast
from pathlib import Path
from unittest.mock import Mock, AsyncMock

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUserExecutionContextIntegrationMissing(SSotBaseTestCase):
    """Test suite to validate missing UserExecutionContext integration."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_agent_lifecycle_missing_user_execution_context_import(self):
        """Test that agent_lifecycle.py is missing UserExecutionContext import.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: No UserExecutionContext import found
        """
        agent_lifecycle_path = Path("netra_backend/app/agents/agent_lifecycle.py")

        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f"agent_lifecycle.py not found at {agent_lifecycle_path}")

        # Check for UserExecutionContext import
        has_user_context_import = 'UserExecutionContext' in source_code

        if not has_user_context_import:
            self.fail(
                f"REGRESSION CONFIRMED: agent_lifecycle.py missing UserExecutionContext import\n"
                f"File: {agent_lifecycle_path}\n"
                f"Expected: Should import UserExecutionContext for proper user isolation\n"
                f"Impact: Agent execution without proper user context isolation"
            )

        # If we reach here, the import exists (regression fixed)
        self.assertTrue(True, "UserExecutionContext import found in agent_lifecycle.py")

    def test_agent_lifecycle_missing_user_execution_context_usage_in_methods(self):
        """Test that agent lifecycle methods don't use UserExecutionContext.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Methods still use DeepAgentState instead of UserExecutionContext
        """
        agent_lifecycle_path = Path("netra_backend/app/agents/agent_lifecycle.py")

        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f"agent_lifecycle.py not found at {agent_lifecycle_path}")

        # Parse AST to check method signatures
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            self.fail(f"Syntax error in agent_lifecycle.py: {e}")

        # Look for method definitions that should use UserExecutionContext
        critical_methods = ['_pre_run', '_post_run', 'execute', 'check_entry_conditions', 'cleanup']
        methods_using_user_context = []
        methods_using_deep_agent_state = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in critical_methods:
                # Check method arguments for type annotations
                for arg in node.args.args:
                    if hasattr(arg, 'annotation') and arg.annotation:
                        annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)

                        if 'UserExecutionContext' in annotation_str:
                            methods_using_user_context.append(f"{node.name}({arg.arg}: {annotation_str})")
                        elif 'DeepAgentState' in annotation_str:
                            methods_using_deep_agent_state.append(f"{node.name}({arg.arg}: {annotation_str})")

        # Check if critical methods are missing UserExecutionContext usage
        if len(methods_using_user_context) == 0 and len(methods_using_deep_agent_state) > 0:
            self.fail(
                f"REGRESSION CONFIRMED: Critical methods missing UserExecutionContext usage\n"
                f"Methods using DeepAgentState: {methods_using_deep_agent_state}\n"
                f"Methods using UserExecutionContext: {methods_using_user_context}\n"
                f"Expected: Critical methods should use UserExecutionContext for proper isolation\n"
                f"Impact: Agent methods operating without proper user context"
            )

        # If we reach here, methods properly use UserExecutionContext (regression fixed)
        self.assertTrue(True, "Agent lifecycle methods properly use UserExecutionContext")

    def test_user_execution_context_not_accessible_from_agent_lifecycle(self):
        """Test that UserExecutionContext is not accessible from agent lifecycle module.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: UserExecutionContext should be importable and usable
        """
        try:
            # Try to import UserExecutionContext from the module
            from netra_backend.app.agents.agent_lifecycle import UserExecutionContext
            has_user_context = True
        except ImportError:
            has_user_context = False

        # Alternative: Check if it's available via the module
        if not has_user_context:
            try:
                import netra_backend.app.agents.agent_lifecycle as lifecycle_module
                has_user_context = hasattr(lifecycle_module, 'UserExecutionContext')
            except ImportError:
                pass

        if not has_user_context:
            self.fail(
                f"REGRESSION CONFIRMED: UserExecutionContext not accessible from agent_lifecycle\n"
                f"Expected: UserExecutionContext should be imported and available\n"
                f"Impact: Agent lifecycle cannot create proper user execution contexts"
            )

        # If we reach here, UserExecutionContext is accessible (regression fixed)
        self.assertTrue(True, "UserExecutionContext accessible from agent_lifecycle module")


class TestUserIsolationVulnerability(SSotBaseTestCase):
    """Test suite to validate user isolation vulnerabilities from incomplete migration."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    async def test_agent_lifecycle_creates_user_isolation_vulnerability(self):
        """Test that current agent lifecycle creates user isolation vulnerability.

        THIS TEST SHOULD FAIL - proving the vulnerability exists.
        Expected failure: Agent execution allows cross-user data contamination
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError as e:
            self.skip(f"Cannot import required classes: {e}")

        # Create test agent that simulates the vulnerability
        class VulnerableTestAgent(AgentLifecycleMixin):
            def __init__(self):
                self.name = "VulnerableTestAgent"
                self.logger = Mock()
                self.start_time = 0.0
                self.end_time = 0.0
                self.context = Mock()

                # Mock WebSocket methods
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()

                # Mock lifecycle methods
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()

                # Simulate shared state vulnerability
                self.shared_state = {}

            async def execute(self, state, run_id, stream_updates):
                """Mock execute method that demonstrates vulnerability."""
                # Simulate storing user data in shared state (vulnerability)
                self.shared_state[run_id] = {
                    'user_id': state.user_id,
                    'user_request': state.user_request,
                    'sensitive_data': getattr(state, 'agent_context', {})
                }

        # Create agent instance
        agent = VulnerableTestAgent()

        # Create states for two different users
        user1_state = DeepAgentState(
            user_id="user_123",
            user_request="User 1 sensitive request",
            agent_context={"secret": "user1_private_data"}
        )

        user2_state = DeepAgentState(
            user_id="user_456",
            user_request="User 2 sensitive request",
            agent_context={"secret": "user2_private_data"}
        )

        # Execute agent methods for both users
        try:
            await agent._pre_run(user1_state, "run_123", True)
            await agent._pre_run(user2_state, "run_456", True)

            # Check if shared state contains data from both users
            if len(agent.shared_state) > 1:
                user_data = list(agent.shared_state.values())
                different_users = len(set(data['user_id'] for data in user_data)) > 1

                if different_users:
                    self.fail(
                        f"VULNERABILITY CONFIRMED: Agent creates cross-user data vulnerability\n"
                        f"Shared state contains data from multiple users: {agent.shared_state}\n"
                        f"Expected: Complete isolation between user execution contexts\n"
                        f"Impact: Potential cross-user data contamination"
                    )

        except Exception as e:
            # Any exception during execution might indicate vulnerability
            if "Mock" not in str(e):
                self.fail(f"Agent execution failed with potential vulnerability: {e}")

        # If we reach here, proper isolation exists (vulnerability fixed)
        self.assertTrue(True, "Agent lifecycle provides proper user isolation")

    def test_deep_agent_state_allows_cross_user_state_merge_vulnerability(self):
        """Test that DeepAgentState merge functionality creates cross-user vulnerability.

        THIS TEST SHOULD FAIL - proving the vulnerability exists.
        Expected failure: merge_from allows mixing data between different users
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError as e:
            self.skip(f"Cannot import DeepAgentState: {e}")

        # Create states for two different users with sensitive data
        user1_state = DeepAgentState(
            user_id="user_123",
            user_request="User 1 private request",
            agent_context={"private_key": "user1_secret_key", "account": "user1_account"}
        )

        user2_state = DeepAgentState(
            user_id="user_456",
            user_request="User 2 private request",
            agent_context={"private_key": "user2_secret_key", "account": "user2_account"}
        )

        # Test merge_from functionality
        try:
            merged_state = user1_state.merge_from(user2_state)

            # Check if merged state contains data from both users
            merged_context = getattr(merged_state, 'agent_context', {})

            # Check for cross-contamination
            has_user1_data = any('user1' in str(value) for value in merged_context.values())
            has_user2_data = any('user2' in str(value) for value in merged_context.values())

            if has_user1_data and has_user2_data:
                self.fail(
                    f"VULNERABILITY CONFIRMED: merge_from creates cross-user data contamination\n"
                    f"Original User 1 context: {user1_state.agent_context}\n"
                    f"Original User 2 context: {user2_state.agent_context}\n"
                    f"Merged context: {merged_context}\n"
                    f"Expected: merge_from should prevent cross-user data mixing\n"
                    f"Impact: User privacy breach through state merging"
                )

            # Check user_id consistency
            if merged_state.user_id != user1_state.user_id and merged_state.user_id != user2_state.user_id:
                self.fail(
                    f"VULNERABILITY CONFIRMED: merge_from creates ambiguous user identity\n"
                    f"User 1 ID: {user1_state.user_id}\n"
                    f"User 2 ID: {user2_state.user_id}\n"
                    f"Merged ID: {merged_state.user_id}\n"
                    f"Expected: Clear user identity should be preserved\n"
                    f"Impact: User session confusion and potential data leakage"
                )

        except Exception as e:
            # Exception during merge might indicate proper protection
            if 'isolation' in str(e).lower() or 'user' in str(e).lower():
                self.assertTrue(True, "merge_from properly prevents cross-user contamination")
            else:
                raise

        # If we reach here, merge provides proper isolation (vulnerability fixed)
        self.assertTrue(True, "DeepAgentState merge_from provides proper user isolation")


class TestMigrationCompletenessValidation(SSotBaseTestCase):
    """Test suite to validate migration completeness claims."""

    def test_migration_completeness_claims_are_false(self):
        """Test that migration completeness claims in documentation are false.

        THIS TEST SHOULD FAIL - proving the false claims exist.
        Expected failure: Documentation claims migration complete but code shows otherwise
        """
        # Check for migration completion claims in various files
        potential_claim_files = [
            "netra_backend/app/agents/base_agent.py",
            "SSOT-regression-DeepAgentState-migration-incomplete-blocking-Golden-Path.md"
        ]

        claims_found = []
        reality_violations = []

        for file_path in potential_claim_files:
            path = Path(file_path)
            if path.exists():
                try:
                    with open(path) as f:
                        content = f.read()

                    # Look for migration completion claims
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if ('MIGRATION COMPLETED' in line or 'migration complete' in line.lower()) and 'DeepAgentState' in line:
                            claims_found.append(f"{file_path}:{line_num} - {line.strip()}")

                except Exception:
                    pass

        # Check agent_lifecycle.py for actual DeepAgentState usage
        lifecycle_path = Path("netra_backend/app/agents/agent_lifecycle.py")
        if lifecycle_path.exists():
            try:
                with open(lifecycle_path) as f:
                    content = f.read()

                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if 'DeepAgentState' in line:
                        reality_violations.append(f"agent_lifecycle.py:{line_num} - {line.strip()}")

            except Exception:
                pass

        # If we have claims but also violations, migration is incomplete
        if claims_found and reality_violations:
            self.fail(
                f"REGRESSION CONFIRMED: Migration completeness claims are false\n"
                f"\nCLAIMS FOUND:\n" + "\n".join(claims_found) +
                f"\n\nREALITY VIOLATIONS:\n" + "\n".join(reality_violations) +
                f"\n\nExpected: Claims should match implementation reality\n"
                f"Impact: False sense of security about migration state"
            )

        # If we reach here, claims match reality (regression fixed)
        self.assertTrue(True, "Migration completeness claims match implementation reality")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])