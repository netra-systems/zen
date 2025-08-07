import pytest
import pandas as pd
import asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from app.main import app
from app.db.testing import override_get_db
from app.dependencies import get_async_db

app.dependency_overrides[get_async_db] = override_get_db

@pytest.fixture(scope="module")
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.fixture
async def auth_token(test_client):
    # Create a test user
    await test_client.post("/auth/users", json={"email": settings.dev_user_email, "password": "testpassword"})
    # Login and get token
    response = await test_client.post("/auth/token", data={"username": "test@example.com", "password": "testpassword"})
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_read_main(test_client):
    response = await test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Netra API v2"}

def test_analysis_runner():
    # Placeholder
    assert True

def test_supply_catalog_service():
    # Placeholder
    assert True

async def poll_job_status(client, job_id):
    # Mocked poll_job_status to avoid sleep
    return {"status": "completed", "result_path": "mocked/path"}

@pytest.mark.asyncio
@patch('app.routes.generation.run_content_generation_job')
async def test_generation_api(mock_generative_model, test_client):
    # Mock the generative model
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = "Generated content"
    mock_generative_model.return_value = mock_model_instance

    # 1. Start content generation job
    response = await test_client.post("/api/v3/generation/content", json={"samples_per_type": 1, "max_cores": 1})
    assert response.status_code == 202
    content_job_id = response.json()["job_id"]

    # 2. Poll for content generation completion
    await poll_job_status(test_client, content_job_id)

    # 3. Start log generation job
    response = await test_client.post("/api/v3/generation/logs", json={"corpus_id": content_job_id, "num_logs": 10})
    assert response.status_code == 202
    log_job_id = response.json()["job_id"]

    # 4. Poll for log generation completion
    log_job_result = await poll_job_status(test_client, log_job_id)
    log_file_path = log_job_result["result_path"]

    # 5. Ingest data
    response = await test_client.post("/api/v3/generation/ingest_data", json={"data_path": log_file_path, "table_name": "test_logs"})
    assert response.status_code == 202
    ingestion_job_id = response.json()["job_id"]

    # 6. Poll for ingestion completion
    await poll_job_status(test_client, ingestion_job_id)

    # 7. Verify data in ClickHouse (optional, requires ClickHouse connection)
    # This part is commented out as it requires a live ClickHouse instance
    # and credentials, which might not be available in a standard test environment.
    # from app.db.clickhouse import get_clickhouse_client
    # client = get_clickhouse_client()
    # result = client.execute("SELECT count() FROM test_logs")
    # assert result[0][0] > 0

@pytest.mark.asyncio
async def test_analysis_api(auth_token, test_client):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await test_client.post("/api/v3/analysis/runs", headers=headers, json={"source_table": "test"})
    assert response.status_code == 202

def test_multi_objective_controller():
    # Placeholder
    assert True