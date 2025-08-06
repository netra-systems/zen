import pytest
import asyncio
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from app.main import app
from app.services.generation_service import GENERATION_JOBS, get_corpus_from_clickhouse, save_corpus_to_clickhouse
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
@patch('app.services.generation_service.run_content_generation_job', new_callable=AsyncMock)
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
@patch('app.services.generation_service.run_synthetic_data_generation_job', new_callable=AsyncMock)
async def test_synthetic_data_generation_with_table_selection(mock_run_job, test_client, clickhouse_client: ClickHouseDatabase):
    # Arrange
    source_table = f"test_source_corpus_{uuid.uuid4().hex}"
    destination_table = f"test_destination_data_{uuid.uuid4().hex}"

    # Create and populate a temporary source table
    try:
        schema = get_content_corpus_schema(source_table)
        await clickhouse_client.command(schema)
        
        sample_corpus = [
            ContentCorpus(workload_type="test", prompt="p1", response="r1", record_id=str(uuid.uuid4())),
            ContentCorpus(workload_type="test", prompt="p2", response="r2", record_id=str(uuid.uuid4()))
        ]
        records = [list(item.model_dump().values()) for item in sample_corpus]
        column_names = list(ContentCorpus.model_fields.keys())
        await clickhouse_client.insert_data(source_table, records, column_names)

        async def side_effect(job_id, params):
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

        # Poll for job completion
        for _ in range(10):
            status_response = test_client.get(f"/api/v3/generation/jobs/{job_id}")
            assert status_response.status_code == 200
            job_status = status_response.json()
            if job_status["status"] == "completed":
                assert f"Synthetic data generated and saved to {destination_table}" in job_status["summary"]["message"]
                # Verify destination table was created
                result = await clickhouse_client.command(f"EXISTS TABLE {destination_table}")
                assert result == 1
                break
            elif job_status["status"] == "failed":
                pytest.fail(f"Synthetic data generation job failed: {job_status.get('error')}")
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Job did not complete in time")

    finally:
        # Clean up the temporary tables
        await clickhouse_client.command(f"DROP TABLE IF EXISTS {source_table}")
        await clickhouse_client.command(f"DROP TABLE IF EXISTS {destination_table}")

@pytest.mark.asyncio
async def test_save_and_get_corpus(clickhouse_client: ClickHouseDatabase):
    """Test saving a corpus to ClickHouse and retrieving it."""
    table_name = f"test_corpus_{uuid.uuid4().hex}"
    test_corpus = {
        "test_workload": [("prompt1", "response1"), ("prompt2", "response2")]
    }

    try:
        # Save the corpus
        await save_corpus_to_clickhouse(test_corpus, table_name)

        # Retrieve the corpus
        retrieved_corpus = await get_corpus_from_clickhouse(table_name)

        # Assertions
        assert "test_workload" in retrieved_corpus
        assert len(retrieved_corpus["test_workload"]) == 2
        assert tuple(retrieved_corpus["test_workload"][0]) == ("prompt1", "response1")

    finally:
        # Clean up the temporary table
        await clickhouse_client.command(f"DROP TABLE IF EXISTS {table_name}")

@pytest.mark.asyncio
async def test_run_synthetic_data_generation_job_e2e(clickhouse_client: ClickHouseDatabase):
    """An end-to-end test for the synthetic data generation job."""
    source_table = f"test_source_corpus_e2e_{uuid.uuid4().hex}"
    destination_table = f"test_dest_data_e2e_{uuid.uuid4().hex}"
    job_id = str(uuid.uuid4())

    # 1. Setup: Create and populate a source corpus table
    try:
        schema = get_content_corpus_schema(source_table)
        await clickhouse_client.command(schema)
        sample_corpus = {
            "greeting": [("hello", "world"), ("hey", "there")]
        }
        await save_corpus_to_clickhouse(sample_corpus, source_table)

        # 2. Execute: Run the actual job function
        params = {
            "num_traces": 5,
            "source_table": source_table,
            "destination_table": destination_table,
            "batch_size": 2
        }
        
        # Mock the parts that are external or too slow for a unit test
        with patch('app.services.generation_service.synthetic_data_main') as mock_synth_main, \
             patch('app.services.generation_service.ingest_records', new_callable=AsyncMock) as mock_ingest:
            
            # Mock the synthetic data generator to return predictable data
            mock_synth_main.return_value = [{"id": i} for i in range(5)]
            # Mock the ingestion to simulate success
            mock_ingest.return_value = 2 # Batch size

            await run_synthetic_data_generation_job(job_id, params)

        # 3. Assert: Check the job status and outcomes
        job_status = GENERATION_JOBS.get(job_id)
        assert job_status is not None
        assert job_status["status"] == "completed"
        assert job_status["summary"]["records_ingested"] == 6 # 2 + 2 + 2 (last batch is 1, but ingest returns 2)

        # Verify that the destination table was created by the job
        table_exists = await clickhouse_client.command(f"EXISTS TABLE {destination_table}")
        assert table_exists == 1

    finally:
        # 4. Teardown: Clean up tables
        await clickhouse_client.command(f"DROP TABLE IF EXISTS {source_table}")
        await clickhouse_client.command(f"DROP TABLE IF EXISTS {destination_table}")
        if job_id in GENERATION_JOBS:
            del GENERATION_JOBS[job_id]