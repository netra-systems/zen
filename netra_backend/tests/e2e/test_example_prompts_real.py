import asyncio

"""
Comprehensive Example Prompts E2E Real LLM Testing Suite
Tests all 9 example prompts with real LLM calls and complete validation.
Maximum 300 lines, functions <=8 lines.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.tests.e2e.example_prompts_core import (
EXAMPLE_PROMPTS,
create_ep_001_state,
create_ep_002_state,
create_ep_003_state,
create_ep_004_state,
create_ep_005_state,
create_ep_006_state,
create_ep_007_state,
create_ep_008_state,
create_ep_009_state,
execute_full_prompt_workflow,
real_llm_prompt_setup,
)
from netra_backend.tests.e2e.example_prompts_validators import (
validate_capacity_planning_result,
validate_cost_optimization_result,
validate_function_optimization_result,
validate_kv_cache_audit_result,
validate_model_selection_result,
validate_multi_constraint_result,
validate_performance_optimization_result,
validate_rollback_analysis_result,
validate_tool_migration_result,
)

@pytest.mark.real_llm
class TestExamplePromptsComprehensive:
    """Test all 9 example prompts with real LLM calls and complete validation."""

    @pytest.mark.asyncio
    async def test_ep_001_cost_quality_optimization(self, real_llm_prompt_setup):
        """Test EP-1: Cost reduction with quality preservation constraints."""
        setup = real_llm_prompt_setup
        state = create_ep_001_state()
        result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[0], state)
        validate_cost_optimization_result(result, setup)

        @pytest.mark.asyncio
        async def test_ep_002_latency_budget_constraint(self, real_llm_prompt_setup):
            """Test EP-2: Latency optimization with budget constraints."""
            setup = real_llm_prompt_setup
            state = create_ep_002_state()
            result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[1], state)
            validate_performance_optimization_result(result, setup)

            @pytest.mark.asyncio
            async def test_ep_003_capacity_planning_analysis(self, real_llm_prompt_setup):
                """Test EP-3: Capacity planning for usage increase."""
                setup = real_llm_prompt_setup
                state = create_ep_003_state()
                result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[2], state)
                validate_capacity_planning_result(result, setup)

                @pytest.mark.asyncio
                async def test_ep_004_function_optimization(self, real_llm_prompt_setup):
                    """Test EP-4: Advanced function optimization methods."""
                    setup = real_llm_prompt_setup
                    state = create_ep_004_state()
                    result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[3], state)
                    validate_function_optimization_result(result, setup)

                    @pytest.mark.asyncio
                    async def test_ep_005_model_selection_evaluation(self, real_llm_prompt_setup):
                        """Test EP-5: Model selection and effectiveness analysis."""
                        setup = real_llm_prompt_setup
                        state = create_ep_005_state()
                        result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[4], state)
                        validate_model_selection_result(result, setup)

                        @pytest.mark.asyncio
                        async def test_ep_006_kv_cache_audit(self, real_llm_prompt_setup):
                            """Test EP-6: KV cache audit and optimization opportunities."""
                            setup = real_llm_prompt_setup
                            state = create_ep_006_state()
                            result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[5], state)
                            validate_kv_cache_audit_result(result, setup)

                            @pytest.mark.asyncio
                            async def test_ep_007_multi_constraint_optimization(self, real_llm_prompt_setup):
                                """Test EP-7: Multi-constraint optimization with usage scaling."""
                                setup = real_llm_prompt_setup
                                state = create_ep_007_state()
                                result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[6], state)
                                validate_multi_constraint_result(result, setup)

                                @pytest.mark.asyncio
                                async def test_ep_008_tool_migration_analysis(self, real_llm_prompt_setup):
                                    """Test EP-8: Tool migration to new models analysis."""
                                    setup = real_llm_prompt_setup
                                    state = create_ep_008_state()
                                    result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[7], state)
                                    validate_tool_migration_result(result, setup)

                                    @pytest.mark.asyncio
                                    async def test_ep_009_rollback_cost_analysis(self, real_llm_prompt_setup):
                                        """Test EP-9: Rollback analysis and cost-effectiveness evaluation."""
                                        setup = real_llm_prompt_setup
                                        state = create_ep_009_state()
                                        result = await execute_full_prompt_workflow(setup, EXAMPLE_PROMPTS[8], state)
                                        validate_rollback_analysis_result(result, setup)