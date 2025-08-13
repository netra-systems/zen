"""
Tests for main synthetic data generation workflow and worker
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.synthetic_data_service import (
    SyntheticDataService,
    GenerationStatus
)
from app.tests.services.synthetic_data.test_data_operations import MockSession


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return MockSession()


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


@pytest.mark.asyncio
class TestMainGenerationWorkflow:
    """Test main generation workflow"""
    
    @patch('app.services.synthetic_data_service.manager')
    @patch('app.db.models_postgres.Corpus')
    async def test_generate_synthetic_data(self, mock_corpus_model, mock_manager, service, mock_db, sample_config):
        """Test main synthetic data generation workflow"""
        user_id = "test-user"
        mock_corpus_instance = MagicMock()
        mock_corpus_instance.id = "corpus-id"
        mock_corpus_model.return_value = mock_corpus_instance
        
        result = await service.generate_synthetic_data(mock_db, sample_config, user_id)
        
        assert "job_id" in result
        assert result["status"] == GenerationStatus.INITIATED.value
        assert "table_name" in result
        assert "websocket_channel" in result
        
        # Verify job was added to active jobs
        job_id = result["job_id"]
        assert job_id in service.active_jobs
        
        job = service.active_jobs[job_id]
        assert job["status"] == GenerationStatus.INITIATED.value
        assert job["config"] == sample_config
        assert job["user_id"] == user_id
    
    async def test_generate_synthetic_data_with_corpus(self, service, mock_db, sample_config):
        """Test generation with specific corpus"""
        user_id = "test-user"
        corpus_id = "test-corpus"
        
        with patch('app.db.models_postgres.Corpus') as mock_corpus:
            mock_instance = MagicMock()
            mock_instance.id = "corpus-id"
            mock_corpus.return_value = mock_instance
            
            result = await service.generate_synthetic_data(mock_db, sample_config, user_id, corpus_id)
            
            assert "job_id" in result
            job = service.active_jobs[result["job_id"]]
            assert job["corpus_id"] == corpus_id


@pytest.mark.asyncio
class TestGenerationWorker:
    """Test the background generation worker"""
    
    @patch('app.services.synthetic_data_service.manager')
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_generate_worker_success(self, mock_get_client, mock_manager, service, mock_db, sample_config):
        """Test successful generation worker execution"""
        job_id = "test-job"
        synthetic_data_id = "synth-id"
        sample_config.num_logs = 2
        
        # Setup mocks
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        # Initialize job
        service.active_jobs[job_id] = {
            "status": GenerationStatus.INITIATED.value,
            "config": sample_config,
            "corpus_id": None,
            "start_time": datetime.now(UTC),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": "test_table",
            "user_id": "test-user"
        }
        
        # Run worker
        await service._generate_worker(job_id, sample_config, None, mock_db, synthetic_data_id)
        
        # Verify job completion
        assert service.active_jobs[job_id]["status"] == GenerationStatus.COMPLETED.value
        assert service.active_jobs[job_id]["records_generated"] == 2
        assert "end_time" in service.active_jobs[job_id]
    
    @patch('app.services.synthetic_data_service.manager')
    async def test_generate_worker_failure(self, mock_manager, service, mock_db, sample_config):
        """Test generation worker with failure"""
        job_id = "test-job"
        synthetic_data_id = "synth-id"
        
        # Initialize job
        service.active_jobs[job_id] = {
            "status": GenerationStatus.INITIATED.value,
            "config": sample_config,
            "corpus_id": None,
            "start_time": datetime.now(UTC),
            "records_generated": 0,
            "records_ingested": 0,
            "errors": [],
            "table_name": "test_table",
            "user_id": "test-user"
        }
        
        # Make table creation fail
        with patch.object(service, '_create_destination_table', side_effect=Exception("Table error")):
            await service._generate_worker(job_id, sample_config, None, mock_db, synthetic_data_id)
        
        # Verify job failure
        assert service.active_jobs[job_id]["status"] == GenerationStatus.FAILED.value
        assert len(service.active_jobs[job_id]["errors"]) > 0