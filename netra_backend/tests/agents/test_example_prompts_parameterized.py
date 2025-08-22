"""
Parameterized Example Prompts E2E Tests with Real LLM Calls
Replaces 90 individual test methods with parameterized testing
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
from typing import Any, Dict

import pytest
import pytest_asyncio

from netra_backend.app.services.quality_gate_service import ContentType

# Add project root to path
from .test_example_prompts_base import (
    # Add project root to path
    EXAMPLE_PROMPTS,
    ExamplePromptsTestBase,
    setup_real_infrastructure,
)
from .test_example_prompts_contexts import ContextGenerator
from .test_example_prompts_runner import TestRunner


@pytest_asyncio.fixture
async def real_infrastructure():
    """Module-level async fixture for real infrastructure setup"""
    infrastructure = setup_real_infrastructure()
    yield infrastructure
    # Cleanup async resources to prevent pending task warnings
    await _cleanup_infrastructure_global(infrastructure)


async def _cleanup_infrastructure_global(infrastructure: Dict[str, Any]) -> None:
    """Global cleanup function for infrastructure"""
    try:
        # Shutdown WebSocket manager and its async components
        websocket_manager = infrastructure.get("websocket_manager")
        if websocket_manager:
            await websocket_manager.shutdown()
        
        # Close mock database session
        db_session = infrastructure.get("db_session")
        if db_session and hasattr(db_session, 'close'):
            await db_session.close()
        
        # Cancel any remaining async tasks
        await _cancel_pending_tasks_global()
        
    except Exception as e:
        # Log cleanup errors but don't fail the test
        print(f"Warning: Error during infrastructure cleanup: {e}")


async def _cancel_pending_tasks_global() -> None:
    """Global function to cancel any remaining pending tasks"""
    try:
        # Get all pending tasks in the current event loop
        pending_tasks = [task for task in asyncio.all_tasks() 
                        if not task.done() and task != asyncio.current_task()]
        
        if pending_tasks:
            # Cancel all pending tasks
            for task in pending_tasks:
                task.cancel()
            
            # Wait briefly for cancellations to complete
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            
    except Exception:
        # Silently handle any cancellation errors
        pass


# Map prompts to their context types
PROMPT_CONTEXT_MAPPING = {
    0: "cost_reduction",      # Cost reduction prompt
    1: "latency_optimization", # Latency optimization prompt
    2: "capacity_planning",    # Capacity planning prompt
    3: "function_optimization", # Function optimization prompt
    4: "model_evaluation",     # Model evaluation prompt
    5: "audit",               # Audit prompt
    6: "multi_objective",     # Multi-objective optimization
    7: "tool_migration",      # Tool migration prompt
    8: "rollback_analysis",   # Rollback analysis prompt
}


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestExamplePromptsParameterized(ExamplePromptsTestBase):
    """
    Parameterized test class for example prompts with real LLM calls.
    Uses pytest.mark.parametrize to generate all 90 test combinations.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test dependencies"""
        self.context_generator = ContextGenerator()
        self.test_runner = TestRunner()
    
    @pytest.mark.parametrize("prompt_index", range(9))
    @pytest.mark.parametrize("variation_num", range(10))
    async def test_prompt_variations(
        self, 
        prompt_index: int, 
        variation_num: int,
        real_infrastructure
    ):
        """
        Test each prompt with 10 variations.
        This single parameterized test replaces 90 individual test methods.
        
        Args:
            prompt_index: Index of the prompt (0-8)
            variation_num: Variation number (0-9)
            real_infrastructure: Fixture providing test infrastructure
        """
        # Get the base prompt
        base_prompt = EXAMPLE_PROMPTS[prompt_index]
        
        # Get the appropriate context type
        context_type = PROMPT_CONTEXT_MAPPING.get(prompt_index, "default")
        
        # Generate synthetic context
        context = self.context_generator.generate_synthetic_context(context_type)
        context["prompt_type"] = context_type
        context["prompt_index"] = prompt_index
        context["variation_num"] = variation_num
        
        # Create prompt variation
        test_prompt = self.create_prompt_variation(base_prompt, variation_num, context)
        
        # Run the test
        result = await self.test_runner.run_single_test(
            prompt=test_prompt,
            context=context,
            infra=real_infrastructure
        )
        
        # Assertions
        assert result["success"], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result["response"], "Response should not be empty"
        assert len(result["response"]) >= 50, "Response too short"
        
        # Validate response quality
        validation = result.get("validation", {})
        assert validation.get("valid", False), f"Quality validation failed: {validation.get('feedback', [])}"
        assert validation.get("score", 0) >= 70, f"Quality score too low: {validation.get('score', 0)}"
        
        # Check metrics
        metrics = result.get("metrics", {})
        if metrics.get("execution_time"):
            assert metrics["execution_time"] < 30, "Execution took too long"
    
    @pytest.mark.parametrize("prompt_index,expected_type", [
        (0, "cost_reduction"),
        (1, "latency_optimization"),
        (2, "capacity_planning"),
        (3, "function_optimization"),
        (4, "model_evaluation"),
        (5, "audit"),
        (6, "multi_objective"),
        (7, "tool_migration"),
        (8, "rollback_analysis"),
    ])
    async def test_prompt_context_mapping(
        self, 
        prompt_index: int, 
        expected_type: str,
        real_infrastructure
    ):
        """Test that each prompt gets the correct context type"""
        context_type = PROMPT_CONTEXT_MAPPING.get(prompt_index)
        assert context_type == expected_type, f"Wrong context type for prompt {prompt_index}"
        
        # Verify context generation works
        context = self.context_generator.generate_synthetic_context(context_type)
        assert context, "Context should not be empty"
        assert isinstance(context, dict), "Context should be a dictionary"
    
    @pytest.mark.slow
    async def test_all_prompts_summary(self, real_infrastructure):
        """Run a summary test of all prompts with basic validation"""
        results = []
        
        for prompt_index, prompt in enumerate(EXAMPLE_PROMPTS):
            context_type = PROMPT_CONTEXT_MAPPING.get(prompt_index, "default")
            context = self.context_generator.generate_synthetic_context(context_type)
            
            # Run with variation 0 (original prompt)
            result = await self.test_runner.run_single_test(
                prompt=prompt,
                context=context,
                infra=real_infrastructure
            )
            results.append(result)
        
        # Analyze aggregate results
        analysis = self.test_runner.analyze_test_results(results)
        
        # Summary assertions
        assert analysis["success_rate"] >= 0.8, f"Success rate too low: {analysis['success_rate']}"
        assert analysis["average_quality_score"] >= 70, f"Average quality too low: {analysis['average_quality_score']}"
        
        # Print summary for debugging
        print(f"\nTest Summary:")
        print(f"  Total tests: {analysis['total_tests']}")
        print(f"  Successful: {analysis['successful_tests']}")
        print(f"  Success rate: {analysis['success_rate']:.2%}")
        print(f"  Avg quality: {analysis['average_quality_score']:.1f}")
        
        if analysis["failed_tests"]:
            print(f"  Failed tests: {analysis['failed_tests']}")


# Additional focused test groups for specific scenarios
@pytest.mark.real_llm
class TestPromptGroups(ExamplePromptsTestBase):
    """Test prompts grouped by functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test dependencies"""
        self.context_generator = ContextGenerator()
        self.test_runner = TestRunner()
    
    @pytest.mark.parametrize("prompt_index", [0, 6])  # Cost-related prompts
    async def test_cost_optimization_prompts(
        self, 
        prompt_index: int,
        real_infrastructure
    ):
        """Test prompts related to cost optimization"""
        prompt = EXAMPLE_PROMPTS[prompt_index]
        context = self.context_generator.generate_synthetic_context("cost_reduction")
        
        result = await self.test_runner.run_single_test(
            prompt=prompt,
            context=context,
            infra=real_infrastructure
        )
        
        assert result["success"]
        assert "cost" in result["response"].lower() or "budget" in result["response"].lower()
    
    @pytest.mark.parametrize("prompt_index", [1, 3])  # Performance-related prompts
    async def test_performance_optimization_prompts(
        self, 
        prompt_index: int,
        real_infrastructure
    ):
        """Test prompts related to performance optimization"""
        prompt = EXAMPLE_PROMPTS[prompt_index]
        context = self.context_generator.generate_synthetic_context("latency_optimization")
        
        result = await self.test_runner.run_single_test(
            prompt=prompt,
            context=context,
            infra=real_infrastructure
        )
        
        assert result["success"]
        assert any(word in result["response"].lower() 
                  for word in ["latency", "performance", "speed", "optimization"])