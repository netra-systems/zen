# app/routes/generation.py

import uuid
import os
import json
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from ..services.generation_service import run_content_generation_job, run_log_generation_job, run_synthetic_data_generation_job, run_data_ingestion_job, GENERATION_JOBS

router = APIRouter()

# --- Request Models ---
class ContentGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, le=os.cpu_count(), description="Max CPU cores to use.")

class LogGenParams(BaseModel):
    corpus_id: str = Field(..., description="The ID of the content corpus to use for generation.")
    num_logs: int = Field(1000, gt=0, le=100000, description="Number of log entries to generate.")
    max_cores: int = Field(4, ge=1, le=os.cpu_count(), description="Max CPU cores to use.")

class SyntheticDataGenParams(BaseModel):
    num_traces: int = Field(10000, gt=0, le=100000, description="Number of traces to generate.")
    output_file: str = Field("generated_logs_v2.json", description="The name of the output file.")

# --- API Endpoints ---

@router.post("/content", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
def create_content_corpus(params: ContentGenParams, background_tasks: BackgroundTasks):
    """Starts a background job to generate a new content corpus."""
    job_id = str(uuid.uuid4())
    GENERATION_JOBS[job_id] = {"status": "pending", "type": "content", "params": params.dict()}
    background_tasks.add_task(run_content_generation_job, job_id, params.dict())
    return {"job_id": job_id, "message": "Content generation job started."}

@router.post("/logs", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
def create_synthetic_logs(params: LogGenParams, background_tasks: BackgroundTasks):
    """Starts a background job to generate a new set of synthetic logs."""
    job_id = str(uuid.uuid4())
    GENERATION_JOBS[job_id] = {"status": "pending", "type": "logs", "params": params.dict()}
    background_tasks.add_task(run_log_generation_job, job_id, params.dict())
    return {"job_id": job_id, "message": "Synthetic log generation job started."}

class DataIngestionParams(BaseModel):
    data_path: str = Field(..., description="The path to the data file to ingest.")
    table_name: str = Field(..., description="The name of the table to ingest the data into.")


from ..services.demo_agent import create_demo_agent

class DemoAgentParams(BaseModel):
    query: str = Field(..., description="The user's query for the demo agent.")
    debug_mode: bool = Field(False, description="Enable debug mode for the agent.")


class ContentCorpusGenParams(BaseModel):
    samples_per_type: int = Field(10, gt=0, le=100, description="Number of samples to generate for each workload type.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Controls randomness. Higher is more creative.")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling probability.")
    top_k: Optional[int] = Field(None, ge=0, description="Top-k sampling control.")
    max_cores: int = Field(4, ge=1, le=os.cpu_count(), description="Max CPU cores to use.")


@router.post("/content_corpus", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
def create_content_corpus(params: ContentCorpusGenParams, background_tasks: BackgroundTasks):
    """Starts a background job to generate a new content corpus and store it in ClickHouse."""
    job_id = str(uuid.uuid4())
    GENERATION_JOBS[job_id] = {"status": "pending", "type": "content_corpus_generation", "params": params.dict()}
    background_tasks.add_task(run_content_generation_job, job_id, params.dict())
    return {"job_id": job_id, "message": "Content corpus generation job started."}


@router.post("/demo_agent", status_code=status.HTTP_200_OK)
async def demo_agent(params: DemoAgentParams):
    """Interacts with the demo agent."""
    agent = create_demo_agent(debug_mode=params.debug_mode)
    response = await agent.invoke({"messages": [{"role": "user", "content": params.query}]})
    return response


@router.post("/ingest_data", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
def ingest_data(params: DataIngestionParams, background_tasks: BackgroundTasks):
    """Starts a background job to ingest data into ClickHouse."""
    job_id = str(uuid.uuid4())
    GENERATION_JOBS[job_id] = {"status": "pending", "type": "data_ingestion", "params": params.dict()}
    background_tasks.add_task(run_data_ingestion_job, job_id, params.dict())
    return {"job_id": job_id, "message": "Data ingestion job started."}


@router.post("/synthetic_data", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
def create_synthetic_data(params: SyntheticDataGenParams, background_tasks: BackgroundTasks):
    """Starts a background job to generate new synthetic data."""
    job_id = str(uuid.uuid4())
    GENERATION_JOBS[job_id] = {"status": "pending", "type": "synthetic_data", "params": params.dict()}
    background_tasks.add_task(run_synthetic_data_generation_job, job_id, params.dict())
    return {"job_id": job_id, "message": "Synthetic data generation job started."}

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Retrieves the status of a generation job."""
    job = GENERATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@router.get("/content")
def list_content_corpuses() -> List[Dict]:
    """Lists all available, successfully generated content corpuses."""
    corpus_dir = os.path.join("app", "data", "generated", "content_corpuses")
    if not os.path.exists(corpus_dir):
        return []
    
    corpuses = []
    for job_id in os.listdir(corpus_dir):
        job_path = os.path.join(corpus_dir, job_id)
        if os.path.isdir(job_path):
            corpus_file = os.path.join(job_path, "content_corpus.json")
            if os.path.exists(corpus_file):
                corpuses.append({"corpus_id": job_id, "path": corpus_file})
    return corpuses

@router.get("/logs")
def list_log_sets() -> List[Dict]:
    """Lists all available, successfully generated synthetic log sets."""
    log_set_dir = os.path.join("app", "data", "generated", "log_sets")
    if not os.path.exists(log_set_dir):
        return []
        
    log_sets = []
    for job_id in os.listdir(log_set_dir):
        job_path = os.path.join(log_set_dir, job_id)
        if os.path.isdir(job_path):
            log_file = os.path.join(job_path, "synthetic_logs.json")
            if os.path.exists(log_file):
                log_sets.append({"log_set_id": job_id, "path": log_file})
    return log_sets
