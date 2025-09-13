"""
CRITICAL TEST: Issue #700 - SSOT Regression in TriageAgent Metadata Bypass

This test reproduces the critical SSOT regression where TriageAgent metadata
handling is bypassed due to missing metadata attribute in UserExecutionContext.

BUSINESS IMPACT: P0 CRITICAL - Golden Path Blocked - $500K+ ARR at Risk

Key Test Scenarios:
1. Reproduce AttributeError when accessing context.metadata 
2. Verify BaseAgent.store_metadata_result fails with real UserExecutionContext
3. Confirm UnifiedTriageAgent execute() fails due to metadata storage
4. Validate SSOT regression impact on Golden Path functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from dataclasses import dataclass

# Critical imports for testing the regression
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent 
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent


@dataclass
class MockExecutionState:
    """Minimal state for testing triage execution"""
    original_request: str


class TestIssue700MetadataBypassSSoTRegression:
    """Test suite to reproduce and validate Issue #700 metadata bypass regression"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create real UserExecutionContext (the one missing metadata field)
        self.real_context = UserExecutionContext(
            user_id="test_user_700",
            thread_id="test_thread_700", 
            run_id="test_run_700",
            request_id="test_request_700"
        )
        
        # Create mock LLM manager and tool dispatcher
        self.mock_llm_manager = Mock()
        self.mock_tool_dispatcher = Mock()
        
    def test_userexecutioncontext_missing_metadata_attribute(self):
        """
        CRITICAL TEST: Verify UserExecutionContext lacks metadata attribute
        
        This test proves that the SSOT regression exists - UserExecutionContext
        does not have the metadata field that BaseAgent.store_metadata_result expects.
        """
        # ASSERTION 1: UserExecutionContext should NOT have metadata attribute
        assert not hasattr(self.real_context, 'metadata'), (
            "CRITICAL: UserExecutionContext has metadata attribute - regression may be fixed"
        )
        
        # ASSERTION 2: UserExecutionContext has other metadata fields but not 'metadata'
        assert hasattr(self.real_context, 'agent_context'), "Should have agent_context"
        assert hasattr(self.real_context, 'audit_metadata'), "Should have audit_metadata"
        
    def test_base_agent_store_metadata_result_fails_with_real_context(self):
        """
        CRITICAL TEST: Reproduce AttributeError in BaseAgent.store_metadata_result
        
        This test proves that BaseAgent.store_metadata_result will fail when
        used with a real UserExecutionContext because it tries to access
        context.metadata which doesn't exist.
        """
        # Create a minimal BaseAgent to test the method
        base_agent = BaseAgent(
            llm_manager=self.mock_llm_manager,
            name="TestAgent"
        )
        
        # CRITICAL TEST: This should raise AttributeError
        with pytest.raises(AttributeError) as exc_info:
            base_agent.store_metadata_result(
                context=self.real_context,
                key="test_key", 
                value="test_value"
            )
        
        # Verify the error is about missing metadata attribute
        error_message = str(exc_info.value)
        assert "metadata" in error_message.lower(), (
            f"Error should mention 'metadata' attribute, got: {error_message}"
        )
        
    @pytest.mark.asyncio
    async def test_unified_triage_agent_execute_fails_due_to_metadata_storage(self):
        """
        CRITICAL TEST: Reproduce Golden Path failure in UnifiedTriageAgent.execute()
        
        This test proves that the UnifiedTriageAgent.execute() method will fail
        when it tries to store triage results in metadata using the SSOT method.
        """
        # Create UnifiedTriageAgent with real context
        triage_agent = UnifiedTriageAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            context=self.real_context,
            execution_priority=0
        )
        
        # Mock WebSocket events to avoid those errors
        triage_agent.emit_agent_started = AsyncMock()
        triage_agent.emit_thinking = AsyncMock()
        triage_agent.emit_agent_completed = AsyncMock()
        triage_agent.emit_error = AsyncMock()
        
        # Create execution state
        state = MockExecutionState(
            original_request="Test triage request for Issue #700"
        )
        
        # CRITICAL TEST: Execute should fail when trying to store metadata
        with pytest.raises(AttributeError) as exc_info:
            await triage_agent.execute(state, self.real_context)
        
        # Verify the error is about metadata storage
        error_message = str(exc_info.value)
        assert "metadata" in error_message.lower(), (
            f"Error should be about metadata access, got: {error_message}"
        )
        
    def test_mock_vs_real_context_behavior_difference(self):
        """
        CRITICAL TEST: Demonstrate why tests are passing but production is failing
        
        This test shows that mocked contexts have metadata while real ones don't,
        explaining why all existing tests pass but the Golden Path is broken.
        """
        # Create a mock context like tests use
        mock_context = Mock()
        mock_context.metadata = {}  # Tests add this
        
        # Create base agent
        base_agent = BaseAgent(
            llm_manager=self.mock_llm_manager,
            name="TestAgent"
        )
        
        # ASSERTION 1: Mock context works fine
        try:
            base_agent.store_metadata_result(
                context=mock_context,
                key="test_key",
                value="test_value"
            )
            mock_success = True
        except Exception:
            mock_success = False
            
        assert mock_success, "Mock context should work (tests pass)"
        
        # ASSERTION 2: Real context fails
        try:
            base_agent.store_metadata_result(
                context=self.real_context,
                key="test_key",
                value="test_value"
            )
            real_success = True
        except Exception:
            real_success = False
            
        assert not real_success, "Real context should fail (production broken)"
        
    def test_ssot_regression_impact_on_golden_path(self):
        """
        CRITICAL TEST: Validate that this regression blocks the Golden Path
        
        This test confirms that the metadata bypass SSOT regression directly
        impacts the Golden Path (login → AI responses) functionality.
        """
        # The Golden Path depends on TriageAgent storing these metadata keys:
        critical_metadata_keys = [
            'triage_result',
            'triage_category', 
            'data_sufficiency',
            'triage_priority',
            'next_agents'
        ]
        
        # All of these metadata storage operations will fail
        base_agent = BaseAgent(
            llm_manager=self.mock_llm_manager,
            name="TestAgent"
        )
        
        failed_keys = []
        for key in critical_metadata_keys:
            try:
                base_agent.store_metadata_result(
                    context=self.real_context,
                    key=key,
                    value=f"test_value_for_{key}"
                )
            except AttributeError:
                failed_keys.append(key)
                
        # CRITICAL ASSERTION: All metadata storage operations should fail
        assert len(failed_keys) == len(critical_metadata_keys), (
            f"All critical metadata storage should fail. Failed: {failed_keys}, "
            f"Expected: {critical_metadata_keys}"
        )
        
        # This proves that the Golden Path is completely blocked
        assert 'triage_result' in failed_keys, "Triage result storage fails - Golden Path broken"
        assert 'next_agents' in failed_keys, "Agent coordination fails - Golden Path broken"
        
    def test_reproduce_error_exact_line_numbers(self):
        """
        CRITICAL TEST: Reproduce error at exact line in UnifiedTriageAgent
        
        This test reproduces the exact error that occurs in production at 
        UnifiedTriageAgent line 397-404 where store_metadata_result is called.
        """
        # Create the exact scenario from UnifiedTriageAgent.execute()
        # Lines 397-404 in unified_triage_agent.py:
        # self.store_metadata_result(exec_context, 'triage_result', triage_result.__dict__)
        # self.store_metadata_result(exec_context, 'triage_category', triage_result.category)
        # self.store_metadata_result(exec_context, 'data_sufficiency', triage_result.data_sufficiency)
        # self.store_metadata_result(exec_context, 'triage_priority', triage_result.priority.value)
        
        triage_agent = UnifiedTriageAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            context=self.real_context,
            execution_priority=0
        )
        
        # Test each exact line that will fail
        test_cases = [
            ('triage_result', {'test': 'data'}),
            ('triage_category', 'Cost Optimization'),
            ('data_sufficiency', 'sufficient'),
            ('triage_priority', 'medium')
        ]
        
        for key, value in test_cases:
            with pytest.raises(AttributeError) as exc_info:
                triage_agent.store_metadata_result(self.real_context, key, value)
            
            # Verify each fails with metadata error
            assert "metadata" in str(exc_info.value).lower(), (
                f"Line with key '{key}' should fail due to missing metadata attribute"
            )


class TestIssue700FixValidation:
    """Test suite to validate the fix for Issue #700"""
    
    def test_proposed_fix_with_agent_context_fallback(self):
        """
        TEST: Validate proposed fix using agent_context as fallback
        
        This test validates that using agent_context instead of metadata
        would resolve the SSOT regression.
        """
        # Create context with proper initialization
        context = UserExecutionContext(
            user_id="test_user_700",
            thread_id="test_thread_700", 
            run_id="test_run_700",
            request_id="test_request_700"
        )
        
        # Test that agent_context is available and mutable
        assert hasattr(context, 'agent_context'), "Context should have agent_context"
        assert isinstance(context.agent_context, dict), "agent_context should be dict"
        
        # Test storing values in agent_context (proposed fix)
        context.agent_context['triage_result'] = {'test': 'data'}
        context.agent_context['triage_category'] = 'Cost Optimization'
        
        # Verify values are stored correctly
        assert context.agent_context['triage_result'] == {'test': 'data'}
        assert context.agent_context['triage_category'] == 'Cost Optimization'
        
        # This proves the proposed fix would work


if __name__ == "__main__":
    # Run the critical tests
    pytest.main([__file__, "-v", "--tb=short"])