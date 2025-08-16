"""
Parameterized Example Prompts E2E Tests with Real LLM Calls
Replaces 90 individual test methods with parameterized testing
"""

import pytest
import pytest_asyncio
from typing import Dict, Any

from app.tests.agents.test_example_prompts_base import (
    EXAMPLE_PROMPTS, 
    setup_real_infrastructure,
    ExamplePromptsTestBase
)
from app.tests.agents.test_example_prompts_contexts import ContextGenerator
from app.tests.agents.test_example_prompts_runner import TestRunner
from app.services.quality_gate_service import ContentType


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
    
    @pytest.fixture
    def setup_real_infrastructure(self):
        """Setup infrastructure for testing"""
        return setup_real_infrastructure()
    
    @pytest.mark.parametrize("prompt_index", range(9))
    @pytest.mark.parametrize("variation_num", range(10))
    async def test_prompt_variations(
        self, 
        prompt_index: int, 
        variation_num: int,
        setup_real_infrastructure
    ):
        """
        Test each prompt with 10 variations.
        This single parameterized test replaces 90 individual test methods.
        
        Args:
            prompt_index: Index of the prompt (0-8)
            variation_num: Variation number (0-9)
            setup_real_infrastructure: Fixture providing test infrastructure
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
            infra=setup_real_infrastructure
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
        setup_real_infrastructure
    ):
        """Test that each prompt gets the correct context type"""
        context_type = PROMPT_CONTEXT_MAPPING.get(prompt_index)
        assert context_type == expected_type, f"Wrong context type for prompt {prompt_index}"
        
        # Verify context generation works
        context = self.context_generator.generate_synthetic_context(context_type)
        assert context, "Context should not be empty"
        assert isinstance(context, dict), "Context should be a dictionary"
    
    @pytest.mark.slow
    async def test_all_prompts_summary(self, setup_real_infrastructure):
        """Run a summary test of all prompts with basic validation"""
        results = []
        
        for prompt_index, prompt in enumerate(EXAMPLE_PROMPTS):
            context_type = PROMPT_CONTEXT_MAPPING.get(prompt_index, "default")
            context = self.context_generator.generate_synthetic_context(context_type)
            
            # Run with variation 0 (original prompt)
            result = await self.test_runner.run_single_test(
                prompt=prompt,
                context=context,
                infra=setup_real_infrastructure
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
    
    @pytest.fixture
    def setup_real_infrastructure(self):
        """Setup infrastructure for testing"""
        return setup_real_infrastructure()
    
    @pytest.mark.parametrize("prompt_index", [0, 6])  # Cost-related prompts
    async def test_cost_optimization_prompts(
        self, 
        prompt_index: int,
        setup_real_infrastructure
    ):
        """Test prompts related to cost optimization"""
        prompt = EXAMPLE_PROMPTS[prompt_index]
        context = self.context_generator.generate_synthetic_context("cost_reduction")
        
        result = await self.test_runner.run_single_test(
            prompt=prompt,
            context=context,
            infra=setup_real_infrastructure
        )
        
        assert result["success"]
        assert "cost" in result["response"].lower() or "budget" in result["response"].lower()
    
    @pytest.mark.parametrize("prompt_index", [1, 3])  # Performance-related prompts
    async def test_performance_optimization_prompts(
        self, 
        prompt_index: int,
        setup_real_infrastructure
    ):
        """Test prompts related to performance optimization"""
        prompt = EXAMPLE_PROMPTS[prompt_index]
        context = self.context_generator.generate_synthetic_context("latency_optimization")
        
        result = await self.test_runner.run_single_test(
            prompt=prompt,
            context=context,
            infra=setup_real_infrastructure
        )
        
        assert result["success"]
        assert any(word in result["response"].lower() 
                  for word in ["latency", "performance", "speed", "optimization"])