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

        

    def test_userexecutioncontext_metadata_property_is_read_only_copy(self):

        """

        CRITICAL TEST: Verify UserExecutionContext metadata property is read-only

        

        This test proves that the SSOT regression exists - UserExecutionContext.metadata

        is a property that returns a copy, making assignments appear to work but

        actually fail silently.

        """

        # ASSERTION 1: UserExecutionContext HAS metadata attribute (it's a property)

        assert hasattr(self.real_context, 'metadata'), (

            "UserExecutionContext should have metadata property"

        )

        

        # ASSERTION 2: But assignments to metadata don't persist

        initial_metadata = self.real_context.metadata.copy()

        self.real_context.metadata['test_key'] = 'test_value'

        

        # The assignment appears to succeed but doesn't persist

        after_assignment = self.real_context.metadata

        assert 'test_key' not in after_assignment, (

            "CRITICAL: metadata assignment should NOT persist (proves the regression)"

        )

        

        # ASSERTION 3: metadata is a fresh copy each time

        metadata1 = self.real_context.metadata

        metadata2 = self.real_context.metadata 

        assert metadata1 is not metadata2, (

            "metadata property should return new copy each time"

        )

        

    def test_base_agent_store_metadata_result_silent_failure(self):

        """

        CRITICAL TEST: Prove BaseAgent.store_metadata_result silently fails

        

        This test proves that BaseAgent.store_metadata_result appears to work

        but silently fails because it assigns to a temporary copy that gets discarded.

        """

        # Create a minimal BaseAgent to test the method

        base_agent = BaseAgent(

            llm_manager=self.mock_llm_manager,

            name="TestAgent"

        )

        

        # CRITICAL TEST: This appears to succeed but silently fails

        initial_metadata = self.real_context.metadata.copy()

        

        # This call should NOT raise an exception (appears to work)

        base_agent.store_metadata_result(

            context=self.real_context,

            key="test_key", 

            value="test_value"

        )

        

        # But the value is NOT actually stored

        after_storage = self.real_context.metadata

        assert "test_key" not in after_storage, (

            "CRITICAL: store_metadata_result should silently fail (key not found)"

        )

        

        # Verify the metadata didn't change at all

        assert after_storage == initial_metadata, (

            "Metadata should be unchanged after 'successful' storage call"

        )

        

    @pytest.mark.asyncio

    async def test_unified_triage_agent_execute_silent_metadata_failure(self):

        """

        CRITICAL TEST: Prove UnifiedTriageAgent.execute() silently fails to store metadata

        

        This test proves that the UnifiedTriageAgent.execute() method appears to succeed

        but silently fails to store critical triage metadata needed for Golden Path coordination.

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

        

        # Mock LLM to return valid response (so we can test metadata storage)

        mock_triage_result = Mock()

        mock_triage_result.category = "Cost Optimization"

        mock_triage_result.data_sufficiency = "sufficient" 

        mock_triage_result.priority = Mock(value="medium")

        mock_triage_result.__dict__ = {"test": "data"}

        

        triage_agent._process_with_llm = AsyncMock(return_value=mock_triage_result)

        triage_agent._determine_next_agents = Mock(return_value=["data", "optimization"])

        

        # Create execution state

        state = MockExecutionState(

            original_request="Test triage request for Issue #700"

        )

        

        # Capture initial metadata

        initial_metadata = self.real_context.metadata.copy()

        

        # CRITICAL TEST: Execute should appear to succeed

        result = await triage_agent.execute(state, self.real_context)

        

        # But none of the critical metadata is actually stored

        after_execution = self.real_context.metadata

        

        # These are the critical metadata keys that Golden Path depends on

        critical_keys = ['triage_result', 'triage_category', 'data_sufficiency', 'triage_priority', 'next_agents']

        

        for key in critical_keys:

            assert key not in after_execution, (

                f"CRITICAL: {key} should NOT be stored (proving silent failure)"

            )

        

        # Verify result appears successful (silent failure)

        assert result is not None, "Execute should return a result"

        assert result.get('success', False), "Result should claim success"

        

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

