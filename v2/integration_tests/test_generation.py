
import pytest
import time
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.generation_service import GENERATION_JOBS
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import get_content_corpus_schema, ContentCorpus

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def clickhouse_client():
    with get_clickhouse_client() as client:
        yield client

@patch('app.services.generation_service.run_content_generation_job')
def test_content_generation_with_custom_table(mock_run_job, test_client):
    # Arrange
    custom_table_name = "my_custom_corpus_table"

    def side_effect(job_id, params):
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
    while True:
        status_response = test_client.get(f"/api/v3/generation/jobs/{job_id}")
        assert status_response.status_code == 200
        job_status = status_response.json()
        if job_status["status"] == "completed":
            assert f"Corpus generated and saved to {custom_table_name}" in job_status["summary"]["message"]
            break
        elif job_status["status"] == "failed":
            pytest.fail("Content generation job failed")
        time.sleep(0.1)

@patch('app.services.generation_service.run_synthetic_data_generation_job')
def test_synthetic_data_generation_with_table_selection(mock_run_job, test_client, clickhouse_client):
    # Arrange
    source_table = f"test_source_corpus_{uuid.uuid4().hex}"
    destination_table = f"test_destination_data_{uuid.uuid4().hex}"

    # Create and populate a temporary source table
    try:
        schema = get_content_corpus_schema(source_table)
        clickhouse_client.command(schema)
        
        sample_corpus = [
            ContentCorpus(workload_type="test", prompt="p1", response="r1", record_id=str(uuid.uuid4())),
            ContentCorpus(workload_type="test", prompt="p2", response="r2", record_id=str(uuid.uuid4()))
        ]
        records = [list(item.model_dump().values()) for item in sample_corpus]
        column_names = list(ContentCorpus.model_fields.keys())
        clickhouse_client.insert_data(source_table, records, column_names)

        def side_effect(job_id, params):
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
        while True:
            status_response = test_client.get(f"/api/v3/generation/jobs/{job_id}")
            assert status_response.status_code == 200
            job_status = status_response.json()
            if job_status["status"] == "completed":
                assert f"Synthetic data generated and saved to {destination_table}" in job_status["summary"]["message"]
                break
            elif job_status["status"] == "failed":
                pytest.fail(f"Synthetic data generation job failed: {job_status.get('error')}")
            time.sleep(0.1)

    finally:
        # Clean up the temporary tables
        clickhouse_client.command(f"DROP TABLE IF EXISTS {source_table}")
        clickhouse_client.command(f"DROP TABLE IF EXISTS {destination_table}")
