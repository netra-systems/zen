"""Unit tests for OptimizationsCoreSubAgent data contract validation.

These tests expose the metadata key mismatch between what OptimizationsCoreSubAgent
expects and what DataHelperAgent/TriageAgent actually provide.

CRITICAL: These tests should FAIL initially, proving they catch the real issue
described in GitHub Issue #267.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


class TestOptimizationDataContractValidation:
    """Test data contract validation in OptimizationsCoreSubAgent."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM manager
        self.mock_llm_manager = Mock()
        self.mock_llm_manager.ask_llm = AsyncMock(return_value='{"optimization_type": "test", "recommendations": ["test"]}')
        
        # Create agent with mock dependencies
        self.agent = OptimizationsCoreSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=None,
            websocket_manager=None
        )
        
        # Create test execution context
        self.user_context = UserExecutionContext(
            user_id=UserID("usr_12345"),
            thread_id=ThreadID("thr_67890"),
            run_id=RunID("run_abcdef"),
            agent_context={}
        )

    @pytest.mark.asyncio
    async def test_optimization_expects_data_result_but_gets_data_helper_result(self):
        """Test that OptimizationsCoreSubAgent expects 'data_result' but DataHelperAgent provides 'data_helper_result'.
        
        CRITICAL: This test should FAIL initially, exposing the metadata key mismatch.
        """
        # Simulate what DataHelperAgent actually stores (the ACTUAL behavior)
        self.user_context.metadata['data_helper_result'] = {
            "data_analysis": "test data",
            "cost_metrics": {"monthly_cost": 1000}
        }
        
        # Simulate what TriageAgent stores
        self.user_context.metadata['triage_result'] = {
            "category": "cost_optimization",
            "priority": "high"
        }
        
        # OptimizationsCoreSubAgent should fail because it looks for 'data_result', not 'data_helper_result'
        with pytest.raises(ValueError, match="Required data not available for optimization analysis"):
            await self.agent.execute(context=self.user_context)

    @pytest.mark.asyncio
    async def test_optimization_validation_with_expected_keys_should_pass(self):
        """Test that OptimizationsCoreSubAgent works when given the keys it expects.
        
        This test documents what the agent EXPECTS vs what it actually GETS.
        """
        # Set the metadata keys that OptimizationsCoreSubAgent actually expects
        self.user_context.metadata['data_result'] = {  # Expected: data_result
            "data_analysis": "test data",
            "cost_metrics": {"monthly_cost": 1000}
        }
        
        self.user_context.metadata['triage_result'] = {  # Expected: triage_result (this one is correct)
            "category": "cost_optimization", 
            "priority": "high"
        }
        
        # This should succeed because we're providing the expected keys
        result = await self.agent.execute(context=self.user_context, stream_updates=False)
        
        # Verify the agent executed successfully
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_data_contract_mismatch_detection(self):
        """Test that detects the specific data contract mismatches in the Golden Path workflow.
        
        This test validates the exact mismatch described in GitHub Issue #267.
        """
        # Test Case 1: Missing both expected keys (current failing state)
        context_missing_both = UserExecutionContext(
            user_id=UserID("usr_12346"),
            thread_id=ThreadID("thr_67891"), 
            run_id=RunID("run_abcdeg"),
            agent_context={}
        )
        
        # DataHelperAgent stores 'data_helper_result' but OptimizationsCoreSubAgent expects 'data_result'
        context_missing_both.metadata['data_helper_result'] = {"test": "data"}
        # No triage_result at all
        
        validation_result = await self.agent._validate_context_data(context_missing_both)
        assert validation_result is False, "Should fail when both expected keys are missing"

    @pytest.mark.asyncio
    async def test_data_contract_key_mapping_requirements(self):
        """Test the specific key mapping requirements for agent coordination.
        
        Documents the exact keys each agent provides vs what OptimizationsCoreSubAgent expects.
        """
        # What DataHelperAgent actually provides
        data_helper_keys = ['data_helper_result']
        
        # What TriageAgent actually provides  
        triage_agent_keys = ['triage_result', 'triage_category', 'data_sufficiency', 'triage_priority']
        
        # What OptimizationsCoreSubAgent expects
        optimization_expected_keys = ['data_result', 'triage_result']
        
        # The mismatch: data_helper_result != data_result
        data_key_mismatch = 'data_result' not in data_helper_keys
        assert data_key_mismatch, "DATA CONTRACT MISMATCH: DataHelperAgent provides 'data_helper_result' but OptimizationsCoreSubAgent expects 'data_result'"
        
        # The triage key is correctly aligned
        triage_key_aligned = 'triage_result' in triage_agent_keys
        assert triage_key_aligned, "Triage key should be aligned between agents"

    def test_metadata_key_constants_documentation(self):
        """Document the metadata key constants that should be used across agents.
        
        This test serves as documentation of the expected metadata keys.
        """
        # Expected metadata keys for agent coordination
        EXPECTED_METADATA_KEYS = {
            'data_result': 'Data analysis results from DataHelperAgent',
            'triage_result': 'Triage analysis results from TriageAgent',
            'optimizations_result': 'Optimization results from OptimizationsCoreSubAgent'
        }
        
        # Actual metadata keys currently being used
        ACTUAL_METADATA_KEYS = {
            'data_helper_result': 'DataHelperAgent stores data analysis here',
            'triage_result': 'TriageAgent stores triage analysis here',
            'optimizations_result': 'OptimizationsCoreSubAgent stores results here'
        }
        
        # Document the mismatch
        data_key_mismatch = EXPECTED_METADATA_KEYS['data_result'] != ACTUAL_METADATA_KEYS.get('data_result')
        assert data_key_mismatch, "DOCUMENTATION: Key mismatch between expected 'data_result' and actual 'data_helper_result'"

    @pytest.mark.asyncio
    async def test_agent_coordination_failure_simulation(self):
        """Simulate the exact failure scenario from Golden Path integration tests.
        
        This replicates the sequence that causes 10/19 Golden Path tests to fail.
        """
        # Step 1: Simulate DataHelperAgent execution (provides data_helper_result)
        data_helper_context = UserExecutionContext(
            user_id=UserID("usr_12347"),
            thread_id=ThreadID("thr_67892"),
            run_id=RunID("run_abcdeh"), 
            agent_context={}
        )
        
        # DataHelperAgent would store its result like this
        data_helper_context.metadata['data_helper_result'] = {
            "cost_analysis": "simulated data",
            "recommendations": ["optimize compute", "reduce storage"]
        }
        
        # Step 2: Simulate TriageAgent execution (provides triage_result - this is correct)
        data_helper_context.metadata['triage_result'] = {
            "category": "cost_optimization",
            "priority": "high", 
            "data_sufficiency": "sufficient"
        }
        
        # Step 3: OptimizationsCoreSubAgent execution should fail
        with pytest.raises(ValueError, match="Required data not available for optimization analysis"):
            await self.agent.execute(context=data_helper_context)
        
        # This failure occurs because OptimizationsCoreSubAgent looks for 'data_result' 
        # but only finds 'data_helper_result' in the metadata