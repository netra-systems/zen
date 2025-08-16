"""
Advanced Features Tests - Prompts 6, 7, 8, and 9 with all variations
Tests audit, multi-objective optimization, tool migration, and rollback analysis prompts
"""

import pytest
from .test_base import BaseExamplePromptsTest
from .conftest import EXAMPLE_PROMPTS


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestAuditPrompts(BaseExamplePromptsTest):
    """Test class for audit prompts (Prompt 6)"""
    async def test_prompt_6_variation_0(self, setup_real_infrastructure):
        """Test audit - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_1(self, setup_real_infrastructure):
        """Test audit - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_2(self, setup_real_infrastructure):
        """Test audit - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_3(self, setup_real_infrastructure):
        """Test audit - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_4(self, setup_real_infrastructure):
        """Test audit - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_5(self, setup_real_infrastructure):
        """Test audit - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_6(self, setup_real_infrastructure):
        """Test audit - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_7(self, setup_real_infrastructure):
        """Test audit - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_8(self, setup_real_infrastructure):
        """Test audit - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_6_variation_9(self, setup_real_infrastructure):
        """Test audit - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestMultiObjectiveOptimization(BaseExamplePromptsTest):
    """Test class for multi-objective optimization prompts (Prompt 7)"""
    async def test_prompt_7_variation_0(self, setup_real_infrastructure):
        """Test multi-objective - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_1(self, setup_real_infrastructure):
        """Test multi-objective - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_2(self, setup_real_infrastructure):
        """Test multi-objective - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_3(self, setup_real_infrastructure):
        """Test multi-objective - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_4(self, setup_real_infrastructure):
        """Test multi-objective - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_5(self, setup_real_infrastructure):
        """Test multi-objective - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_6(self, setup_real_infrastructure):
        """Test multi-objective - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_7(self, setup_real_infrastructure):
        """Test multi-objective - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_8(self, setup_real_infrastructure):
        """Test multi-objective - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_7_variation_9(self, setup_real_infrastructure):
        """Test multi-objective - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestToolMigration(BaseExamplePromptsTest):
    """Test class for tool migration prompts (Prompt 8)"""
    async def test_prompt_8_variation_0(self, setup_real_infrastructure):
        """Test tool migration - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_1(self, setup_real_infrastructure):
        """Test tool migration - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_2(self, setup_real_infrastructure):
        """Test tool migration - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_3(self, setup_real_infrastructure):
        """Test tool migration - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_4(self, setup_real_infrastructure):
        """Test tool migration - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_5(self, setup_real_infrastructure):
        """Test tool migration - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_6(self, setup_real_infrastructure):
        """Test tool migration - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_7(self, setup_real_infrastructure):
        """Test tool migration - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_8(self, setup_real_infrastructure):
        """Test tool migration - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_8_variation_9(self, setup_real_infrastructure):
        """Test tool migration - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"


@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
class TestRollbackAnalysis(BaseExamplePromptsTest):
    """Test class for rollback analysis prompts (Prompt 9)"""
    async def test_prompt_9_variation_0(self, setup_real_infrastructure):
        """Test rollback analysis - original prompt"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_1(self, setup_real_infrastructure):
        """Test rollback analysis - with budget"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_2(self, setup_real_infrastructure):
        """Test rollback analysis - urgent"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_3(self, setup_real_infrastructure):
        """Test rollback analysis - with GPU info"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_4(self, setup_real_infrastructure):
        """Test rollback analysis - team perspective"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_5(self, setup_real_infrastructure):
        """Test rollback analysis - with region"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_6(self, setup_real_infrastructure):
        """Test rollback analysis - with error constraint"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_7(self, setup_real_infrastructure):
        """Test rollback analysis - caps"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_8(self, setup_real_infrastructure):
        """Test rollback analysis - follow-up"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"
    async def test_prompt_9_variation_9(self, setup_real_infrastructure):
        """Test rollback analysis - GPU count"""
        infra = setup_real_infrastructure
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result.success, f"Test failed: {result.error}"
        assert result.quality_passed, "Response quality check failed"