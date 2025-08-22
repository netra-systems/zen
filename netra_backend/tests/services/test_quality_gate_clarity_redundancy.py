"""Tests for Quality Gate Service clarity and redundancy calculations"""

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
from netra_backend.app.services.quality_gate_service import QualityGateService
from .quality_gate_comprehensive_helpers import (
    create_excessive_acronyms_content,
    create_high_overlap_content,
    create_nested_parentheses_content,
    # Add project root to path
    create_very_long_sentence,
)


class TestClarityCalculation:
    """Test clarity calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_clarity_very_long_sentences(self, quality_service):
        """Test clarity with very long sentences"""
        long_sentence = create_very_long_sentence()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_clarity(long_sentence)
        assert score < 0.6  # Should be penalized for length
    async def test_clarity_excessive_acronyms(self, quality_service):
        """Test clarity with many unexplained acronyms"""
        content = create_excessive_acronyms_content()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_clarity(content)
        assert score < 0.95  # Should be slightly penalized
    async def test_clarity_nested_parentheses(self, quality_service):
        """Test clarity with nested parentheses"""
        content = create_nested_parentheses_content()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_clarity(content)
        assert score < 0.95  # Should be penalized
    async def test_clarity_no_sentences(self, quality_service):
        """Test clarity calculation with no proper sentences"""
        content = "optimization performance metrics"
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_clarity(content)
        assert score >= 0  # Should handle gracefully


class TestRedundancyCalculation:
    """Test redundancy calculation edge cases"""
    
    @pytest.fixture
    def quality_service(self):
        return QualityGateService(redis_manager=None)
    async def test_redundancy_single_sentence(self, quality_service):
        """Test redundancy with single sentence"""
        content = "This is a single sentence."
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_redundancy(content)
        assert score == 0.0  # No redundancy possible
    async def test_redundancy_empty_sentences(self, quality_service):
        """Test redundancy with empty sentence splits"""
        content = "First. . . Last."
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_redundancy(content)
        assert score >= 0  # Should handle empty splits
    async def test_redundancy_high_overlap(self, quality_service):
        """Test redundancy with high word overlap"""
        content = create_high_overlap_content()
        
        score = await quality_service.metrics_calculator.core_calculator.calculate_redundancy(content)
        assert score > 0.4  # Should detect high redundancy