import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
from app.main import app
from app.services.job_store import job_store
from app.db.models_clickhouse import get_llm_events_table_schema

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as c:
        yield c

@patch('app.services.generation_service.ClickHouseClient')
@patch('app.data.synthetic.synthetic_data_v2.main')
def test_batch_ingestion_process(mock_generate_data, mock_clickhouse_client, test_client):
    # Arrange
    mock_generate_data.return_value = [[{"log": f"log {i}"}] for i in range(5)] # 5 dummy records
    
    mock_db_instance = MagicMock()
    mock_clickhouse_client.return_value = mock_db_instance

    # Act
    response = test_client.post(
        "/api/v3/generation/synthetic_data",
        json={"num_traces": 5, "output_file": "test.json", "batch_size": 2}
    )
    job_id = response.json()["job_id"]

    # Assert
    assert response.status_code == 202
    
    # Let the background task run
    import time
    time.sleep(1) 

    # Verify ClickHouse calls
    mock_db_instance.connect.assert_called_once()
    mock_db_instance.command.assert_called_once_with(get_llm_events_table_schema('llm_events'))
    
    # 2 batches of 2, 1 batch of 1
    assert mock_db_instance.insert_data.call_count == 3
    mock_db_instance.disconnect.assert_called_once()

    # Verify job status updates
    final_job_status = job_store.get(job_id, {})
    assert final_job_status.get("status") == "completed"
    assert final_job_status.get("records_ingested") == 5