# app/routes/generation.py

import uuid
import os
import json
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Depends

from app.services.generation_service import run_content_generation_job, run_log_generation_job, run_synthetic_data_generation_job, run_data_ingestion_job
from app.services.job_store import job_store
from app.db.clickhouse import get_clickhouse_client
from app.logging_config import central_logger
from app.schemas import (LogGenParams, SyntheticDataGenParams, ContentGenParams, 
                         DataIngestionParams, ContentCorpusGenParams)

router = APIRouter()

@router.post("/content", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def create_content_corpus(params: ContentGenParams, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Starts a background job to generate a new content corpus."""
    job_id = str(uuid.uuid4())
    await job_store.set(job_id, {"status": "pending", "type": "content", "params": params.model_dump()})
    background_tasks.add_task(run_content_generation_job, job_id, params.model_dump())
    return {"job_id": job_id, "message": "Content generation job started."}

@router.post("/logs", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def create_synthetic_logs(params: LogGenParams, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Starts a background job to generate a new set of synthetic logs."""
    job_id = str(uuid.uuid4())
    await job_store.set(job_id, {"status": "pending", "type": "logs", "params": params.model_dump()})
    background_tasks.add_task(run_log_generation_job, job_id, params.model_dump())
    return {"job_id": job_id, "message": "Synthetic log generation job started."}

@router.post("/content_corpus", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def create_content_corpus_and_store(params: ContentCorpusGenParams, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Starts a background job to generate a new content corpus and store it in ClickHouse."""
    job_id = str(uuid.uuid4())
    await job_store.set(job_id, {"status": "pending", "type": "content_corpus_generation", "params": params.model_dump()})
    background_tasks.add_task(run_content_generation_job, job_id, params.model_dump())
    return {"job_id": job_id, "message": "Content corpus generation job started."}


@router.post("/ingest_data", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def ingest_data(params: DataIngestionParams, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Starts a background job to ingest data into ClickHouse."""
    job_id = str(uuid.uuid4())
    await job_store.set(job_id, {"status": "pending", "type": "data_ingestion", "params": params.model_dump()})
    background_tasks.add_task(run_data_ingestion_job, job_id, params.model_dump())
    return {"job_id": job_id, "message": "Data ingestion job started."}


@router.post("/synthetic_data", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str])
async def create_synthetic_data(params: SyntheticDataGenParams, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Starts a background job to generate new synthetic data."""
    job_id = str(uuid.uuid4())
    await job_store.set(job_id, {"status": "pending", "type": "synthetic_data", "params": params.model_dump()})
    background_tasks.add_task(run_synthetic_data_generation_job, job_id, params.model_dump())
    return {"job_id": job_id, "message": "Synthetic data generation job started."}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Retrieves the status of a generation job."""
    job = await job_store.get(job_id)
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

@router.get("/clickhouse_tables")
async def list_clickhouse_tables() -> List[str]:
    """Lists all tables in the ClickHouse database."""
    logger = central_logger.get_logger(__name__)
    logger.info("Attempting to list ClickHouse tables.")
    try:
        async with get_clickhouse_client() as client:
            if client is None:
                logger.error("Failed to get ClickHouse client.")
                raise HTTPException(status_code=500, detail="Failed to get ClickHouse client.")
            logger.info("Successfully acquired ClickHouse client.")
            result = await client.execute_query("SHOW TABLES")
            logger.info(f"Successfully executed 'SHOW TABLES' query. Result: {result}")
            if result:
                table_names = [row[0] for row in result]
                logger.info(f"Returning table names: {table_names}")
                return table_names
            else:
                logger.info("No tables found in ClickHouse.")
                return []
    except Exception as e:
        logger.error(f"Failed to fetch tables from ClickHouse: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables from ClickHouse: {e}")
