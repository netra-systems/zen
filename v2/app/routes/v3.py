# /v2/app/routes/v3.py
import logging
import json
import os
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..v3_simulation import initialize_system, run_single_workload
from ..services.generation_service import GENERATION_JOBS

class V3RunRequest(BaseModel):
    prompt: str
    metadata: Dict[str, Any]

class V3ValidationRequest(BaseModel):
    log_set_id: str

router = APIRouter()

# Initialize the system once at startup
system = initialize_system()

@router.post("/run", status_code=200)
def run_v3_simulation(request: V3RunRequest):
    """Triggers a single workload simulation of the V3 architecture."""
    try:
        run_single_workload(system, request.prompt, request.metadata)
        return {"status": "simulation complete"}
    except Exception as e:
        logging.exception("Error during V3 simulation")
        raise HTTPException(status_code=500, detail=str(e))

def run_validation_against_log_set(log_set_id: str):
    """Background task to run the V3 simulation against a full log set."""
    job = GENERATION_JOBS.get(log_set_id)
    if not job or job.get('type') != 'logs' or job.get('status') != 'completed':
        logging.error(f"Validation run failed: Log set {log_set_id} not found or not ready.")
        return

    log_file_path = job['result_path']
    with open(log_file_path, 'r') as f:
        logs = json.load(f)

    for log in logs:
        try:
            prompt = log['request']['prompt']['messages'][0]['content']
            metadata = log['application_context']
            # In a real scenario, you might extract more metadata
            metadata['app_id'] = metadata.get('app_name', 'default') 
            run_single_workload(system, prompt, metadata)
        except (KeyError, IndexError) as e:
            logging.warning(f"Skipping log due to missing data for validation: {e}")
            continue
    logging.info(f"Completed validation run against log set {log_set_id}")

@router.post("/validate", status_code=202)
def start_validation_run(request: V3ValidationRequest, background_tasks: BackgroundTasks):
    """Starts a background task to run a validation simulation against a generated log set."""
    background_tasks.add_task(run_validation_against_log_set, request.log_set_id)
    return {"message": f"Started validation run against log set {request.log_set_id}"}
