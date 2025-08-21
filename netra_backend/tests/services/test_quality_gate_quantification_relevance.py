"""Tests for Quality Gate Service quantification and relevance calculations"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest

# Add project root to path

from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.tests.helpers.quality_gate_comprehensive_helpers import (

# Add project root to path
    setup_quantification_patterns_content,
    setup_relevance_test_context
)


class TestQuantificationPatterns:
    """Test quantification pattern matching"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_quantification_all_patterns(self, quality_service):
        """Test all quantification patterns"""
        content = setup_quantification_patterns_content()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_quantification(content)
        assert score > 0.9  # Should match all patterns
    async def test_quantification_before_after(self, quality_service):
        """Test before/after comparison bonus"""
        content = "Latency improved from 500ms before optimization to 150ms after."
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_quantification(content)
        assert score > 0.3  # Should get bonus for before/after
    async def test_quantification_metric_names(self, quality_service):
        """Test metric names with values bonus"""
        content = "Achieved throughput of 5000 QPS with latency under 50ms and precision at 0.95."
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_quantification(content)
        assert score > 0.4  # Should get bonus for named metrics


class TestRelevanceCalculation:
    """Test relevance calculation with various contexts"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_relevance_technical_terms_matching(self, quality_service):
        """Test relevance with technical term matching"""
        content = "Implement distributed training across multiple GPUs for faster convergence."
        context = setup_relevance_test_context()
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_relevance(content, context)
        assert score > 0.5  # Should match technical concepts
    async def test_relevance_empty_request_words(self, quality_service):
        """Test relevance when request has no words"""
        content = "Optimization strategy"
        context = {"user_request": ""}
        
        score = await quality_service.metrics_calculator.specialized_calculator.calculate_relevance(content, context)
        assert score >= 0  # Should handle empty request gracefully