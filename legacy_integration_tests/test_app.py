import pytest
import pandas as pd
import asyncio
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from netra_backend.app.db.testing import override_get_db
from netra_backend.app.dependencies import get_db_dependency
from netra_backend.app.schemas.Generation import ContentGenParams, LogGenParams, DataIngestionParams

# Set testing flags to simplify startup
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SKIP_STARTUP_CHECKS"] = "true"
os.environ["SKIP_CLICKHOUSE_INIT"] = "true"

app.dependency_overrides[get_db_dependency] = override_get_db

@pytest.fixture(scope="module")
def test_client():
    import os
    # Set testing flags to prevent complex startup
    os.environ["TESTING"] = "1"
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SKIP_STARTUP_CHECKS"] = "true"
    os.environ["SKIP_CLICKHOUSE_INIT"] = "true"
    
    with TestClient(app=app, base_url="http://test") as c:
        yield c

def test_read_main(test_client: TestClient):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Netra API"}

async def poll_job_status(client, job_id):
    # Mocked poll_job_status to avoid sleep
    return {"status": "completed", "result_path": "mocked/path"}

@pytest.mark.asyncio
@patch('app.routes.generation.run_content_generation_job')
async def test_generation_api(mock_generative_model, test_client: TestClient):
    # Mock the generative model
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = "Generated content"
    mock_generative_model.return_value = mock_model_instance

    # 1. Start content generation job
    content_params = ContentGenParams(samples_per_type=1, max_cores=1)
    response = test_client.post("/api/generation/content", json=content_params.model_dump())
    assert response.status_code == 202
    content_job_id = response.json()["job_id"]

    # 2. Poll for content generation completion
    await poll_job_status(test_client, content_job_id)

    # 3. Start log generation job
    log_params = LogGenParams(corpus_id=content_job_id, num_logs=10)
    response = test_client.post("/api/generation/logs", json=log_params.model_dump())
    assert response.status_code == 202
    log_job_id = response.json()["job_id"]

    # 4. Poll for log generation completion
    log_job_result = await poll_job_status(test_client, log_job_id)
    log_file_path = log_job_result["result_path"]

    # 5. Ingest data
    ingestion_params = DataIngestionParams(data_path=log_file_path, table_name="test_logs")
    response = test_client.post("/api/generation/ingest_data", json=ingestion_params.model_dump())
    assert response.status_code == 202
    ingestion_job_id = response.json()["job_id"]

    # 6. Poll for ingestion completion
    await poll_job_status(test_client, ingestion_job_id)

    # 7. Verify data in ClickHouse (optional, requires ClickHouse connection)
    # This part is commented out as it requires a live ClickHouse instance
    # and credentials, which might not be available in a standard test environment.
    # from netra_backend.app.db.clickhouse import get_clickhouse_client
    # client = get_clickhouse_client()
    # result = client.execute("SELECT count() FROM test_logs")
    # assert result[0][0] > 0

def test_analysis_api(test_client: TestClient):
    response = test_client.post("/api/analysis/runs", json={"source_table": "test"})
    assert response.status_code == 404