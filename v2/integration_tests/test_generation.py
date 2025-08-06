import pytest
import asyncio
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from app.main import app
from app.services.generation_service import GENERATION_JOBS, get_corpus_from_clickhouse, save_corpus_to_clickhouse, run_synthetic_data_generation_job
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import get_content_corpus_schema, ContentCorpus, get_llm_events_table_schema
from app.db.clickhouse_base import ClickHouseDatabase

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def clickhouse_client():
    async with get_clickhouse_client() as client:
        yield client

@pytest.mark.asyncio
@patch('app.routes.generation.run_content_generation_job', new_callable=AsyncMock)
async def test_content_generation_with_custom_table(mock_run_job, test_client):
    # Arrange
    custom_table_name = f"test_content_corpus_{uuid.uuid4().hex}"

    async def side_effect(job_id, params):
        GENERATION_JOBS[job_id] = {
            "status": "completed",
            "summary": {
                "message": f"Corpus generated and saved to {params['clickhouse_table']}"
            }
        }

    mock_run_job.side_effect = side_effect
    
    # Act
    response = test_client.post(
        "/api/v3/generation/content_corpus",
        json={
            "samples_per_type": 1,
            "temperature": 0.1,
            "max_cores": 1,
            "clickhouse_table": custom_table_name
        }
    )

    # Assert
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Poll for job completion
    for _ in range(10): # Poll for a maximum of 1 second
        status_response = test_client.get(f"/api/v3/generation/jobs/{job_id}")
        assert status_response.status_code == 200
        job_status = status_response.json()
        if job_status["status"] == "completed":
            assert f"Corpus generated and saved to {custom_table_name}" in job_status["summary"]["message"]
            return
        elif job_status["status"] == "failed":
            pytest.fail("Content generation job failed")
        await asyncio.sleep(0.1)
    pytest.fail("Job did not complete in time")

@pytest.mark.asyncio
@patch('app.routes.generation.run_synthetic_data_generation_job', new_callable=AsyncMock)
async def test_synthetic_data_generation_with_table_selection(mock_run_job, test_client):
    # Arrange
    source_table = f"test_source_corpus_{uuid.uuid4().hex}"
    destination_table = f"test_destination_data_{uuid.uuid4().hex}"

    async def side_effect(job_id, params):
        # This is now the mock, so we update the job status here
        GENERATION_JOBS[job_id] = {
            "status": "completed",
            "summary": {
                "message": f"Synthetic data generated and saved to {params['destination_table']}"
            }
        }

    mock_run_job.side_effect = side_effect

    # Act
    response = test_client.post(
        "/api/v3/generation/synthetic_data",
        json={
            "num_traces": 10,
            "source_table": source_table,
            "destination_table": destination_table
        }
    )

    # Assert
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    await asyncio.sleep(0.1) 

    # Poll for job completion
    for _ in range(10):
        status_response = test_client.get(f"/api/v3/generation/jobs/{job_id}")
        assert status_response.status_code == 200
        job_status = status_response.json()
        if job_status["status"] == "completed":
            assert f"Synthetic data generated and saved to {destination_table}" in job_status["summary"]["message"]
            break
        elif job_status["status"] == "failed":
            pytest.fail(f"Synthetic data generation job failed: {job_status.get('error')}")
        await asyncio.sleep(0.1)
    else:
        pytest.fail("Job did not complete in time")

@pytest.mark.asyncio
@patch('app.services.generation_service.ClickHouseDatabase')
async def test_save_and_get_corpus(MockClickHouseDatabase):
    """Test saving a corpus to ClickHouse and retrieving it."""
    # Arrange
    mock_instance = MagicMock()
    mock_instance.command = AsyncMock()
    mock_instance.insert_data = AsyncMock()
    mock_instance.execute_query = AsyncMock(return_value=[
        {'workload_type': 'test_workload', 'prompt': 'prompt1', 'response': 'response1'},
        {'workload_type': 'test_workload', 'prompt': 'prompt2', 'response': 'response2'}
    ])
    MockClickHouseDatabase.return_value = mock_instance

    table_name = f"test_corpus_{uuid.uuid4().hex}"
    test_corpus = {
        "test_workload": [("prompt1", "response1"), ("prompt2", "response2")]
    }

    # Act
    await save_corpus_to_clickhouse(test_corpus, table_name)
    retrieved_corpus = await get_corpus_from_clickhouse(table_name)

    # Assert
    mock_instance.command.assert_called_once()
    mock_instance.insert_data.assert_called_once()
    mock_instance.execute_query.assert_called_once_with(f"SELECT workload_type, prompt, response FROM {table_name}")
    assert retrieved_corpus == {"test_workload": [('prompt1', 'response1'), ('prompt2', 'response2')]}

@pytest.mark.asyncio
@patch('app.services.generation_service.ingest_records', new_callable=AsyncMock)
@patch('app.services.generation_service.synthetic_data_main')
@patch('app.services.generation_service.get_corpus_from_clickhouse', new_callable=AsyncMock)
@patch('app.services.generation_service.ClickHouseDatabase')
async def test_run_synthetic_data_generation_job_e2e(MockClickHouseDatabase, mock_get_corpus, mock_synth_main, mock_ingest):
    """An end-to-end test for the synthetic data generation job."""
    # Arrange
    mock_db_instance = MagicMock()
    mock_db_instance.command = AsyncMock()
    MockClickHouseDatabase.return_value = mock_db_instance

    job_id = str(uuid.uuid4())
    source_table = 'source_corpus'
    destination_table = 'dest_table'
    
    mock_get_corpus.return_value = {"greeting": [("hello", "world")]}
    mock_synth_main.return_value = [{"id": i} for i in range(5)]
    mock_ingest.side_effect = [2, 2, 1] 

    params = {
        "num_traces": 5,
        "source_table": source_table,
        "destination_table": destination_table,
        "batch_size": 2
    }

    # Act
    await run_synthetic_data_generation_job(job_id, params)

    # Assert
    job_status = GENERATION_JOBS.get(job_id)
    assert job_status is not None
    assert job_status["status"] == "completed"
    assert job_status["summary"]["records_ingested"] == 5
    mock_db_instance.command.assert_called_once_with(get_llm_events_table_schema(destination_table))
    assert mock_ingest.call_count == 3

    if job_id in GENERATION_JOBS:
        del GENERATION_JOBS[job_id]
