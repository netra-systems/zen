
import pytest
import pandas as pd
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.db.testing import override_get_db
from app.dependencies import get_async_db

app.dependency_overrides[get_async_db] = override_get_db

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_token(test_client):
    # Create a test user
    test_client.post("/auth/users", json={"email": "test@example.com", "password": "testpassword"})
    # Login and get token
    response = test_client.post("/auth/token", data={"username": "test@example.com", "password": "testpassword"})
    return response.json()["access_token"]

def test_read_main(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Netra API v2"}

def test_analysis_runner():
    # Placeholder
    assert True

def test_supply_catalog_service():
    # Placeholder
    assert True

@patch('app.services.generation_service.genai.GenerativeModel')
def test_generation_api(mock_generative_model, test_client):
    # Mock the generative model
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = "Generated content"
    mock_generative_model.return_value = mock_model_instance

    # 1. Start content generation job
    response = test_client.post("/api/v3/generation/content", json={"samples_per_type": 1, "max_cores": 1})
    assert response.status_code == 202
    content_job_id = response.json()["job_id"]

    # 2. Poll for content generation completion
    while True:
        response = test_client.get(f"/api/v3/generation/jobs/{content_job_id}")
        assert response.status_code == 200
        status = response.json()["status"]
        if status == "completed":
            break
        elif status == "failed":
            pytest.fail("Content generation job failed")
        time.sleep(1)

    # 3. Start log generation job
    response = test_client.post("/api/v3/generation/logs", json={"corpus_id": content_job_id, "num_logs": 10})
    assert response.status_code == 202
    log_job_id = response.json()["job_id"]

    # 4. Poll for log generation completion
    while True:
        response = test_client.get(f"/api/v3/generation/jobs/{log_job_id}")
        assert response.status_code == 200
        status = response.json()["status"]
        if status == "completed":
            log_file_path = response.json()["result_path"]
            break
        elif status == "failed":
            pytest.fail("Log generation job failed")
        time.sleep(1)

    # 5. Ingest data
    response = test_client.post("/api/v3/generation/ingest_data", json={"data_path": log_file_path, "table_name": "test_logs"})
    assert response.status_code == 202
    ingestion_job_id = response.json()["job_id"]

    # 6. Poll for ingestion completion
    while True:
        response = test_client.get(f"/api/v3/generation/jobs/{ingestion_job_id}")
        assert response.status_code == 200
        status = response.json()["status"]
        if status == "completed":
            break
        elif status == "failed":
            pytest.fail("Data ingestion job failed")
        time.sleep(1)

    # 7. Verify data in ClickHouse (optional, requires ClickHouse connection)
    # This part is commented out as it requires a live ClickHouse instance
    # and credentials, which might not be available in a standard test environment.
    # from app.db.clickhouse import get_clickhouse_client
    # client = get_clickhouse_client()
    # result = client.execute("SELECT count() FROM test_logs")
    # assert result[0][0] > 0


def test_analysis_api(auth_token, test_client):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = test_client.post("/api/v3/analysis/runs", headers=headers, json={"source_table": "test"})
    assert response.status_code == 202

def test_multi_objective_controller():
    # Placeholder
    assert True
