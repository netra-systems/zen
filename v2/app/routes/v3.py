# /v2/app/routes/v3.py
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..v3_simulation import initialize_system, run_single_workload


class V3RunRequest(BaseModel):
    prompt: str
    metadata: Dict[str, Any]


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
