"""Job management utilities for generation services.

Provides centralized job status management, progress tracking,
and corpus data access for all generation services.
"""

import json
import os
import time
import uuid
from collections import defaultdict
from typing import Any, Dict

import pandas as pd

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from netra_backend.app.db.models_clickhouse import get_content_corpus_schema
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.corpus import ContentCorpus
from netra_backend.app.services.job_store import job_store
# WebSocket manager import moved to function level for security

logger = central_logger.get_logger(__name__)


async def update_job_status(job_id: str, status: str, user_context=None, **kwargs):
    """Updates the status and other attributes of a generation job and sends a WebSocket message.
    
    Args:
        job_id: The job identifier
        status: New job status
        user_context: Optional user execution context for WebSocket notifications
        **kwargs: Additional status attributes
    """
    await job_store.update(job_id, status, **kwargs)
    
    # Send WebSocket notification if user context is available
    if user_context:
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            websocket_manager = create_websocket_manager(user_context)
            await websocket_manager.broadcast_to_job(job_id, {"job_id": job_id, "status": status, **kwargs})
        except Exception as e:
            logger.error(f"Failed to send WebSocket job status update: {e}")
    else:
        logger.debug(f"Job status updated without WebSocket notification (no user context): {job_id} -> {status}")


def _build_clickhouse_config() -> dict:
    """Build ClickHouse connection configuration."""
    return {
        'host': settings.clickhouse_https.host,
        'port': settings.clickhouse_https.port,
        'user': settings.clickhouse_https.user,
        'password': settings.clickhouse_https.password,
        'database': settings.clickhouse_https.database
    }

def _create_clickhouse_connection():
    """Create ClickHouse database connection."""
    config = _build_clickhouse_config()
    base_db = ClickHouseDatabase(**config)
    return ClickHouseQueryInterceptor(base_db)

async def _fetch_corpus_data(db, table_name: str) -> list:
    """Fetch corpus data from ClickHouse table."""
    query = f"SELECT workload_type, prompt, response FROM {table_name}"
    results = await db.execute_query(query)
    logger.info(f"Successfully loaded {len(results)} records from corpus table {table_name}")
    return results

def _process_corpus_results(results: list) -> dict:
    """Process corpus results into dictionary format."""
    corpus = defaultdict(list)
    for row in results:
        corpus[row['workload_type']].append((row['prompt'], row['response']))
    return dict(corpus)

async def _execute_corpus_fetch(table_name: str) -> dict:
    """Execute corpus fetch with connection management."""
    db = _create_clickhouse_connection()
    try:
        results = await _fetch_corpus_data(db, table_name)
        return _process_corpus_results(results)
    finally:
        await db.disconnect()

async def get_corpus_from_clickhouse(table_name: str) -> dict:
    """Fetches the content corpus from a specified ClickHouse table."""
    try:
        return await _execute_corpus_fetch(table_name)
    except Exception as e:
        logger.exception(f"Failed to load corpus from ClickHouse table {table_name}")
        raise


def load_corpus_from_file(corpus_id: str) -> dict:
    """Load content corpus from local file."""
    corpus_path = os.path.join("app", "data", "generated", "content_corpuses", corpus_id, "content_corpus.json")
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Content corpus '{corpus_id}' not found.")
    with open(corpus_path, 'r') as f:
        return json.load(f)


def create_output_directory(job_id: str, subdir: str) -> str:
    """Create output directory for job results."""
    output_dir = os.path.join("app", "data", "generated", subdir, job_id)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_job_result_to_file(output_dir: str, filename: str, data: Any) -> str:
    """Save job result data to file."""
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    return output_path


async def validate_job_params(job_id: str, api_key_required: bool = True) -> bool:
    """Validates job parameters and API availability."""
    if api_key_required and not settings.llm_configs['default'].api_key:
        await update_job_status(job_id, "failed", error="GEMINI_API_KEY not set")
        return False
    return True


async def finalize_job_completion(job_id: str, result_path: str, summary: Dict[str, Any]) -> None:
    """Finalize job completion with results."""
    await job_store.update(
        job_id, "completed",
        finished_at=time.time(),
        result_path=result_path,
        summary=summary
    )


def _normalize_sample_format(sample):
    """Normalize sample to consistent format."""
    actual_sample = sample
    if isinstance(actual_sample, list) and len(actual_sample) == 1 and isinstance(actual_sample[0], tuple):
        actual_sample = actual_sample[0]
    return actual_sample


def _create_corpus_record(w_type: str, prompt_text: str, response_text: str, timestamp) -> ContentCorpus:
    """Create ContentCorpus record from validated data."""
    return ContentCorpus(
        workload_type=w_type,
        prompt=prompt_text,
        response=response_text,
        record_id=uuid.uuid4(),
        created_at=timestamp
    )


def _process_sample_record(w_type: str, sample, timestamp):
    """Process a single sample record efficiently."""
    actual_sample = _normalize_sample_format(sample)
    if isinstance(actual_sample, (list, tuple)) and len(actual_sample) == 2:
        prompt_text, response_text = actual_sample
        return _create_corpus_record(w_type, prompt_text, response_text, timestamp)
    logger.warning(f"Skipping malformed sample for workload '{w_type}': {sample}")
    return None


async def _insert_record_batch(db, table_name: str, records):
    """Insert a batch of records efficiently."""
    if not records:
        return
    record_data = [list(record.model_dump().values()) for record in records]
    field_names = list(ContentCorpus.model_fields.keys())
    await db.insert_data(table_name, record_data, field_names)


def _save_corpus_to_file(corpus: dict, job_id: str) -> None:
    """Save corpus to file if job_id is provided."""
    if job_id:
        output_dir = create_output_directory(job_id, "content_corpuses")
        save_job_result_to_file(output_dir, "content_corpus.json", corpus)

async def _setup_corpus_table(db, table_name: str) -> None:
    """Setup ClickHouse table schema."""
    table_schema = get_content_corpus_schema(table_name)
    await db.command(table_schema)

async def _execute_corpus_save(corpus: dict, table_name: str) -> None:
    """Execute corpus save with connection management."""
    db = _create_clickhouse_connection()
    try:
        await _setup_corpus_table(db, table_name)
        await _process_corpus_records(db, table_name, corpus)
        logger.info(f"Successfully saved corpus to ClickHouse table: {table_name}")
    finally:
        await db.disconnect()

async def save_corpus_to_clickhouse(corpus: dict, table_name: str, job_id: str = None):
    """Saves the generated content corpus to a specified ClickHouse table."""
    _save_corpus_to_file(corpus, job_id)
    try:
        await _execute_corpus_save(corpus, table_name)
    except Exception as e:
        logger.exception(f"Failed to save corpus to ClickHouse table {table_name}")
        raise


def _calculate_optimal_batch_size(corpus: dict) -> int:
    """Calculate optimal batch size for corpus processing."""
    total_samples = sum(len(samples) for samples in corpus.values())
    return min(1000, max(100, total_samples // 10))


async def _process_batch_when_full(db, table_name: str, records: list, batch_size: int) -> list:
    """Process batch when it reaches capacity."""
    if len(records) >= batch_size:
        await _insert_record_batch(db, table_name, records)
        return []
    return records


async def _initialize_batch_processing(corpus: dict) -> tuple:
    """Initialize batch processing parameters."""
    records = []
    batch_timestamp = pd.Timestamp.now().to_pydatetime()
    batch_size = _calculate_optimal_batch_size(corpus)
    return records, batch_timestamp, batch_size

async def _process_sample_collection(db, table_name: str, w_type: str, samples: list, 
                                   batch_timestamp, batch_size: int, records: list) -> list:
    """Process all samples for a workload type."""
    for sample in samples:
        processed_record = _process_sample_record(w_type, sample, batch_timestamp)
        if processed_record:
            records.append(processed_record)
        records = await _process_batch_when_full(db, table_name, records, batch_size)
    return records

async def _process_corpus_records(db, table_name: str, corpus: dict):
    """Process and insert corpus records in batches."""
    records, batch_timestamp, batch_size = await _initialize_batch_processing(corpus)
    for w_type, samples in corpus.items():
        records = await _process_sample_collection(db, table_name, w_type, samples, batch_timestamp, batch_size, records)
    if records:
        await _insert_record_batch(db, table_name, records)