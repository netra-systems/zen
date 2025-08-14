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
    
    def test_calculate_metrics_empty(self, service):
        """Test metrics calculation with empty invocations"""
        metrics = service._calculate_metrics([])
        
        assert metrics["total_latency_ms"] == 0
        assert metrics["tool_count"] == 0
        assert metrics["success_rate"] == 1.0
    
    def test_calculate_metrics_with_data(self, service):
        """Test metrics calculation with tool invocations"""
        invocations = [
            {"latency_ms": 100, "status": "success"},
            {"latency_ms": 200, "status": "success"},
            {"latency_ms": 150, "status": "failed"}
        ]
        
        metrics = service._calculate_metrics(invocations)
        
        assert metrics["total_latency_ms"] == 450
        assert metrics["tool_count"] == 3
        assert metrics["success_rate"] == 2/3
        assert metrics["avg_latency_ms"] == 150


class TestGenerationRateCalculation:
    """Test generation rate calculation"""
    
    def test_calculate_generation_rate_no_job(self, service):
        """Test generation rate for non-existent job"""
        rate = service._calculate_generation_rate("non-existent")
        assert rate == 0.0
    
    def test_calculate_generation_rate_zero_elapsed(self, service):
        """Test generation rate with zero elapsed time"""
        job_id = "test-job"
        service.active_jobs[job_id] = {
            "start_time": datetime.now(UTC),
            "records_generated": 100
        }
        
        rate = service._calculate_generation_rate(job_id)
        assert rate == 0.0  # Division by zero handled
    
    def test_calculate_generation_rate_with_time(self, service):
        """Test generation rate calculation with elapsed time"""
        job_id = "test-job"
        start_time = datetime.now(UTC) - timedelta(seconds=10)
        service.active_jobs[job_id] = {
            "start_time": start_time,
            "records_generated": 100
        }
        
        rate = service._calculate_generation_rate(job_id)
        assert rate > 0
        assert rate == pytest.approx(10, rel=0.1)  # ~10 records/second