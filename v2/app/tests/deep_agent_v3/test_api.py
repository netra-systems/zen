
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_agent_run_success():
    run_id = "test-run-api-success"
    agent_request = {
        "user_id": "test_user",
        "workloads": [{
            "run_id": run_id,
            "query": "test query"
        }]
    }
    response = client.post("/api/v3/agent/create", json=agent_request)
    assert response.status_code == 202
    assert response.json()["run_id"] == run_id

def test_create_agent_run_no_workload():
    agent_request = {
        "user_id": "test_user",
        "workloads": []
    }
    response = client.post("/api/v3/agent/create", json=agent_request)
    assert response.status_code == 400

def test_get_agent_step_not_found():
    response = client.get("/api/v3/agent/non-existent-run/step")
    assert response.status_code == 404

def test_get_agent_history_not_found():
    response = client.get("/api/v3/agent/non-existent-run/history")
    assert response.status_code == 404
