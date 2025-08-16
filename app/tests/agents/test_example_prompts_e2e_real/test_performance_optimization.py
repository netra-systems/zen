"""
Performance Optimization Tests - Prompts 2 and 4 with all variations
Tests latency optimization and function optimization prompts
"""

import pytest
from .test_base import BaseExamplePromptsTest
from .conftest import EXAMPLE_PROMPTS


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestLatencyOptimization(BaseExamplePromptsTest):
    """Test class for latency optimization prompts (Prompt 2)"""
    async def test_prompt_2_variation_0(self, setup_real_infrastructure):
        """Test latency optimization - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_1(self, setup_real_infrastructure):
        """Test latency optimization - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_2(self, setup_real_infrastructure):
        """Test latency optimization - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_3(self, setup_real_infrastructure):
        """Test latency optimization - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_4(self, setup_real_infrastructure):
        """Test latency optimization - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_5(self, setup_real_infrastructure):
        """Test latency optimization - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_6(self, setup_real_infrastructure):
        """Test latency optimization - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_7(self, setup_real_infrastructure):
        """Test latency optimization - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_8(self, setup_real_infrastructure):
        """Test latency optimization - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_2_variation_9(self, setup_real_infrastructure):
        """Test latency optimization - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestFunctionOptimization(BaseExamplePromptsTest):
    """Test class for function optimization prompts (Prompt 4)"""
    async def test_prompt_4_variation_0(self, setup_real_infrastructure):
        """Test function optimization - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_1(self, setup_real_infrastructure):
        """Test function optimization - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_2(self, setup_real_infrastructure):
        """Test function optimization - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_3(self, setup_real_infrastructure):
        """Test function optimization - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_4(self, setup_real_infrastructure):
        """Test function optimization - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_5(self, setup_real_infrastructure):
        """Test function optimization - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_6(self, setup_real_infrastructure):
        """Test function optimization - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_7(self, setup_real_infrastructure):
        """Test function optimization - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_8(self, setup_real_infrastructure):
        """Test function optimization - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_4_variation_9(self, setup_real_infrastructure):
        """Test function optimization - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"