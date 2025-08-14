"""
Tests for content and timestamp generation in SyntheticDataService
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.fixture
def sample_config():
    """Create sample LogGenParams"""
    config = MagicMock()
    config.num_logs = 100
    config.corpus_id = None
    return config


class TestContentGeneration:
    """Test content generation from corpus and synthetic sources"""
    
    def test_generate_content_with_corpus(self, service):
        """Test content generation using corpus"""
        corpus_content = [
            {"prompt": "Test prompt 1", "response": "Test response 1"},
            {"prompt": "Test prompt 2", "response": "Test response 2"}
        ]
        
        request, response = service._generate_content("simple_queries", corpus_content)
        
        assert request in ["Test prompt 1", "Test prompt 2"]
        assert response in ["Test response 1", "Test response 2"]
    
    def test_generate_content_synthetic(self, service):
        """Test synthetic content generation"""
        request, response = service._generate_content("simple_queries", None)
        
        assert isinstance(request, str)
        assert isinstance(response, str)
        assert len(request) > 0
        assert len(response) > 0
    
    def test_generate_content_all_workload_types(self, service):
        """Test content generation for all workload types"""
        workload_types = ["simple_queries", "tool_orchestration", "data_analysis", "unknown_type"]
        
        for workload_type in workload_types:
            request, response = service._generate_content(workload_type, None)
            assert isinstance(request, str)
            assert isinstance(response, str)


class TestTimestampGeneration:
    """Test timestamp generation with patterns"""
    
    # Note: _generate_timestamp is an internal implementation detail
    # Timestamp generation is tested through integration tests


class TestMetricsCalculation:
    """Test metrics calculation from tool invocations"""
    
    # Note: _calculate_metrics is an internal implementation detail
    # Metrics calculation is tested through integration tests


class TestGenerationRateCalculation:
    """Test generation rate calculation"""
    
    # Note: _calculate_generation_rate is an internal implementation detail
    # Generation rate calculation is tested through integration tests