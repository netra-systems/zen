"""Generation route specific utilities."""

import os
import uuid
from typing import Dict, List, Optional
from fastapi import BackgroundTasks
from netra_backend.app.services.job_store import job_store


def _build_job_data(job_type: str, params: Dict) -> Dict:
    """Build job data dictionary."""
    return {
        "status": "pending", 
        "type": job_type, 
        "params": params
    }

async def create_job_entry(job_type: str, params: Dict) -> str:
    """Create job entry and return job ID."""
    job_id = str(uuid.uuid4())
    job_data = _build_job_data(job_type, params)
    await job_store.set(job_id, job_data)
    return job_id


def add_background_task(
    background_tasks: BackgroundTasks, 
    task_func, 
    job_id: str, 
    params: Dict
) -> None:
    """Add background task for job processing."""
    background_tasks.add_task(task_func, job_id, params)


def build_job_response(job_id: str, message: str) -> Dict[str, str]:
    """Build job creation response."""
    return {"job_id": job_id, "message": message}


def get_directory_path(*path_parts: str) -> str:
    """Get directory path from parts."""
    return os.path.join(*path_parts)


def check_directory_exists(directory: str) -> bool:
    """Check if directory exists."""
    return os.path.exists(directory)


def check_file_exists(file_path: str) -> bool:
    """Check if file exists."""
    return os.path.exists(file_path)


def check_path_is_directory(path: str) -> bool:
    """Check if path is a directory."""
    return os.path.isdir(path)


def list_directory_contents(directory: str) -> List[str]:
    """List directory contents."""
    return os.listdir(directory)


def create_corpus_entry(job_id: str, corpus_file: str) -> Dict:
    """Create corpus entry dictionary."""
    return {"corpus_id": job_id, "path": corpus_file}


def create_log_entry(job_id: str, log_file: str) -> Dict:
    """Create log set entry dictionary."""
    return {"log_set_id": job_id, "path": log_file}


def build_corpus_file_path(job_path: str) -> str:
    """Build corpus file path."""
    return os.path.join(job_path, "content_corpus.json")


def build_log_file_path(job_path: str) -> str:
    """Build log file path."""
    return os.path.join(job_path, "synthetic_logs.json")