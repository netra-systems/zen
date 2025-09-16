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

class UserExecutionContextIntegrationMissingTests(SSotBaseTestCase):
    """Test suite to validate missing UserExecutionContext integration."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

    def test_agent_lifecycle_missing_user_execution_context_import(self):
        """Test that agent_lifecycle.py is missing UserExecutionContext import.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: No UserExecutionContext import found
        """
        agent_lifecycle_path = Path('netra_backend/app/agents/agent_lifecycle.py')
        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f'agent_lifecycle.py not found at {agent_lifecycle_path}')
        has_user_context_import = 'UserExecutionContext' in source_code
        if not has_user_context_import:
            self.fail(f'REGRESSION CONFIRMED: agent_lifecycle.py missing UserExecutionContext import\nFile: {agent_lifecycle_path}\nExpected: Should import UserExecutionContext for proper user isolation\nImpact: Agent execution without proper user context isolation')
        self.assertTrue(True, 'UserExecutionContext import found in agent_lifecycle.py')

    def test_agent_lifecycle_missing_user_execution_context_usage_in_methods(self):
        """Test that agent lifecycle methods don't use UserExecutionContext.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Methods still use DeepAgentState instead of UserExecutionContext
        """
        agent_lifecycle_path = Path('netra_backend/app/agents/agent_lifecycle.py')
        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f'agent_lifecycle.py not found at {agent_lifecycle_path}')
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            self.fail(f'Syntax error in agent_lifecycle.py: {e}')
        critical_methods = ['_pre_run', '_post_run', 'execute', 'check_entry_conditions', 'cleanup']
        methods_using_user_context = []
        methods_using_deep_agent_state = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in critical_methods:
                for arg in node.args.args:
                    if hasattr(arg, 'annotation') and arg.annotation:
                        annotation_str = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                        if 'UserExecutionContext' in annotation_str:
                            methods_using_user_context.append(f'{node.name}({arg.arg}: {annotation_str})')
                        elif 'DeepAgentState' in annotation_str:
                            methods_using_deep_agent_state.append(f'{node.name}({arg.arg}: {annotation_str})')
        if len(methods_using_user_context) == 0 and len(methods_using_deep_agent_state) > 0:
            self.fail(f'REGRESSION CONFIRMED: Critical methods missing UserExecutionContext usage\nMethods using DeepAgentState: {methods_using_deep_agent_state}\nMethods using UserExecutionContext: {methods_using_user_context}\nExpected: Critical methods should use UserExecutionContext for proper isolation\nImpact: Agent methods operating without proper user context')
        self.assertTrue(True, 'Agent lifecycle methods properly use UserExecutionContext')

    def test_user_execution_context_not_accessible_from_agent_lifecycle(self):
        """Test that UserExecutionContext is not accessible from agent lifecycle module.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: UserExecutionContext should be importable and usable
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import UserExecutionContext
            has_user_context = True
        except ImportError:
            has_user_context = False
        if not has_user_context:
            try:
                import netra_backend.app.agents.agent_lifecycle as lifecycle_module
                has_user_context = hasattr(lifecycle_module, 'UserExecutionContext')
            except ImportError:
                pass
        if not has_user_context:
            self.fail(f'REGRESSION CONFIRMED: UserExecutionContext not accessible from agent_lifecycle\nExpected: UserExecutionContext should be imported and available\nImpact: Agent lifecycle cannot create proper user execution contexts')
        self.assertTrue(True, 'UserExecutionContext accessible from agent_lifecycle module')

class UserIsolationVulnerabilityTests(SSotBaseTestCase):
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
            self.skip(f'Cannot import required classes: {e}')

        class VulnerableTestAgent(AgentLifecycleMixin):

            def __init__(self):
                self.name = 'VulnerableTestAgent'
                self.logger = Mock()
                self.start_time = 0.0
                self.end_time = 0.0
                self.context = Mock()
                self.emit_agent_started = AsyncMock()
                self.emit_agent_completed = AsyncMock()
                self.emit_error = AsyncMock()
                self.set_state = Mock()
                self._log_agent_start = Mock()
                self._log_agent_completion = Mock()
                self.shared_state = {}

            async def execute(self, state, run_id, stream_updates):
                """Mock execute method that demonstrates vulnerability."""
                self.shared_state[run_id] = {'user_id': state.user_id, 'user_request': state.user_request, 'sensitive_data': getattr(state, 'agent_context', {})}
        agent = VulnerableTestAgent()
        user1_state = DeepAgentState(user_id='user_123', user_request='User 1 sensitive request', agent_context={'secret': 'user1_private_data'})
        user2_state = DeepAgentState(user_id='user_456', user_request='User 2 sensitive request', agent_context={'secret': 'user2_private_data'})
        try:
            await agent._pre_run(user1_state, 'run_123', True)
            await agent._pre_run(user2_state, 'run_456', True)
            if len(agent.shared_state) > 1:
                user_data = list(agent.shared_state.values())
                different_users = len(set((data['user_id'] for data in user_data))) > 1
                if different_users:
                    self.fail(f'VULNERABILITY CONFIRMED: Agent creates cross-user data vulnerability\nShared state contains data from multiple users: {agent.shared_state}\nExpected: Complete isolation between user execution contexts\nImpact: Potential cross-user data contamination')
        except Exception as e:
            if 'Mock' not in str(e):
                self.fail(f'Agent execution failed with potential vulnerability: {e}')
        self.assertTrue(True, 'Agent lifecycle provides proper user isolation')

    def test_deep_agent_state_allows_cross_user_state_merge_vulnerability(self):
        """Test that DeepAgentState merge functionality creates cross-user vulnerability.

        THIS TEST SHOULD FAIL - proving the vulnerability exists.
        Expected failure: merge_from allows mixing data between different users
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError as e:
            self.skip(f'Cannot import DeepAgentState: {e}')
        user1_state = DeepAgentState(user_id='user_123', user_request='User 1 private request', agent_context={'private_key': 'user1_secret_key', 'account': 'user1_account'})
        user2_state = DeepAgentState(user_id='user_456', user_request='User 2 private request', agent_context={'private_key': 'user2_secret_key', 'account': 'user2_account'})
        try:
            merged_state = user1_state.merge_from(user2_state)
            merged_context = getattr(merged_state, 'agent_context', {})
            has_user1_data = any(('user1' in str(value) for value in merged_context.values()))
            has_user2_data = any(('user2' in str(value) for value in merged_context.values()))
            if has_user1_data and has_user2_data:
                self.fail(f'VULNERABILITY CONFIRMED: merge_from creates cross-user data contamination\nOriginal User 1 context: {user1_state.agent_context}\nOriginal User 2 context: {user2_state.agent_context}\nMerged context: {merged_context}\nExpected: merge_from should prevent cross-user data mixing\nImpact: User privacy breach through state merging')
            if merged_state.user_id != user1_state.user_id and merged_state.user_id != user2_state.user_id:
                self.fail(f'VULNERABILITY CONFIRMED: merge_from creates ambiguous user identity\nUser 1 ID: {user1_state.user_id}\nUser 2 ID: {user2_state.user_id}\nMerged ID: {merged_state.user_id}\nExpected: Clear user identity should be preserved\nImpact: User session confusion and potential data leakage')
        except Exception as e:
            if 'isolation' in str(e).lower() or 'user' in str(e).lower():
                self.assertTrue(True, 'merge_from properly prevents cross-user contamination')
            else:
                raise
        self.assertTrue(True, 'DeepAgentState merge_from provides proper user isolation')

class MigrationCompletenessValidationTests(SSotBaseTestCase):
    """Test suite to validate migration completeness claims."""

    def test_migration_completeness_claims_are_false(self):
        """Test that migration completeness claims in documentation are false.

        THIS TEST SHOULD FAIL - proving the false claims exist.
        Expected failure: Documentation claims migration complete but code shows otherwise
        """
        potential_claim_files = ['netra_backend/app/agents/base_agent.py', 'SSOT-regression-DeepAgentState-migration-incomplete-blocking-Golden-Path.md']
        claims_found = []
        reality_violations = []
        for file_path in potential_claim_files:
            path = Path(file_path)
            if path.exists():
                try:
                    with open(path) as f:
                        content = f.read()
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if ('MIGRATION COMPLETED' in line or 'migration complete' in line.lower()) and 'DeepAgentState' in line:
                            claims_found.append(f'{file_path}:{line_num} - {line.strip()}')
                except Exception:
                    pass
        lifecycle_path = Path('netra_backend/app/agents/agent_lifecycle.py')
        if lifecycle_path.exists():
            try:
                with open(lifecycle_path) as f:
                    content = f.read()
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if 'DeepAgentState' in line:
                        reality_violations.append(f'agent_lifecycle.py:{line_num} - {line.strip()}')
            except Exception:
                pass
        if claims_found and reality_violations:
            self.fail(f'REGRESSION CONFIRMED: Migration completeness claims are false\n\nCLAIMS FOUND:\n' + '\n'.join(claims_found) + f'\n\nREALITY VIOLATIONS:\n' + '\n'.join(reality_violations) + f'\n\nExpected: Claims should match implementation reality\nImpact: False sense of security about migration state')
        self.assertTrue(True, 'Migration completeness claims match implementation reality')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')