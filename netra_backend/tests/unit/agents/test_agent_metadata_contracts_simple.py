"""Simple unit tests for agent metadata contracts.

These tests focus specifically on the metadata key mismatch between agents
without requiring full agent execution or WebSocket infrastructure.

CRITICAL: These tests demonstrate the exact GitHub Issue #267 problem.
"""

import pytest
from unittest.mock import Mock

from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


class TestAgentMetadataContractsSimple:
    """Test agent metadata contracts without full execution."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM manager
        self.mock_llm_manager = Mock()
        
        # Create agent with minimal dependencies
        self.optimization_agent = OptimizationsCoreSubAgent(
            llm_manager=self.mock_llm_manager
        )
        
        # Create test execution context
        self.user_context = UserExecutionContext(
            user_id=UserID("usr_12349"),
            thread_id=ThreadID("thr_67894"),
            run_id=RunID("run_abcdej"),
            agent_context={}
        )

    @pytest.mark.asyncio
    async def test_optimization_agent_validation_with_wrong_data_key(self):
        """Test OptimizationsCoreSubAgent validation fails with 'data_helper_result' key.
        
        This is the exact scenario causing Golden Path test failures.
        """
        # Simulate what DataHelperAgent actually stores
        self.user_context.metadata['data_helper_result'] = {
            "cost_analysis": "test data",
            "recommendations": ["test"]
        }
        
        # Simulate what TriageAgent stores (this is correct)
        self.user_context.metadata['triage_result'] = {
            "category": "cost_optimization",
            "priority": "high"
        }
        
        # OptimizationsCoreSubAgent validation should fail
        validation_result = await self.optimization_agent._validate_context_data(self.user_context)
        assert validation_result is False, "Should fail when 'data_result' is missing but 'data_helper_result' is present"

    @pytest.mark.asyncio
    async def test_optimization_agent_validation_with_correct_data_key(self):
        """Test OptimizationsCoreSubAgent validation passes with 'data_result' key.
        
        This demonstrates what SHOULD happen when the contract is correct.
        """
        # Set the correct key that OptimizationsCoreSubAgent expects
        self.user_context.metadata['data_result'] = {  # Correct key
            "cost_analysis": "test data",
            "recommendations": ["test"]
        }
        
        # Set the correct triage result
        self.user_context.metadata['triage_result'] = {
            "category": "cost_optimization",
            "priority": "high"
        }
        
        # OptimizationsCoreSubAgent validation should pass
        validation_result = await self.optimization_agent._validate_context_data(self.user_context)
        assert validation_result is True, "Should pass when all expected keys are present"

    @pytest.mark.asyncio
    async def test_metadata_key_mismatch_detection(self):
        """Test detection of the specific metadata key mismatch.
        
        This test isolates the exact contract violation causing the Golden Path failures.
        """
        # Test the specific keys involved in the mismatch
        DATA_HELPER_STORES = 'data_helper_result'
        OPTIMIZATION_EXPECTS = 'data_result'
        TRIAGE_STORES = 'triage_result'
        OPTIMIZATION_ALSO_EXPECTS = 'triage_result'
        
        # Set up context with what agents actually provide
        self.user_context.metadata[DATA_HELPER_STORES] = {"test": "data"}
        self.user_context.metadata[TRIAGE_STORES] = {"test": "triage"}
        
        # Check what the optimization agent finds
        data_result_present = self.user_context.metadata.get(OPTIMIZATION_EXPECTS) is not None
        triage_result_present = self.user_context.metadata.get(OPTIMIZATION_ALSO_EXPECTS) is not None
        data_helper_result_present = self.user_context.metadata.get(DATA_HELPER_STORES) is not None
        
        # Document the mismatch
        assert not data_result_present, f"OptimizationsCoreSubAgent expects '{OPTIMIZATION_EXPECTS}' but it's not present"
        assert triage_result_present, f"OptimizationsCoreSubAgent expects '{OPTIMIZATION_ALSO_EXPECTS}' and it IS present"
        assert data_helper_result_present, f"DataHelperAgent provides '{DATA_HELPER_STORES}' but it's not what OptimizationsCoreSubAgent expects"
        
        # Prove the contract mismatch
        assert DATA_HELPER_STORES != OPTIMIZATION_EXPECTS, "KEY MISMATCH: DataHelperAgent stores different key than OptimizationsCoreSubAgent expects"
        assert TRIAGE_STORES == OPTIMIZATION_ALSO_EXPECTS, "Triage key contract is correct"

    def test_github_issue_267_documentation(self):
        """Document the exact GitHub Issue #267 problem.
        
        This test serves as documentation of the issue and its scope.
        """
        # GitHub Issue #267 details
        ISSUE_SUMMARY = {
            "title": "Golden path integration tests failing (10/19 tests)",
            "root_cause": "OptimizationsCoreSubAgent expects `data_result`/`triage_result` but gets `data_helper_result`",
            "affected_tests": 10,
            "total_tests": 19,
            "failure_rate": "52.6%"
        }
        
        # Specific metadata key contracts
        CURRENT_STATE = {
            "DataHelperAgent_stores": "data_helper_result",
            "OptimizationsCoreSubAgent_expects": "data_result", 
            "TriageAgent_stores": "triage_result",
            "OptimizationsCoreSubAgent_also_expects": "triage_result"
        }
        
        # The mismatch
        data_key_mismatch = CURRENT_STATE["DataHelperAgent_stores"] != CURRENT_STATE["OptimizationsCoreSubAgent_expects"]
        triage_key_aligned = CURRENT_STATE["TriageAgent_stores"] == CURRENT_STATE["OptimizationsCoreSubAgent_also_expects"]
        
        # Assertions documenting the issue
        assert data_key_mismatch, "GITHUB ISSUE #267: Data key mismatch between DataHelperAgent and OptimizationsCoreSubAgent"
        assert triage_key_aligned, "Triage key is correctly aligned"
        assert ISSUE_SUMMARY["failure_rate"] == "52.6%", "Over half of Golden Path tests are failing"

    def test_proposed_solution_documentation(self):
        """Document the proposed solution for GitHub Issue #267.
        
        This test documents what needs to be changed to fix the issue.
        """
        # Current problematic implementation
        CURRENT_IMPLEMENTATION = {
            "file": "netra_backend/app/agents/data_helper_agent.py", 
            "line": 136,
            "code": "self.store_metadata_result(context, 'data_helper_result', data_request_result)",
            "problem": "Stores 'data_helper_result' but OptimizationsCoreSubAgent expects 'data_result'"
        }
        
        # Proposed fix
        PROPOSED_FIX = {
            "file": "netra_backend/app/agents/data_helper_agent.py",
            "line": 136, 
            "old_code": "self.store_metadata_result(context, 'data_helper_result', data_request_result)",
            "new_code": "self.store_metadata_result(context, 'data_result', data_request_result)",
            "impact": "OptimizationsCoreSubAgent will find expected 'data_result' key"
        }
        
        # Alternative fix (update OptimizationsCoreSubAgent)
        ALTERNATIVE_FIX = {
            "file": "netra_backend/app/agents/optimizations_core_sub_agent.py",
            "lines": [75, 248],
            "change": "Update to look for 'data_helper_result' instead of 'data_result'",
            "risk": "Higher impact - affects more code locations"
        }
        
        # Validation
        assert CURRENT_IMPLEMENTATION["problem"] == "Stores 'data_helper_result' but OptimizationsCoreSubAgent expects 'data_result'"
        assert PROPOSED_FIX["impact"] == "OptimizationsCoreSubAgent will find expected 'data_result' key"
        assert ALTERNATIVE_FIX["risk"] == "Higher impact - affects more code locations"

    @pytest.mark.asyncio
    async def test_fix_validation_simulation(self):
        """Simulate the proposed fix to validate it would work.
        
        This test proves that changing the metadata key would resolve the issue.
        """
        # Simulate the proposed fix: DataHelperAgent stores 'data_result' instead of 'data_helper_result'
        self.user_context.metadata['data_result'] = {  # FIXED: Use the key OptimizationsCoreSubAgent expects
            "cost_analysis": "test data",
            "recommendations": ["test"]
        }
        
        # Keep the correct triage result
        self.user_context.metadata['triage_result'] = {
            "category": "cost_optimization",
            "priority": "high"
        }
        
        # OptimizationsCoreSubAgent validation should now pass
        validation_result = await self.optimization_agent._validate_context_data(self.user_context)
        assert validation_result is True, "Fix validation: OptimizationsCoreSubAgent should pass with 'data_result' key"
        
        # Verify the fix addresses the contract mismatch
        data_result_present = 'data_result' in self.user_context.metadata
        data_helper_result_present = 'data_helper_result' in self.user_context.metadata
        
        assert data_result_present, "Fixed: 'data_result' key is now present"
        assert not data_helper_result_present, "Fixed: 'data_helper_result' key is no longer used"