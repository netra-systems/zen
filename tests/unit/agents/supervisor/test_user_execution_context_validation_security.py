"""SSOT Test Suite for UserExecutionContext Security Validation (Issue #346)

This test suite validates that the enhanced UserExecutionContext security validation
in agent_execution_core.py properly rejects Mock objects and enforces real context
requirements for user isolation and security.

Business Value Justification (BVJ):
- Segment: ALL (Enterprise security requirement)
- Business Goal: Security/Compliance (prevent data leakage)
- Value Impact: Protects $500K+ ARR by ensuring proper user isolation
- Revenue Impact: Prevents security breaches that could lose enterprise customers

Test Strategy:
1. FAILING TEST: Reproduce Mock rejection behavior (should fail initially)
2. VALIDATION TEST: Verify correct UserExecutionContext pattern works
3. SECURITY TEST: Validate comprehensive security validation
4. MIGRATION TEST: Provide template for other test migrations

SSOT Compliance:
- Inherits from SSotAsyncTestCase (test_framework/ssot/)
- Uses real UserExecutionContext (no mocks for core security)
- Follows absolute import patterns
- Tests business-critical security behavior
"""
import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from shared.types.core_types import UserID, ThreadID, RunID

class TestUserExecutionContextValidationSecurity(SSotAsyncTestCase):
    """Test suite for UserExecutionContext security validation in AgentExecutionCore.
    
    This test class validates Issue #346: Enhanced UserExecutionContext validation
    breaking 192 test files using Mock objects. Tests ensure security validation
    works correctly while providing migration patterns.
    """

    def setup_method(self, method=None):
        """Set up test fixtures with real components (no mocks for core security)."""
        super().setup_method(method)
        from unittest.mock import Mock
        mock_registry = Mock()
        self.agent_core = AgentExecutionCore(registry=mock_registry)
        self.logger = logging.getLogger(__name__)
        self.agent_context = AgentExecutionContext(run_id='test_run_123', thread_id='test_thread_456', user_id='test_user_789', agent_name='TestAgent', correlation_id='test_correlation_001')

    def test_execute_agent_rejects_mock_objects_for_security(self):
        """FAILING TEST: Demonstrates Mock objects are properly rejected for security.
        
        This test SHOULD FAIL initially, proving that the security validation
        is working correctly by rejecting Mock objects that could bypass user
        isolation safeguards.
        
        Expected Result: ValueError with clear security message
        Business Impact: Protects $500K+ ARR from user data contamination
        """
        mock_user_context = Mock()
        mock_user_context.__class__.__name__ = 'Mock'
        with pytest.raises(ValueError) as exc_info:
            self.agent_core._validate_user_execution_context(mock_user_context, self.agent_context)
        error_message = str(exc_info.value)
        self.assertIn('Expected UserExecutionContext', error_message)
        self.assertIn("got <class 'unittest.mock.Mock'>", error_message)
        self.assertIn('DeepAgentState is no longer supported', error_message)
        self.logger.info(f' PASS:  SECURITY VALIDATION SUCCESS: Mock object properly rejected with error: {error_message}')

    def test_execute_agent_rejects_deep_agent_state_with_security_message(self):
        """Test that DeepAgentState attempts get specific security error message.
        
        Validates that the migration from DeepAgentState provides clear security
        guidance for developers attempting to use the deprecated pattern.
        """
        mock_deep_state = Mock()
        mock_deep_state.__class__.__name__ = 'DeepAgentState'
        with pytest.raises(ValueError) as exc_info:
            self.agent_core._validate_user_execution_context(mock_deep_state, self.agent_context)
        error_message = str(exc_info.value)
        self.assertIn(' ALERT:  SECURITY VULNERABILITY', error_message)
        self.assertIn('DeepAgentState is FORBIDDEN', error_message)
        self.assertIn('user isolation risks', error_message)
        self.assertIn('data leakage between users', error_message)
        self.assertIn('issue #271 remediation plan', error_message)
        self.logger.info(f' PASS:  DEEP_AGENT_STATE SECURITY: Specific guidance provided: {error_message[:100]}...')

    def test_execute_agent_accepts_real_user_execution_context(self):
        """VALIDATION TEST: Demonstrates correct UserExecutionContext pattern works.
        
        This test should PASS and serve as a template for migrating other tests
        from Mock objects to proper UserExecutionContext usage.
        
        Expected Result: Successful validation without errors
        Business Value: Template for systematic migration of 192 failing tests
        """
        real_user_context = UserExecutionContext(user_id='real_user_123', thread_id='real_thread_456', run_id='real_run_789', request_id='real_request_001', websocket_client_id='ws_client_123', agent_context={'test': 'data'}, audit_metadata={'validation': 'test'})
        validated_context = self.agent_core._validate_user_execution_context(real_user_context, self.agent_context)
        self.assertTrue(isinstance(validated_context, UserExecutionContext))
        self.assertEqual(validated_context.user_id, 'real_user_123')
        self.assertEqual(validated_context.thread_id, 'real_thread_456')
        self.assertEqual(validated_context.run_id, 'real_run_789')
        self.logger.info(f' PASS:  REAL CONTEXT SUCCESS: UserExecutionContext validated successfully: user_id={validated_context.user_id}, thread_id={validated_context.thread_id}')

    def test_user_execution_context_missing_required_fields(self):
        """Test validation of required UserExecutionContext fields.
        
        Validates that UserExecutionContext security validation ensures all
        required fields are present and not placeholder values.
        """
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(user_id='', thread_id='thread_123', run_id='run_456')
        error_message = str(exc_info.value)
        self.assertIn('Invalid user_id', error_message)
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(user_id='user_123', thread_id='', run_id='run_456')
        error_message = str(exc_info.value)
        self.assertIn('Invalid thread_id', error_message)
        with pytest.raises(ValueError) as exc_info:
            UserExecutionContext(user_id='user_123', thread_id='thread_456', run_id='')
        error_message = str(exc_info.value)
        self.assertIn('Invalid run_id', error_message)

    def test_user_execution_context_placeholder_value_detection(self):
        """Test that placeholder values are detected and rejected.
        
        Validates comprehensive placeholder detection including common
        test placeholder patterns that could bypass security validation.
        """
        placeholder_patterns = ['test_user', 'mock_user', 'fake_user', 'dummy_user', 'placeholder', 'TODO', 'FIXME', 'temp_', 'example_']
        for placeholder in placeholder_patterns:
            with pytest.raises(ValueError) as exc_info:
                UserExecutionContext(user_id=placeholder, thread_id='thread_123', run_id='run_456')
            error_message = str(exc_info.value)
            self.assertIn('placeholder or test value detected', error_message)
            self.logger.debug(f" PASS:  Placeholder '{placeholder}' properly rejected")

    async def test_execute_agent_end_to_end_with_real_context(self):
        """Integration test: Full execute_agent flow with real UserExecutionContext.
        
        This test validates the complete execute_agent method works correctly
        with proper UserExecutionContext, serving as validation for the
        security migration.
        
        Business Impact: Ensures core agent execution still works after security fixes
        """
        real_user_context = UserExecutionContext(user_id='integration_user_123', thread_id='integration_thread_456', run_id='integration_run_789', websocket_client_id='ws_integration_001')
        with patch.object(self.agent_core, 'agent_registry') as mock_registry:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = 'Test agent execution successful'
            mock_registry.get_agent.return_value = mock_agent
            result = await self.agent_core.execute_agent(context=self.agent_context, user_context=real_user_context, timeout=30.0)
            self.assertTrue(isinstance(result, AgentExecutionResult))
            self.assertTrue(result.success)
            self.assertEqual(result.agent_name, 'TestAgent')
            self.logger.info(f' PASS:  END-TO-END SUCCESS: Agent execution completed with real context: success={result.success}, agent={result.agent_name}')

    def test_migration_pattern_documentation(self):
        """Documentation test: Provides migration patterns for other tests.
        
        This test serves as executable documentation showing how to migrate
        from Mock objects to real UserExecutionContext patterns.
        """
        real_context = UserExecutionContext(user_id='migration_example_user', thread_id='migration_example_thread', run_id='migration_example_run', agent_context={'migration': 'example'}, audit_metadata={'test_type': 'migration_pattern'})
        validated = self.agent_core._validate_user_execution_context(real_context, self.agent_context)
        self.assertTrue(isinstance(validated, UserExecutionContext))
        self.assertEqual(validated.user_id, 'migration_example_user')
        self.logger.info(' PASS:  MIGRATION PATTERN: Real UserExecutionContext pattern validated for migration guide')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')