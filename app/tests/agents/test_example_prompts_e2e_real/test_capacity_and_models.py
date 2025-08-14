"""
Capacity Planning and Model Selection Tests - Prompts 3 and 5 with all variations
Tests capacity planning and model selection prompts
"""

import pytest
from .test_base import BaseExamplePromptsTest
from .conftest import EXAMPLE_PROMPTS


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestCapacityPlanning(BaseExamplePromptsTest):
    """Test class for capacity planning prompts (Prompt 3)"""

    @pytest.mark.asyncio
    async def test_prompt_3_variation_0(self, setup_real_infrastructure):
        """Test capacity planning - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_1(self, setup_real_infrastructure):
        """Test capacity planning - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_2(self, setup_real_infrastructure):
        """Test capacity planning - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_3(self, setup_real_infrastructure):
        """Test capacity planning - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_4(self, setup_real_infrastructure):
        """Test capacity planning - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_5(self, setup_real_infrastructure):
        """Test capacity planning - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_6(self, setup_real_infrastructure):
        """Test capacity planning - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_7(self, setup_real_infrastructure):
        """Test capacity planning - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_8(self, setup_real_infrastructure):
        """Test capacity planning - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_9(self, setup_real_infrastructure):
        """Test capacity planning - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestModelSelection(BaseExamplePromptsTest):
    """Test class for model selection prompts (Prompt 5)"""

    @pytest.mark.asyncio
    async def test_prompt_5_variation_0(self, setup_real_infrastructure):
        """Test model selection - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_1(self, setup_real_infrastructure):
        """Test model selection - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_2(self, setup_real_infrastructure):
        """Test model selection - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_3(self, setup_real_infrastructure):
        """Test model selection - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_4(self, setup_real_infrastructure):
        """Test model selection - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_5(self, setup_real_infrastructure):
        """Test model selection - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_6(self, setup_real_infrastructure):
        """Test model selection - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_7(self, setup_real_infrastructure):
        """Test model selection - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_8(self, setup_real_infrastructure):
        """Test model selection - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_9(self, setup_real_infrastructure):
        """Test model selection - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"