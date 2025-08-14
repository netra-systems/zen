"""
Cost Optimization Tests - Prompt 1 with all variations
Tests cost optimization prompts with different contexts and variations
"""

import pytest
from .test_base import BaseExamplePromptsTest
from .conftest import EXAMPLE_PROMPTS


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestCostOptimization(BaseExamplePromptsTest):
    """Test class for cost optimization prompts (Prompt 1)"""

    @pytest.mark.asyncio
    async def test_prompt_1_variation_0(self, setup_real_infrastructure):
        """Test cost optimization - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
        assert result.response_length > 100, "Response too short"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_1(self, setup_real_infrastructure):
        """Test cost optimization - with budget context"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_2(self, setup_real_infrastructure):
        """Test cost optimization - urgent request"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_3(self, setup_real_infrastructure):
        """Test cost optimization - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_4(self, setup_real_infrastructure):
        """Test cost optimization - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_5(self, setup_real_infrastructure):
        """Test cost optimization - with region context"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_6(self, setup_real_infrastructure):
        """Test cost optimization - with error rate constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_7(self, setup_real_infrastructure):
        """Test cost optimization - urgent caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_8(self, setup_real_infrastructure):
        """Test cost optimization - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_9(self, setup_real_infrastructure):
        """Test cost optimization - with GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"