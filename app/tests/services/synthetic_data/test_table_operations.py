"""
Tests for ClickHouse table operations and ingestion
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.mark.asyncio
class TestTableOperations:
    """Test ClickHouse table operations"""
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_create_destination_table(self, mock_get_client, service):
        """Test creating destination table"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        await service._create_destination_table("test_table")
        
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_table" in call_args
        assert "MergeTree()" in call_args
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_ingest_batch_empty(self, mock_get_client, service):
        """Test ingesting empty batch"""
        await service._ingest_batch("test_table", [])
        
        # Should not attempt ClickHouse operation
        mock_get_client.assert_not_called()
    
    @patch('app.services.synthetic_data_service.get_clickhouse_client')
    async def test_ingest_batch_with_data(self, mock_get_client, service):
        """Test ingesting batch with data"""
        mock_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        batch = [
            {
                "event_id": "event1",
                "trace_id": "trace1",
                "span_id": "span1",
                "parent_span_id": None,
                "timestamp_utc": datetime.now(UTC),
                "workload_type": "test",
                "agent_type": "test",
                "tool_invocations": ["tool1"],
                "request_payload": {"prompt": "test"},
                "response_payload": {"completion": "test"},
                "metrics": {"latency": 100},
                "corpus_reference_id": None
            }
        ]
        
        await service._ingest_batch("test_table", batch)
        
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args
        assert "INSERT INTO test_table" in call_args[0][0]
        assert len(call_args[0][1]) == 1  # One record