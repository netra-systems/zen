import os
import json
import time
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_store import job_store

client = TestClient(app)


def test_create_and_get_job():
    # 1. Create a new job
    response = client.post(
        "/generation/synthetic_data",
        json={
            "num_traces": 10,
            "num_users": 1,
            "error_rate": 0.1,
            "event_types": ["search"],
            "source_table": "content_corpus",
            "destination_table": "synthetic_data",
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # 2. Get the job status
    response = client.get(f"/generation/jobs/{job_id}")
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "pending"

    # 3. Verify that the job is stored in the file system
    job_path = job_store._get_job_path(job_id)
    assert os.path.exists(job_path)

    # 4. Clean up the job file
    os.remove(job_path)
