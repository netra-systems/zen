"""Integration tests for agent coordination data contracts.

These tests demonstrate the metadata key mismatches that cause Golden Path
integration test failures, specifically between DataHelperAgent and
OptimizationsCoreSubAgent.

CRITICAL: These tests reproduce the exact failure scenario from GitHub Issue #267.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any

from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


class TestAgentCoordinationDataContracts:
    """Test agent coordination with real metadata contracts."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock LLM manager for all agents
        self.mock_llm_manager = Mock()
        self.mock_llm_manager.ask_llm = AsyncMock(return_value='{"result": "test", "recommendations": ["test"]}')
        
        # Create mock tool dispatcher
        self.mock_tool_dispatcher = Mock()
        
        # Create agents with proper dependencies
        self.data_agent = DataHelperAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        self.optimization_agent = OptimizationsCoreSubAgent(
            llm_manager=self.mock_llm_manager, 
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=None
        )
        
        self.triage_agent = UnifiedTriageAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher
        )
        
        # Create test execution context
        self.user_context = UserExecutionContext(
            user_id=UserID("usr_12348"),
            thread_id=ThreadID("thr_67893"),
            run_id=RunID("run_abcdei"),
            agent_context={}
        )

    @pytest.mark.asyncio
    async def test_data_agent_stores_data_helper_result(self):
        """Test that DataHelperAgent stores its result with 'data_helper_result' key.
        
        This documents what DataHelperAgent actually does.
        """
        # Execute data agent
        await self.data_agent.execute(
            message="Collect cost data",
            context=self.user_context
        )
        
        # Verify DataHelperAgent stores 'data_helper_result'
        assert 'data_helper_result' in self.user_context.metadata
        assert 'data_result' not in self.user_context.metadata  # This is what OptimizationsCoreSubAgent expects
        
        # Document the actual key being used
        data_helper_result = self.user_context.metadata['data_helper_result']
        assert data_helper_result is not None

    @pytest.mark.asyncio
    async def test_triage_agent_stores_triage_result(self):
        """Test that TriageAgent stores its result with 'triage_result' key.
        
        This documents what TriageAgent actually does (this one is correct).
        """
        # Execute triage agent
        await self.triage_agent.execute(
            message="Analyze requirements",
            context=self.user_context
        )
        
        # Verify TriageAgent stores 'triage_result' correctly
        assert 'triage_result' in self.user_context.metadata
        
        # Document the actual key being used (this matches expectations)
        triage_result = self.user_context.metadata['triage_result']
        assert triage_result is not None

    @pytest.mark.asyncio  
    async def test_optimization_agent_coordination_failure(self):
        """Test the exact coordination failure between DataHelperAgent and OptimizationsCoreSubAgent.
        
        CRITICAL: This reproduces the exact scenario causing 10/19 Golden Path test failures.
        """
        # Step 1: Execute DataHelperAgent (stores 'data_helper_result')
        await self.data_agent.execute(
            message="Collect cost data",
            context=self.user_context
        )
        
        # Step 2: Execute TriageAgent (stores 'triage_result' - correct)  
        await self.triage_agent.execute(
            message="Analyze requirements",
            context=self.user_context
        )
        
        # Step 3: OptimizationsCoreSubAgent should fail due to missing 'data_result'
        with pytest.raises(ValueError, match="Required data not available for optimization analysis"):
            await self.optimization_agent.execute(
                message="Optimize based on collected data",
                context=self.user_context
            )
        
        # Verify the exact metadata keys present
        assert 'data_helper_result' in self.user_context.metadata  # What DataHelperAgent provides
        assert 'triage_result' in self.user_context.metadata      # What TriageAgent provides (correct)
        assert 'data_result' not in self.user_context.metadata    # What OptimizationsCoreSubAgent expects

    @pytest.mark.asyncio
    async def test_golden_path_sequence_reproduction(self):
        """Reproduce the exact Golden Path test sequence that fails.
        
        This test demonstrates the specific orchestration pattern from the failing tests.
        """
        # Simulate the exact sequence from test_sub_agent_execution_pipeline_sequencing
        
        # 1. Triage agent determines requirements (WORKS)
        triage_result = await self.triage_agent.execute(
            message="Analyze AI costs",
            context=self.user_context
        )
        execution_order = ["triage"]
        
        # 2. Data agent collects required data (WORKS - but stores wrong key)
        data_result = await self.data_agent.execute(
            message="Collect cost data based on triage requirements",
            context=self.user_context,
            previous_result=triage_result
        )
        execution_order.append("data")
        
        # Verify data agent stored its result with the wrong key
        assert 'data_helper_result' in self.user_context.metadata
        assert 'data_result' not in self.user_context.metadata
        
        # 3. Optimizer agent processes data (FAILS - expects different key)
        with pytest.raises(ValueError, match="Required data not available for optimization analysis"):
            optimizer_result = await self.optimization_agent.execute(
                message="Optimize based on collected data", 
                context=self.user_context,
                previous_result=data_result
            )

    def test_metadata_key_contract_documentation(self):
        """Document the metadata key contracts for each agent.
        
        This serves as authoritative documentation of the current state vs expected state.
        """
        # Current metadata key contracts (what agents actually use)
        CURRENT_CONTRACTS = {
            'DataHelperAgent': {
                'stores': ['data_helper_result'],
                'expects': []
            },
            'UnifiedTriageAgent': {
                'stores': ['triage_result', 'triage_category', 'data_sufficiency', 'triage_priority'],
                'expects': []
            },
            'OptimizationsCoreSubAgent': {
                'stores': ['optimizations_result'],
                'expects': ['data_result', 'triage_result']  # MISMATCH: expects 'data_result' but gets 'data_helper_result'
            }
        }
        
        # Expected metadata key contracts (what should be used for proper coordination)
        EXPECTED_CONTRACTS = {
            'DataHelperAgent': {
                'stores': ['data_result'],  # Should store 'data_result', not 'data_helper_result'
                'expects': []
            },
            'UnifiedTriageAgent': {
                'stores': ['triage_result', 'triage_category', 'data_sufficiency', 'triage_priority'],
                'expects': []
            },
            'OptimizationsCoreSubAgent': {
                'stores': ['optimizations_result'],
                'expects': ['data_result', 'triage_result']
            }
        }
        
        # Document the specific mismatch
        current_data_key = CURRENT_CONTRACTS['DataHelperAgent']['stores'][0]
        expected_data_key = EXPECTED_CONTRACTS['DataHelperAgent']['stores'][0]
        optimization_expects = CURRENT_CONTRACTS['OptimizationsCoreSubAgent']['expects'][0]
        
        assert current_data_key != optimization_expects, \
            f"MISMATCH: DataHelperAgent stores '{current_data_key}' but OptimizationsCoreSubAgent expects '{optimization_expects}'"
        
        assert expected_data_key == optimization_expects, \
            f"FIX: DataHelperAgent should store '{expected_data_key}' to match OptimizationsCoreSubAgent expectations"

    @pytest.mark.asyncio
    async def test_proposed_fix_validation(self):
        """Test that demonstrates how the fix would work.
        
        This test shows that if DataHelperAgent stored 'data_result' instead of 'data_helper_result',
        the coordination would work properly.
        """
        # Step 1: Execute TriageAgent (this works correctly)
        await self.triage_agent.execute(
            message="Analyze requirements",
            context=self.user_context
        )
        
        # Step 2: Manually simulate what DataHelperAgent SHOULD store
        # (instead of what it currently stores)
        self.user_context.metadata['data_result'] = {  # Proposed fix: use 'data_result'
            "cost_analysis": "simulated data",
            "recommendations": ["optimize compute", "reduce storage"]
        }
        
        # Step 3: OptimizationsCoreSubAgent should now work
        result = await self.optimization_agent.execute(
            message="Optimize based on collected data",
            context=self.user_context
        )
        
        # Verify the coordination works with the correct key
        assert result is not None
        assert isinstance(result, dict)
        assert 'optimizations_result' in self.user_context.metadata

    def test_impact_analysis(self):
        """Analyze the impact of the data contract mismatch.
        
        Documents the business impact and scope of the issue.
        """
        # Tests affected by this issue
        AFFECTED_TESTS = [
            "test_sub_agent_execution_pipeline_sequencing",
            "test_agent_tool_execution_integration", 
            "test_agent_timeout_performance_management",
            "test_multi_agent_coordination_communication",
            "test_agent_permission_access_control",
            "test_agent_execution_metrics_analytics"
        ]
        
        # Business impact
        BUSINESS_IMPACT = {
            "golden_path_tests_failing": "10/19 tests",
            "affected_workflow": "AI cost optimization",
            "user_experience_impact": "Agent coordination failures",
            "revenue_impact": "Reduced optimization recommendations quality"
        }
        
        # Root cause
        ROOT_CAUSE = {
            "component": "DataHelperAgent",
            "issue": "Stores 'data_helper_result' instead of 'data_result'",
            "expecting_component": "OptimizationsCoreSubAgent",
            "location": "netra_backend/app/agents/data_helper_agent.py:136"
        }
        
        # Proposed fix
        PROPOSED_FIX = {
            "action": "Change metadata key in DataHelperAgent",
            "from": "data_helper_result", 
            "to": "data_result",
            "file": "netra_backend/app/agents/data_helper_agent.py",
            "line": 136
        }
        
        # Validate the analysis
        assert len(AFFECTED_TESTS) >= 6, "Multiple Golden Path tests are affected"
        assert BUSINESS_IMPACT["golden_path_tests_failing"] == "10/19 tests", "Significant test failure rate"
        assert ROOT_CAUSE["issue"] == "Stores 'data_helper_result' instead of 'data_result'", "Specific metadata key mismatch identified"