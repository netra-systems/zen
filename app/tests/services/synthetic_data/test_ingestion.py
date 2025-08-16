"""
Tests for data ingestion methods with retry and transformation
"""

import pytest
from unittest.mock import patch

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()
class TestIngestionMethods:
    """Test various ingestion methods"""
    
    # async def test_ingest_batch_method(self, service):
    #     """Test the ingest_batch public method"""
    #     records = [{"id": 1, "data": "test"}]
    #     
    #     with patch.object(service, '_create_destination_table') as mock_create:
    #         with patch.object(service, '_ingest_batch') as mock_ingest:
    #             result = await service.ingest_batch(records, "test_table")
    #             
    #             mock_create.assert_called_once_with("test_table")
    #             mock_ingest.assert_called_once_with("test_table", records)
    #             
    #             assert result["records_ingested"] == 1
    #             assert result["table_name"] == "test_table"
    
    async def test_ingest_with_retry_success(self, service):
        """Test ingestion with successful retry"""
        records = [{"id": 1}]
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 1}):
            result = await service.ingest_with_retry(records, max_retries=3)
            
            assert result["success"] == True
            assert result["retry_count"] == 0
            assert result["records_ingested"] == 1
    
    async def test_ingest_with_retry_failure(self, service):
        """Test ingestion with all retries failing"""
        records = [{"id": 1}]
        
        with patch.object(service, 'ingest_batch', side_effect=Exception("Ingest failed")):
            result = await service.ingest_with_retry(records, max_retries=2)
            
            assert result["success"] == False
            assert result["retry_count"] == 2
            assert result["failed_records"] == 1
    
    async def test_ingest_with_deduplication(self, service):
        """Test ingestion with deduplication"""
        records = [
            {"id": "1", "data": "test1"},
            {"id": "2", "data": "test2"},
            {"id": "1", "data": "duplicate"}  # Duplicate
        ]
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 2}):
            result = await service.ingest_with_deduplication(records)
            
            assert result["records_ingested"] == 2
            assert result["duplicates_removed"] == 1
    
    async def test_ingest_with_transform(self, service):
        """Test ingestion with data transformation"""
        records = [{"value": 1}, {"value": 2}]
        
        def transform_fn(record):
            return {"transformed_value": record["value"] * 2}
        
        with patch.object(service, 'ingest_batch', return_value={"records_ingested": 2}):
            result = await service.ingest_with_transform(records, transform_fn)
            
            assert result["records_ingested"] == 2
            assert len(result["transformed_records"]) == 2
            assert result["transformed_records"][0]["transformed_value"] == 2