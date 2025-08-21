"""Data ingestion service for processing and loading data into ClickHouse.

Provides data ingestion capabilities with job management,
following the pattern of other generation services.
"""

import json
import os
from typing import Dict, List, Any
from netra_backend.app.schemas.Generation import DataIngestionParams
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.services.generation_job_manager import (
    update_job_status,
    validate_job_params
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def _convert_params_to_schema(params: dict) -> DataIngestionParams:
    """Convert dict params to DataIngestionParams schema."""
    return DataIngestionParams(**params)


def _validate_data_file(file_path: str) -> bool:
    """Validate that data file exists and is readable."""
    return os.path.exists(file_path) and os.path.isfile(file_path)


def _load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON data from file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


async def _create_table_if_not_exists(client, table_name: str):
    """Create table in ClickHouse if it doesn't exist."""
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id String,
        data String,
        timestamp DateTime DEFAULT now()
    ) ENGINE = MergeTree() ORDER BY timestamp
    """
    await client.execute_query(create_query)


async def _insert_data_to_clickhouse(client, data: List[Dict], table_name: str):
    """Insert data records into ClickHouse table."""
    for record in data:
        insert_query = f"""
        INSERT INTO {table_name} (id, data) VALUES
        """
        record_id = record.get('id', 'unknown')
        record_data = json.dumps(record)
        values = f"('{record_id}', '{record_data}')"
        await client.execute_query(insert_query + values)


async def _execute_data_ingestion(job_id: str, params: dict):
    """Execute data ingestion with proper job tracking."""
    schema_params = _convert_params_to_schema(params)
    await update_job_status(job_id, "running", progress=0)
    
    if not _validate_data_file(schema_params.data_path):
        raise FileNotFoundError(f"Data file not found: {schema_params.data_path}")
    
    data = _load_json_data(schema_params.data_path)
    async with get_clickhouse_client() as client:
        await _create_table_if_not_exists(client, schema_params.table_name)
        await _insert_data_to_clickhouse(client, data, schema_params.table_name)
    
    return {"records_ingested": len(data), "table_name": schema_params.table_name}


async def _handle_ingestion_error(job_id: str, error: Exception):
    """Handle ingestion errors with proper status updates."""
    logger.exception("Error during data ingestion")
    error_message = f"Data ingestion failed: {str(error)}"
    await update_job_status(job_id, "failed", error=error_message)


async def run_data_ingestion_job(job_id: str, params: dict):
    """Main job runner for data ingestion."""
    if not await validate_job_params(job_id, api_key_required=False):
        return
    try:
        result = await _execute_data_ingestion(job_id, params)
        await update_job_status(job_id, "completed", summary=result)
    except Exception as e:
        await _handle_ingestion_error(job_id, e)