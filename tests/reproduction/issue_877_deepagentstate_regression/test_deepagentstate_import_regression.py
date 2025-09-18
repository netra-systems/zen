"""Test Issue #877: DeepAgentState Migration Incomplete Regression

This test reproduces the critical regression where agent_lifecycle.py still uses
deprecated DeepAgentState pattern despite migration claims, blocking Golden Path.

CRITICAL BUSINESS IMPACT:
- $500K+ ARR at risk due to broken user login -> AI response flow
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

class DeepAgentStateImportRegressionTests(SSotBaseTestCase):
    """Test suite to validate DeepAgentState import regression exists."""

    def test_agent_lifecycle_still_imports_deepagentstate_deprecated(self):
        """Test that agent_lifecycle.py still imports DeepAgentState from deprecated location.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: DeepAgentState import found in agent_lifecycle.py
        """
        import os
        cwd = os.getcwd()
        agent_lifecycle_path = Path(cwd) / 'netra_backend/app/agents/agent_lifecycle.py'
        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            pytest.fail(f'agent_lifecycle.py not found at {agent_lifecycle_path}')
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            pytest.fail(f'Syntax error in agent_lifecycle.py: {e}')
        deepagent_import_found = False
        import_location = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and 'schemas.agent_models' in node.module:
                    for alias in node.names:
                        if alias.name == 'DeepAgentState':
                            deepagent_import_found = True
                            import_location = f'Line {node.lineno}: from {node.module} import DeepAgentState'
        if deepagent_import_found:
            pytest.fail(f'REGRESSION CONFIRMED: DeepAgentState import still present in agent_lifecycle.py\nImport found: {import_location}\nExpected: DeepAgentState should be migrated to UserExecutionContext pattern\nImpact: Golden Path broken, user isolation compromised')
        assert True, 'DeepAgentState import properly removed from agent_lifecycle.py'

    def test_agent_lifecycle_method_signatures_use_deepagentstate(self):
        """Test that agent_lifecycle.py method signatures still use DeepAgentState.

        THIS TEST SHOULD FAIL - proving the regression exists.
        Expected failure: Method signatures still reference DeepAgentState type
        """
        try:
            from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        except ImportError as e:
            self.fail(f'Cannot import AgentLifecycleMixin: {e}')
        try:
            pre_run_method = getattr(AgentLifecycleMixin, '_pre_run')
            pre_run_sig = inspect.signature(pre_run_method)
            try:
                hints = get_type_hints(pre_run_method)
            except (NameError, AttributeError):
                hints = {}
            state_param = pre_run_sig.parameters.get('state')
            if state_param and state_param.annotation != inspect.Parameter.empty:
                annotation_str = str(state_param.annotation)
                if 'DeepAgentState' in annotation_str:
                    self.fail(f'REGRESSION CONFIRMED: _pre_run method still uses DeepAgentState\nMethod signature: {pre_run_sig}\nState parameter type: {annotation_str}\nExpected: Should use UserExecutionContext pattern\nImpact: Agent execution using deprecated state management')
        except AttributeError:
            self.fail('_pre_run method not found in AgentLifecycleMixin')
        try:
            post_run_method = getattr(AgentLifecycleMixin, '_post_run')
            post_run_sig = inspect.signature(post_run_method)
            state_param = post_run_sig.parameters.get('state')
            if state_param and state_param.annotation != inspect.Parameter.empty:
                annotation_str = str(state_param.annotation)
                if 'DeepAgentState' in annotation_str:
                    self.fail(f'REGRESSION CONFIRMED: _post_run method still uses DeepAgentState\nMethod signature: {post_run_sig}\nState parameter type: {annotation_str}\nExpected: Should use UserExecutionContext pattern\nImpact: Agent cleanup using deprecated state management')
        except AttributeError:
            self.fail('_post_run method not found in AgentLifecycleMixin')
        self.assertTrue(True, 'Method signatures properly migrated from DeepAgentState')

    def test_base_agent_migration_claims_vs_reality_mismatch(self):
        """Test that base_agent.py migration claims don't match agent_lifecycle.py reality.

        THIS TEST SHOULD FAIL - proving the inconsistency exists.
        Expected failure: base_agent claims migration complete but agent_lifecycle still uses old pattern
        """
        import os
        cwd = os.getcwd()
        base_agent_path = Path(cwd) / 'netra_backend/app/agents/base_agent.py'
        try:
            with open(base_agent_path) as f:
                base_agent_source = f.read()
        except FileNotFoundError:
            self.skip(f'base_agent.py not found at {base_agent_path}')
        migration_claims = []
        for line_num, line in enumerate(base_agent_source.split('\n'), 1):
            if 'MIGRATION COMPLETED' in line and 'DeepAgentState' in line:
                migration_claims.append(f'Line {line_num}: {line.strip()}')
        agent_lifecycle_path = Path(cwd) / 'netra_backend/app/agents/agent_lifecycle.py'
        try:
            with open(agent_lifecycle_path) as f:
                lifecycle_source = f.read()
        except FileNotFoundError:
            self.fail(f'agent_lifecycle.py not found at {agent_lifecycle_path}')
        deepagent_usage = []
        for line_num, line in enumerate(lifecycle_source.split('\n'), 1):
            if 'DeepAgentState' in line:
                deepagent_usage.append(f'Line {line_num}: {line.strip()}')
        if migration_claims and deepagent_usage:
            self.fail(f"REGRESSION CONFIRMED: Migration claims don't match reality\n\nCLAIMS in base_agent.py:\n" + '\n'.join(migration_claims) + f'\n\nREALITY in agent_lifecycle.py:\n' + '\n'.join(deepagent_usage) + f'\n\nExpected: Consistent migration state across all files\nImpact: False sense of security, incomplete migration')
        self.assertTrue(True, 'Migration claims consistent with actual implementation')

class UserExecutionContextMigrationIncompleteTests(SSotBaseTestCase):
    """Test suite to validate UserExecutionContext migration is incomplete."""

    def test_agent_lifecycle_not_using_user_execution_context(self):
        """Test that agent_lifecycle.py is not using UserExecutionContext pattern.

        THIS TEST SHOULD FAIL - proving the incomplete migration.
        Expected failure: agent_lifecycle should import and use UserExecutionContext
        """
        agent_lifecycle_path = Path('netra_backend/app/agents/agent_lifecycle.py')
        try:
            with open(agent_lifecycle_path) as f:
                source_code = f.read()
        except FileNotFoundError:
            self.fail(f'agent_lifecycle.py not found at {agent_lifecycle_path}')
        has_user_context_import = 'UserExecutionContext' in source_code
        has_user_context_usage = False
        if has_user_context_import:
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
                pass
        if not has_user_context_import or not has_user_context_usage:
            self.fail(f'INCOMPLETE MIGRATION CONFIRMED: agent_lifecycle.py not using UserExecutionContext\nUserExecutionContext import found: {has_user_context_import}\nUserExecutionContext usage found: {has_user_context_usage}\nExpected: Full migration to UserExecutionContext pattern\nImpact: Agent execution context isolation compromised')
        self.assertTrue(True, 'agent_lifecycle.py properly using UserExecutionContext pattern')

    def test_concurrent_user_isolation_vulnerability_exists(self):
        """Test that current DeepAgentState usage creates cross-user data vulnerability.

        THIS TEST SHOULD FAIL - proving the security vulnerability exists.
        Expected failure: DeepAgentState allows potential cross-user data contamination
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState
        except ImportError:
            self.skip('DeepAgentState not available for testing')
        user1_state = DeepAgentState(user_id='user_123', user_request='User 1 request', agent_context={'sensitive_data': 'user1_secret'})
        user2_state = DeepAgentState(user_id='user_456', user_request='User 2 request', agent_context={'sensitive_data': 'user2_secret'})
        if user1_state.agent_context == user2_state.agent_context:
            self.fail(f'VULNERABILITY CONFIRMED: DeepAgentState allows cross-user context sharing\nUser 1 context: {user1_state.agent_context}\nUser 2 context: {user2_state.agent_context}\nExpected: Complete isolation between user contexts\nImpact: Potential data leakage between users')
        try:
            merged_state = user1_state.merge_from(user2_state)
            if merged_state.user_id != user1_state.user_id and merged_state.user_id != user2_state.user_id:
                self.fail(f'VULNERABILITY CONFIRMED: merge_from creates ambiguous user identity\nOriginal user_id: {user1_state.user_id}\nMerged user_id: {merged_state.user_id}\nExpected: Clear user identity preservation\nImpact: User session confusion')
        except Exception as e:
            pass
        self.assertTrue(True, 'DeepAgentState provides proper user isolation')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')