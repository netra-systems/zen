"""Job management utilities for generation services.

Provides centralized job status management, progress tracking,
and corpus data access for all generation services.
"""

import os
import json
import time
import uuid
from collections import defaultdict
from typing import Dict, Any

import pandas as pd

from app.config import settings
from app.schemas import ContentCorpus
from app.db.clickhouse_base import ClickHouseDatabase
from app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from app.db.models_clickhouse import get_content_corpus_schema
from app.services.job_store import job_store
from app.ws_manager import manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def update_job_status(job_id: str, status: str, **kwargs):
    """Updates the status and other attributes of a generation job and sends a WebSocket message."""
    await job_store.update(job_id, status, **kwargs)
    await manager.broadcast_to_job(job_id, {"job_id": job_id, "status": status, **kwargs})


async def get_corpus_from_clickhouse(table_name: str) -> dict:
    """Fetches the content corpus from a specified ClickHouse table."""
    db = None
    try:
        base_db = ClickHouseDatabase(
            host=settings.clickhouse_https.host,
            port=settings.clickhouse_https.port,
            user=settings.clickhouse_https.user,
            password=settings.clickhouse_https.password,
            database=settings.clickhouse_https.database
        )
        db = ClickHouseQueryInterceptor(base_db)
        query = f"SELECT workload_type, prompt, response FROM {table_name}"
        results = await db.execute_query(query)
        corpus = defaultdict(list)
        for row in results:
            corpus[row['workload_type']].append((row['prompt'], row['response']))
        logger.info(f"Successfully loaded {len(results)} records from corpus table {table_name}")
        return dict(corpus)
    except Exception as e:
        logger.exception(f"Failed to load corpus from ClickHouse table {table_name}")
        raise
    finally:
        if 'db' in locals() and db:
            await db.disconnect()


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


def _process_sample_record(w_type: str, sample, timestamp):
    """Process a single sample record efficiently."""
    actual_sample = sample
    if isinstance(actual_sample, list) and len(actual_sample) == 1 and isinstance(actual_sample[0], tuple):
        actual_sample = actual_sample[0]
    if isinstance(actual_sample, (list, tuple)) and len(actual_sample) == 2:
        prompt_text, response_text = actual_sample
        return ContentCorpus(
            workload_type=w_type,
            prompt=prompt_text,
            response=response_text,
            record_id=uuid.uuid4(),
            created_at=timestamp
        )
    logger.warning(f"Skipping malformed sample for workload '{w_type}': {sample}")
    return None


async def _insert_record_batch(db, table_name: str, records):
    """Insert a batch of records efficiently."""
    if not records:
        return
    record_data = [list(record.model_dump().values()) for record in records]
    field_names = list(ContentCorpus.model_fields.keys())
    await db.insert_data(table_name, record_data, field_names)


async def save_corpus_to_clickhouse(corpus: dict, table_name: str, job_id: str = None):
    """Saves the generated content corpus to a specified ClickHouse table."""
    if job_id:
        output_dir = create_output_directory(job_id, "content_corpuses")
        save_job_result_to_file(output_dir, "content_corpus.json", corpus)
    db = None
    try:
        base_db = ClickHouseDatabase(
            host=settings.clickhouse_https.host,
            port=settings.clickhouse_https.port,
            user=settings.clickhouse_https.user,
            password=settings.clickhouse_https.password,
            database=settings.clickhouse_https.database
        )
        db = ClickHouseQueryInterceptor(base_db)
        table_schema = get_content_corpus_schema(table_name)
        await db.command(table_schema)
        await _process_corpus_records(db, table_name, corpus)
        logger.info(f"Successfully saved corpus to ClickHouse table: {table_name}")
    except Exception as e:
        logger.exception(f"Failed to save corpus to ClickHouse table {table_name}")
        raise
    finally:
        if 'db' in locals() and db:
            await db.disconnect()


async def _process_corpus_records(db, table_name: str, corpus: dict):
    """Process and insert corpus records in batches."""
    records = []
    batch_timestamp = pd.Timestamp.now().to_pydatetime()
    total_samples = sum(len(samples) for samples in corpus.values())
    batch_size = min(1000, max(100, total_samples // 10))
    for w_type, samples in corpus.items():
        for sample in samples:
            processed_record = _process_sample_record(w_type, sample, batch_timestamp)
            if processed_record:
                records.append(processed_record)
            if len(records) >= batch_size:
                await _insert_record_batch(db, table_name, records)
                records = []
    if records:
        await _insert_record_batch(db, table_name, records)