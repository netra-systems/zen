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

def _get_corpus_directory() -> str:
    """Get the corpus directory path."""
    return os.path.join("app", "data", "generated", "content_corpuses")

def _check_directory_exists(directory: str) -> bool:
    """Check if directory exists."""
    return os.path.exists(directory)

def _get_job_path(job_id: str, corpus_dir: str) -> str:
    """Get job directory path."""
    return os.path.join(corpus_dir, job_id)

def _create_corpus_entry_dict(job_id: str, corpus_file: str) -> Dict:
    """Create corpus entry dictionary."""
    return {"corpus_id": job_id, "path": corpus_file}

def _check_corpus_path_validity(job_path: str) -> bool:
    """Check if corpus job path is valid directory."""
    return os.path.isdir(job_path)

def _get_corpus_file_path(job_path: str) -> str:
    """Get corpus file path from job path."""
    return os.path.join(job_path, "content_corpus.json")

def _validate_corpus_job_path(job_id: str, corpus_dir: str) -> Optional[str]:
    """Validate corpus job path and return corpus file if exists."""
    job_path = _get_job_path(job_id, corpus_dir)
    if not _check_corpus_path_validity(job_path):
        return None
    corpus_file = _get_corpus_file_path(job_path)
    return corpus_file if os.path.exists(corpus_file) else None

def _build_corpus_entry(job_id: str, corpus_dir: str) -> Optional[Dict]:
    """Build corpus entry if valid."""
    corpus_file = _validate_corpus_job_path(job_id, corpus_dir)
    return _create_corpus_entry_dict(job_id, corpus_file) if corpus_file else None

def _collect_corpus_entries(corpus_dir: str) -> List[Dict]:
    """Collect all valid corpus entries."""
    corpuses = []
    for job_id in os.listdir(corpus_dir):
        entry = _build_corpus_entry(job_id, corpus_dir)
        if entry:
            corpuses.append(entry)
    return corpuses

@router.get("/content")
def list_content_corpuses() -> List[Dict]:
    """Lists all available, successfully generated content corpuses."""
    corpus_dir = _get_corpus_directory()
    if not _check_directory_exists(corpus_dir):
        return []
    return _collect_corpus_entries(corpus_dir)

def _get_log_sets_directory() -> str:
    """Get the log sets directory path."""
    return os.path.join("app", "data", "generated", "log_sets")

def _get_log_job_path(job_id: str, log_set_dir: str) -> str:
    """Get log job directory path."""
    return os.path.join(log_set_dir, job_id)

def _create_log_entry_dict(job_id: str, log_file: str) -> Dict:
    """Create log set entry dictionary."""
    return {"log_set_id": job_id, "path": log_file}

def _check_log_path_validity(job_path: str) -> bool:
    """Check if log job path is valid directory."""
    return os.path.isdir(job_path)

def _get_log_file_path(job_path: str) -> str:
    """Get log file path from job path."""
    return os.path.join(job_path, "synthetic_logs.json")

def _validate_log_job_path(job_id: str, log_set_dir: str) -> Optional[str]:
    """Validate log job path and return log file if exists."""
    job_path = _get_log_job_path(job_id, log_set_dir)
    if not _check_log_path_validity(job_path):
        return None
    log_file = _get_log_file_path(job_path)
    return log_file if os.path.exists(log_file) else None

def _build_log_set_entry(job_id: str, log_set_dir: str) -> Optional[Dict]:
    """Build log set entry if valid."""
    log_file = _validate_log_job_path(job_id, log_set_dir)
    return _create_log_entry_dict(job_id, log_file) if log_file else None

def _collect_log_set_entries(log_set_dir: str) -> List[Dict]:
    """Collect all valid log set entries."""
    log_sets = []
    for job_id in os.listdir(log_set_dir):
        entry = _build_log_set_entry(job_id, log_set_dir)
        if entry:
            log_sets.append(entry)
    return log_sets

@router.get("/logs")
def list_log_sets() -> List[Dict]:
    """Lists all available, successfully generated synthetic log sets."""
    log_set_dir = _get_log_sets_directory()
    if not _check_directory_exists(log_set_dir):
        return []
    return _collect_log_set_entries(log_set_dir)

def _get_clickhouse_logger():
    """Get logger for ClickHouse operations."""
    logger = central_logger.get_logger(__name__)
    logger.info("Attempting to list ClickHouse tables.")
    return logger

async def _get_validated_clickhouse_client(logger):
    """Get and validate ClickHouse client."""
    client = await get_clickhouse_client().__aenter__()
    if client is None:
        logger.error("Failed to get ClickHouse client.")
        raise HTTPException(status_code=500, detail="Failed to get ClickHouse client.")
    logger.info("Successfully acquired ClickHouse client.")
    return client

async def _execute_show_tables_query(client, logger):
    """Execute SHOW TABLES query."""
    result = await client.execute_query("SHOW TABLES")
    logger.info(f"Successfully executed 'SHOW TABLES' query. Result: {result}")
    return result

def _process_tables_result(result, logger) -> List[str]:
    """Process tables query result."""
    if result:
        table_names = [row[0] for row in result]
        logger.info(f"Returning table names: {table_names}")
        return table_names
    logger.info("No tables found in ClickHouse.")
    return []

async def _handle_clickhouse_query_error(e: Exception, logger):
    """Handle ClickHouse query errors."""
    logger.error(f"Failed to fetch tables from ClickHouse: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Failed to fetch tables from ClickHouse: {e}")

async def _execute_clickhouse_tables_query(logger):
    """Execute ClickHouse tables query with client."""
    async with get_clickhouse_client() as client:
        validated_client = await _get_validated_clickhouse_client(logger)
        result = await _execute_show_tables_query(validated_client, logger)
        return _process_tables_result(result, logger)

@router.get("/clickhouse_tables")
async def list_clickhouse_tables() -> List[str]:
    """Lists all tables in the ClickHouse database."""
    logger = _get_clickhouse_logger()
    try:
        return await _execute_clickhouse_tables_query(logger)
    except Exception as e:
        await _handle_clickhouse_query_error(e, logger)
