"""
Tests for job management and preview generation
"""

import pytest
from app.services.synthetic_data_service import (
    SyntheticDataService,
    GenerationStatus,
    synthetic_data_service
)


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.mark.asyncio
class TestJobManagement:
    """Test job status and management operations"""
    
    async def test_get_job_status_exists(self, service):
        """Test getting status of existing job"""
        job_id = "test-job"
        job_data = {"status": "running", "progress": 50}
        service.active_jobs[job_id] = job_data
        
        status = await service.get_job_status(job_id)
        assert status == job_data
    
    async def test_get_job_status_not_exists(self, service):
        """Test getting status of non-existent job"""
        status = await service.get_job_status("non-existent")
        assert status == None
    
    async def test_cancel_job_exists(self, service):
        """Test canceling existing job"""
        job_id = "test-job"
        service.active_jobs[job_id] = {"status": "running"}
        
        result = await service.cancel_job(job_id)
        assert result == True
        assert service.active_jobs[job_id]["status"] == GenerationStatus.CANCELLED.value
    
    async def test_cancel_job_not_exists(self, service):
        """Test canceling non-existent job"""
        result = await service.cancel_job("non-existent")
        assert result == False


@pytest.mark.asyncio
class TestPreviewGeneration:
    """Test preview generation functionality"""
    
    async def test_get_preview(self, service):
        """Test generating preview samples"""
        corpus_id = "test-corpus"
        workload_type = "simple_queries"
        
        samples = await service.get_preview(corpus_id, workload_type, 5)
        
        assert len(samples) == 5
        for sample in samples:
            assert "event_id" in sample
            assert "workload_type" in sample
    
    async def test_get_preview_no_corpus(self, service):
        """Test generating preview without corpus"""
        samples = await service.get_preview(None, "test_type", 3)
        
        assert len(samples) == 3


class TestSingletonInstance:
    """Test singleton instance functionality"""
    
    def test_singleton_instance_exists(self):
        """Test that singleton instance is accessible"""
        assert synthetic_data_service != None
        assert isinstance(synthetic_data_service, SyntheticDataService)
    
    def test_singleton_instance_consistency(self):
        """Test that singleton returns same instance"""
        from app.services.synthetic_data_service import synthetic_data_service as service1
        from app.services.synthetic_data_service import synthetic_data_service as service2
        
        assert service1 is service2