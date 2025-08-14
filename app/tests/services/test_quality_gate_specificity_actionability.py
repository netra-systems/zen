"""Tests for Quality Gate Service specificity and actionability calculations"""

import pytest
from app.services.quality_gate_service import (
    QualityGateService,
    ContentType
)
from app.tests.helpers.quality_gate_comprehensive_helpers import (
    setup_specificity_test_content,
    setup_actionability_test_content,
    setup_code_block_content
)


class TestSpecificityCalculationEdgeCases:
    """Test edge cases in specificity calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    @pytest.mark.asyncio
    async def test_specificity_with_all_indicators(self, quality_service):
        """Test specificity with all positive indicators"""
        content = setup_specificity_test_content()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_specificity(
            content,
            ContentType.OPTIMIZATION
        )
        
        assert score > 0.8  # Should be very high
        
    @pytest.mark.asyncio
    async def test_specificity_with_vague_language_penalty(self, quality_service):
        """Test specificity penalty for vague language"""
        content = "You might want to consider optimizing your model perhaps."
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_specificity(
            content,
            ContentType.OPTIMIZATION
        )
        
        assert score < 0.2  # Should be penalized for vagueness


class TestActionabilityEdgeCases:
    """Test edge cases in actionability calculation"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
        
    def _validate_actionability_with_paths(self, content, quality_service):
        """Helper to validate actionability with file paths"""
        return quality_service.metrics_calculator.core_calculator.calculate_actionability(
            content,
            ContentType.ACTION_PLAN
        )
        
    @pytest.mark.asyncio
    async def test_actionability_with_file_paths(self, quality_service):
        """Test actionability with file paths and URLs"""
        content = setup_actionability_test_content()
        
        score = await self._validate_actionability_with_paths(content, quality_service)
        
        assert score > 0.5  # Should recognize paths and URLs
        
    def _validate_actionability_with_code(self, content, quality_service):
        """Helper to validate actionability with code blocks"""
        return quality_service.metrics_calculator.core_calculator.calculate_actionability(
            content,
            ContentType.ACTION_PLAN
        )
        
    @pytest.mark.asyncio
    async def test_actionability_code_blocks(self, quality_service):
        """Test actionability with code blocks"""
        content = setup_code_block_content()
        
        score = await self._validate_actionability_with_code(content, quality_service)
        
        assert score > 0.6  # Should recognize code