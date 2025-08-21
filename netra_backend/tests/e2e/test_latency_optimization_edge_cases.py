"""
Latency Optimization Edge Cases and Integration Tests
Tests edge cases and integration scenarios for latency optimization workflows.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import pytest

# Add project root to path
from netra_backend.tests.e2e.latency_optimization_helpers import (
    create_3x_latency_state,
    create_already_optimized_state,
    create_caching_optimization_state,
    create_impossible_latency_state,
    # Add project root to path
    create_latency_optimization_setup,
    execute_latency_workflow,
    validate_agent_data_flow,
    validate_impossible_target_handling,
    validate_optimized_system_handling,
    validate_state_consistency,
)


@pytest.fixture
def latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):
    """Setup real agent environment for latency optimization testing."""
    return create_latency_optimization_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher)


class TestLatencyOptimizationEdgeCases:
    """Test edge cases in latency optimization workflows."""
    
    async def test_impossible_latency_targets(self, latency_optimization_setup):
        """Test handling of impossible latency targets."""
        setup = latency_optimization_setup
        state = create_impossible_latency_state()
        results = await execute_latency_workflow(setup, state)
        validate_impossible_target_handling(results)
    
    async def test_already_optimized_system(self, latency_optimization_setup):
        """Test handling of already well-optimized systems."""
        setup = latency_optimization_setup
        state = create_already_optimized_state()
        results = await execute_latency_workflow(setup, state)
        validate_optimized_system_handling(results)


class TestIntegrationValidation:
    """Test integration between latency optimization agents."""
    
    async def test_data_flow_between_agents(self, latency_optimization_setup):
        """Test proper data flow between optimization agents."""
        setup = latency_optimization_setup
        state = create_3x_latency_state()
        results = await execute_latency_workflow(setup, state)
        validate_agent_data_flow(results, state)
    
    async def test_state_consistency_maintenance(self, latency_optimization_setup):
        """Test state consistency throughout workflow."""
        setup = latency_optimization_setup
        state = create_caching_optimization_state()
        results = await execute_latency_workflow(setup, state)
        validate_state_consistency(results, state)