
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.data.ingestion import ingest_records, prepare_data_for_insert
from app.data.content_corpus import DEFAULT_CONTENT_CORPUS
from app.db.models_clickhouse import CONTENT_CORPUS_TABLE_NAME

@pytest.fixture
def mock_clickhouse_client():
    """Fixture to create a mock ClickHouse client."""
    client = MagicMock()
    client.insert_data = AsyncMock()
    client.command = AsyncMock()
    client.query = AsyncMock()
    client.table_exists = AsyncMock(return_value=True)
    return client

@pytest.mark.asyncio
async def test_ingest_records(mock_clickhouse_client):
    """Test that records are ingested correctly."""
    records = [
        {"event_metadata_log_schema_version": "3.0.0", "event_metadata_event_id": "1"},
        {"event_metadata_log_schema_version": "3.0.0", "event_metadata_event_id": "2"}
    ]
    
    await ingest_records(mock_clickhouse_client, records, "test_table")
    
    mock_clickhouse_client.insert_data.assert_called_once()
    args, kwargs = mock_clickhouse_client.insert_data.call_args
    assert args[0] == "test_table"
    assert len(args[1]) == 2

def test_prepare_data_for_insert():
    """Test that data is prepared correctly for insertion."""
    records = [
        {"col1": "a", "col2": 1},
        {"col2": 2, "col1": "b"}
    ]
    
    columns, data = prepare_data_for_insert(records)
    
    assert columns == ["col1", "col2"]
    assert data == [["a", 1], ["b", 2]]

@pytest.mark.asyncio
async def test_populate_with_default_data(mock_clickhouse_client):
    """Test that the database is populated with the default data."""
    all_records = []
    for workload_type, content_list in DEFAULT_CONTENT_CORPUS.items():
        for prompt, response in content_list:
            all_records.append({
                "workload_type": workload_type,
                "prompt": prompt,
                "response": response,
            })

    await ingest_records(mock_clickhouse_client, all_records, CONTENT_CORPUS_TABLE_NAME)

    mock_clickhouse_client.insert_data.assert_called_once()
    inserted_data = mock_clickhouse_client.insert_data.call_args[0][1]
    assert len(inserted_data) == len(all_records)

