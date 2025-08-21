"""
Data ingestion methods for synthetic data
"""

import asyncio
import json
import uuid
from collections import namedtuple
from datetime import UTC, datetime
from typing import Dict, List, Optional


def _build_table_schema(table_name: str) -> str:
    """Build ClickHouse table schema"""
    return f"""
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


async def create_destination_table(
    table_name: str, get_clickhouse_client
) -> None:
    """Create ClickHouse table for synthetic data"""
    create_query = _build_table_schema(table_name)
    async with get_clickhouse_client() as client:
        await client.execute(create_query)


async def ingest_batch_to_clickhouse(
    table_name: str, batch: List[Dict], get_clickhouse_client
):
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


def _extract_core_record_fields(record: Dict) -> List:
    """Extract core record fields"""
    return [
        record["event_id"], record["trace_id"], record["span_id"],
        record["parent_span_id"], record["timestamp_utc"]
    ]


def _extract_data_record_fields(record: Dict) -> List:
    """Extract data record fields"""
    return [
        record["workload_type"],
        record["agent_type"],
        record["tool_invocations"],
        record["request_payload"]
    ]


def _extract_payload_record_fields(record: Dict) -> List:
    """Extract payload record fields"""
    return [
        record["response_payload"],
        record["metrics"],
        record["corpus_reference_id"]
    ]


def _extract_record_values(record: Dict) -> List:
    """Extract values from a single record"""
    core_fields = _extract_core_record_fields(record)
    data_fields = _extract_data_record_fields(record)
    payload_fields = _extract_payload_record_fields(record)
    return core_fields + data_fields + payload_fields


async def _execute_batch_insertion(
    client, table_name: str, values: List[List]
) -> None:
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


def _generate_table_name(table_name: Optional[str]) -> str:
    """Generate table name if not provided"""
    if table_name:
        return table_name
    return f"synthetic_data_{uuid.uuid4().hex}"


async def _execute_table_operations(
    table_name: str, records: List[Dict], create_table_fn, ingest_fn
) -> None:
    """Execute table creation and ingestion operations"""
    if create_table_fn:
        await create_table_fn(table_name)
    if ingest_fn:
        await ingest_fn(table_name, records)


def _build_ingestion_result(records: List[Dict], table_name: str) -> Dict:
    """Build ingestion result dictionary"""
    return {
        "records_ingested": len(records),
        "batches_processed": 1,
        "table_name": table_name
    }


async def ingest_batch(records: List[Dict], table_name: str = None, batch_size: int = 100, 
                      create_table_fn=None, ingest_fn=None) -> Dict:
    """Ingest batch of records to ClickHouse"""
    final_table_name = _generate_table_name(table_name)
    await _execute_table_operations(
        final_table_name, records, create_table_fn, ingest_fn
    )
    return _build_ingestion_result(records, final_table_name)


def _create_ingestion_metrics() -> namedtuple:
    """Create ingestion metrics namedtuple"""
    return namedtuple('IngestionMetrics', ['records_processed', 'backpressure_events'])


def _initialize_stream_state() -> Dict:
    """Initialize streaming state variables"""
    return {
        "records_processed": 0,
        "backpressure_events": 0,
        "buffer": []
    }


async def _handle_backpressure(
    buffer: List, max_buffer_size: int, flush_interval_ms: int
) -> int:
    """Handle backpressure when buffer is full"""
    if len(buffer) < max_buffer_size:
        return 0
    await asyncio.sleep(flush_interval_ms / 1000)
    buffer.clear()
    return 1


async def _process_stream_record(
    state: Dict, record, max_buffer_size: int, flush_interval_ms: int
) -> None:
    """Process a single stream record"""
    state["buffer"].append(record)
    state["records_processed"] += 1
    backpressure_event = await _handle_backpressure(
        state["buffer"], max_buffer_size, flush_interval_ms
    )
    state["backpressure_events"] += backpressure_event


async def ingest_stream(
    stream, max_buffer_size: int = 500, flush_interval_ms: int = 100
):
    """Ingest streaming data with backpressure handling"""
    IngestionMetrics = _create_ingestion_metrics()
    state = _initialize_stream_state()
    
    async for record in stream:
        await _process_stream_record(
            state, record, max_buffer_size, flush_interval_ms
        )
    
    return IngestionMetrics(
        records_processed=state["records_processed"], 
        backpressure_events=state["backpressure_events"]
    )


async def _attempt_ingestion(records: List[Dict], ingest_batch_fn) -> Dict:
    """Attempt single ingestion operation"""
    if ingest_batch_fn:
        return await ingest_batch_fn(records)
    return {}


def _build_success_result(
    retry_count: int, result: Dict, records: List[Dict]
) -> Dict:
    """Build successful ingestion result"""
    return {
        "success": True, "retry_count": retry_count,
        "records_ingested": result.get("records_ingested", len(records)),
        "failed_records": 0
    }


def _build_failure_result(
    retry_count: int, records: List[Dict], error: Exception
) -> Dict:
    """Build failed ingestion result"""
    return {
        "success": False, "retry_count": retry_count,
        "records_ingested": 0, "failed_records": len(records),
        "error": str(error)
    }


async def _handle_retry_exception(
    retry_count: int, max_retries: int, records: List[Dict], 
    error: Exception, retry_delay_ms: int
) -> Optional[Dict]:
    """Handle exception during retry attempt"""
    if retry_count >= max_retries:
        return _build_failure_result(retry_count, records, error)
    await asyncio.sleep(retry_delay_ms / 1000)
    return None


async def ingest_with_retry(
    records: List[Dict], max_retries: int = 3, retry_delay_ms: int = 100, 
    ingest_batch_fn=None
) -> Dict:
    """Ingest with retry logic"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            result = await _attempt_ingestion(records, ingest_batch_fn)
            return _build_success_result(retry_count, result, records)
        except Exception as e:
            retry_count += 1
            failure_result = await _handle_retry_exception(
                retry_count, max_retries, records, e, retry_delay_ms
            )
            if failure_result:
                return failure_result


def _process_record_for_dedup(
    record: Dict, dedup_key: str, seen_keys: set, deduplicated: List[Dict]
) -> int:
    """Process single record for deduplication"""
    key_value = record.get(dedup_key)
    if key_value in seen_keys:
        return 1
    seen_keys.add(key_value)
    deduplicated.append(record)
    return 0


def _deduplicate_records(records: List[Dict], dedup_key: str) -> tuple[List[Dict], int]:
    """Deduplicate records based on key"""
    seen_keys = set()
    deduplicated = []
    duplicates_removed = 0
    
    for record in records:
        duplicates_removed += _process_record_for_dedup(
            record, dedup_key, seen_keys, deduplicated
        )
    
    return deduplicated, duplicates_removed


async def _execute_dedup_ingestion(deduplicated: List[Dict], ingest_batch_fn) -> Dict:
    """Execute ingestion after deduplication"""
    if ingest_batch_fn:
        return await ingest_batch_fn(deduplicated)
    return {"records_ingested": len(deduplicated)}


async def ingest_with_deduplication(
    records: List[Dict], dedup_key: str = "id", ingest_batch_fn=None
) -> Dict:
    """Ingest with deduplication"""
    deduplicated, duplicates_removed = _deduplicate_records(records, dedup_key)
    await _execute_dedup_ingestion(deduplicated, ingest_batch_fn)
    return {
        "records_ingested": len(deduplicated),
        "duplicates_removed": duplicates_removed
    }


def _update_basic_metrics(metrics, batch_size: int) -> None:
    """Update basic batch and record metrics"""
    metrics.total_records += batch_size
    metrics.total_batches += 1


def _update_latency_bounds(metrics, latency_ms: float) -> None:
    """Update latency min/max bounds"""
    if latency_ms > metrics.max_latency_ms:
        metrics.max_latency_ms = latency_ms
    if latency_ms < metrics.min_latency_ms:
        metrics.min_latency_ms = latency_ms


def _update_average_latency(metrics, latency_ms: float) -> None:
    """Update running average latency"""
    total_latency = metrics.avg_latency_ms * (metrics.total_batches - 1) + latency_ms
    metrics.avg_latency_ms = total_latency / metrics.total_batches


async def track_ingestion(
    metrics, batch_size: int, latency_ms: float
) -> None:
    """Track ingestion metrics"""
    _update_basic_metrics(metrics, batch_size)
    _update_latency_bounds(metrics, latency_ms)
    _update_average_latency(metrics, latency_ms)


def _transform_records(records: List[Dict], transform_fn) -> List[Dict]:
    """Transform records using provided function"""
    return [transform_fn(record) for record in records]


async def _execute_transform_ingestion(
    transformed_records: List[Dict], ingest_batch_fn
) -> Dict:
    """Execute ingestion for transformed records"""
    if ingest_batch_fn:
        return await ingest_batch_fn(transformed_records)
    return {"records_ingested": len(transformed_records)}


def _build_transform_result(
    result: Dict, transformed_records: List[Dict]
) -> Dict:
    """Build transformation result"""
    return {
        "records_ingested": result["records_ingested"],
        "transformed_records": transformed_records
    }


async def ingest_with_transform(
    records: List[Dict], transform_fn, ingest_batch_fn=None
) -> Dict:
    """Ingest with data transformation"""
    transformed_records = _transform_records(records, transform_fn)
    result = await _execute_transform_ingestion(
        transformed_records, ingest_batch_fn
    )
    return _build_transform_result(result, transformed_records)


def _build_progress_data(new_processed: int, total_records: int) -> Dict:
    """Build progress callback data"""
    return {
        "percentage": (new_processed / total_records) * 100,
        "processed": new_processed,
        "total": total_records
    }


async def _process_batch_with_callback(
    batch: List[Dict], processed: int, total_records: int,
    progress_callback, ingest_batch_fn
) -> int:
    """Process batch and call progress callback"""
    if ingest_batch_fn:
        await ingest_batch_fn(batch)
    new_processed = processed + len(batch)
    
    if progress_callback:
        progress_data = _build_progress_data(new_processed, total_records)
        await progress_callback(progress_data)
    return new_processed


async def ingest_with_progress(
    records: List[Dict], batch_size: int = 100, 
    progress_callback=None, ingest_batch_fn=None
) -> None:
    """Ingest with progress tracking"""
    total_records = len(records)
    processed = 0
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        processed = await _process_batch_with_callback(
            batch, processed, total_records, progress_callback, ingest_batch_fn
        )