"""
Data ingestion methods for synthetic data
"""

import json
import uuid
import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Optional
from collections import namedtuple


async def create_destination_table(table_name: str, get_clickhouse_client):
    """Create ClickHouse table for synthetic data"""
    create_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            event_id UUID,
            trace_id UUID,
            span_id UUID,
            parent_span_id Nullable(UUID),
            timestamp_utc DateTime64(3),
            workload_type String,
            agent_type String,
            tool_invocations Array(String),
            request_payload String,
            response_payload String,
            metrics String,
            corpus_reference_id Nullable(UUID)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp_utc)
        ORDER BY (timestamp_utc, trace_id)
    """
    
    async with get_clickhouse_client() as client:
        await client.execute(create_query)


async def ingest_batch_to_clickhouse(table_name: str, batch: List[Dict], get_clickhouse_client):
    """Ingest batch of records to ClickHouse"""
    if not batch:
        return
    
    _prepare_batch_for_insertion(batch)
    async with get_clickhouse_client() as client:
        values = _extract_values_from_batch(batch)
        await _execute_batch_insertion(client, table_name, values)


def _prepare_batch_for_insertion(batch: List[Dict]) -> None:
    """Convert complex fields to JSON strings"""
    for record in batch:
        _convert_record_payloads_to_json(record)


def _convert_record_payloads_to_json(record: Dict) -> None:
    """Convert record payloads to JSON strings"""
    record["request_payload"] = json.dumps(record["request_payload"])
    record["response_payload"] = json.dumps(record["response_payload"])
    record["metrics"] = json.dumps(record["metrics"])


def _extract_values_from_batch(batch: List[Dict]) -> List[List]:
    """Extract values from batch for insertion"""
    values = []
    for record in batch:
        values.append(_extract_record_values(record))
    return values


def _extract_record_values(record: Dict) -> List:
    """Extract values from a single record"""
    return [
        record["event_id"],
        record["trace_id"],
        record["span_id"],
        record["parent_span_id"],
        record["timestamp_utc"],
        record["workload_type"],
        record["agent_type"],
        record["tool_invocations"],
        record["request_payload"],
        record["response_payload"],
        record["metrics"],
        record["corpus_reference_id"]
    ]


async def _execute_batch_insertion(client, table_name: str, values: List[List]) -> None:
    """Execute batch insertion into ClickHouse"""
    insert_query = _build_insert_query(table_name)
    await client.execute(insert_query, values)


def _build_insert_query(table_name: str) -> str:
    """Build INSERT query for ClickHouse"""
    return f"""INSERT INTO {table_name} 
    (event_id, trace_id, span_id, parent_span_id, timestamp_utc, 
     workload_type, agent_type, tool_invocations, request_payload, 
     response_payload, metrics, corpus_reference_id)
    VALUES"""


async def ingest_batch(records: List[Dict], table_name: str = None, batch_size: int = 100, 
                      create_table_fn=None, ingest_fn=None) -> Dict:
    """Ingest batch of records to ClickHouse"""
    if not table_name:
        table_name = f"synthetic_data_{uuid.uuid4().hex}"
    
    if create_table_fn:
        await create_table_fn(table_name)
    if ingest_fn:
        await ingest_fn(table_name, records)
    
    return {
        "records_ingested": len(records),
        "batches_processed": 1,
        "table_name": table_name
    }


async def ingest_stream(stream, max_buffer_size: int = 500, flush_interval_ms: int = 100):
    """Ingest streaming data with backpressure handling"""
    IngestionMetrics = namedtuple('IngestionMetrics', ['records_processed', 'backpressure_events'])
    
    records_processed = 0
    backpressure_events = 0
    buffer = []
    
    async for record in stream:
        buffer.append(record)
        records_processed += 1
        
        # Handle backpressure
        if len(buffer) >= max_buffer_size:
            backpressure_events += 1
            await asyncio.sleep(flush_interval_ms / 1000)  # Convert to seconds
            buffer.clear()
    
    return IngestionMetrics(records_processed=records_processed, backpressure_events=backpressure_events)


async def ingest_with_retry(records: List[Dict], max_retries: int = 3, retry_delay_ms: int = 100, 
                           ingest_batch_fn=None) -> Dict:
    """Ingest with retry logic"""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            result = await ingest_batch_fn(records) if ingest_batch_fn else {}
            return {
                "success": True,
                "retry_count": retry_count,
                "records_ingested": result.get("records_ingested", len(records)),
                "failed_records": 0
            }
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                return {
                    "success": False,
                    "retry_count": retry_count,
                    "records_ingested": 0,
                    "failed_records": len(records),
                    "error": str(e)
                }
            await asyncio.sleep(retry_delay_ms / 1000)


async def ingest_with_deduplication(records: List[Dict], dedup_key: str = "id", 
                                   ingest_batch_fn=None) -> Dict:
    """Ingest with deduplication"""
    seen_keys = set()
    deduplicated = []
    duplicates_removed = 0
    
    for record in records:
        key_value = record.get(dedup_key)
        if key_value not in seen_keys:
            seen_keys.add(key_value)
            deduplicated.append(record)
        else:
            duplicates_removed += 1
    
    result = await ingest_batch_fn(deduplicated) if ingest_batch_fn else {"records_ingested": len(deduplicated)}
    return {
        "records_ingested": len(deduplicated),
        "duplicates_removed": duplicates_removed
    }


async def track_ingestion(metrics, batch_size: int, latency_ms: float):
    """Track ingestion metrics"""
    metrics.total_records += batch_size
    metrics.total_batches += 1
    
    if latency_ms > metrics.max_latency_ms:
        metrics.max_latency_ms = latency_ms
    if latency_ms < metrics.min_latency_ms:
        metrics.min_latency_ms = latency_ms
    
    # Calculate running average
    total_latency = metrics.avg_latency_ms * (metrics.total_batches - 1) + latency_ms
    metrics.avg_latency_ms = total_latency / metrics.total_batches


async def ingest_with_transform(records: List[Dict], transform_fn, ingest_batch_fn=None) -> Dict:
    """Ingest with data transformation"""
    transformed_records = [transform_fn(record) for record in records]
    result = await ingest_batch_fn(transformed_records) if ingest_batch_fn else {"records_ingested": len(transformed_records)}
    
    return {
        "records_ingested": result["records_ingested"],
        "transformed_records": transformed_records
    }


async def ingest_with_progress(records: List[Dict], batch_size: int = 100, 
                              progress_callback=None, ingest_batch_fn=None):
    """Ingest with progress tracking"""
    total_records = len(records)
    processed = 0
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        if ingest_batch_fn:
            await ingest_batch_fn(batch)
        processed += len(batch)
        
        if progress_callback:
            await progress_callback({
                "percentage": (processed / total_records) * 100,
                "processed": processed,
                "total": total_records
            })