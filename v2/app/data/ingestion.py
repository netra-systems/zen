import json
import time
import logging
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import LLM_EVENTS_TABLE_SCHEMA

def prepare_data_for_insert(flattened_records: list[dict]) -> tuple[list[str], list[list]]:
    """
    Prepares a list of dictionaries for database insertion by ensuring consistent
    column order and applying auto-corrections to the data.
    """
    if not flattened_records:
        return [], []

    all_column_names = set()
    for record in flattened_records:
        all_column_names.update(record.keys())
    ordered_columns = sorted(list(all_column_names))

    data_for_insert = []
    for record in flattened_records:
        row = []
        for col in ordered_columns:
            value = record.get(col)
            if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
                value = value[0]
            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            row.append(value)
        data_for_insert.append(row)

    return ordered_columns, data_for_insert

def _flatten_json_first_level(nested_json, sep='_'):
    """Flattens the first level of a nested dictionary."""
    items = {}
    if not isinstance(nested_json, dict):
        return {}
    for k, v in nested_json.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                items[f"{k}{sep}{sub_k}"] = sub_v
        else:
            items[k] = v
    return items

def ingest_records(records: list[dict]) -> dict:
    """
    Ingests a list of in-memory records into ClickHouse.
    This is the primary, most efficient ingestion method.
    """
    if not records or not isinstance(records, list):
        return {"status": "failed", "message": "No records provided or format is incorrect."}

    logging.info(f"Starting in-memory data ingestion for {len(records)} records...")
    start_time = time.time()

    with get_clickhouse_client() as client:
        client.command(LLM_EVENTS_TABLE_SCHEMA)
        
        # The check for record[0] is specific to the current log generation format.
        # It might need to be generalized if the source format changes.
        flattened_records = [_flatten_json_first_level(record[0] if isinstance(record, list) and record else record) for record in records]
        ordered_columns, data_for_insert = prepare_data_for_insert(flattened_records)

        if not data_for_insert:
            return {"status": "failed", "message": "Data preparation resulted in no records to insert."}

        client.insert_data('JSON_HYBRID_EVENTS4', data_for_insert, column_names=ordered_columns)
        
        end_time = time.time()
        summary = {
            "status": "completed",
            "total_records_inserted": len(flattened_records),
            "time_taken_seconds": f"{end_time - start_time:.2f}"
        }
        logging.info(f"In-memory data ingestion completed: {summary}")
        return summary

def ingest_data_from_file(file_path: str) -> dict:
    """
    Reads data from a JSON file and ingests it into ClickHouse using the
    primary in-memory ingestion function.
    """
    logging.info(f"Starting data ingestion process from {file_path}...")
    try:
        with open(file_path, 'r') as f:
            records = json.load(f)
        return ingest_records(records)
    except FileNotFoundError:
        logging.error(f"Ingestion failed: File not found at {file_path}")
        return {"status": "failed", "message": f"File not found: {file_path}"}
    except json.JSONDecodeError:
        logging.error(f"Ingestion failed: Could not decode JSON from {file_path}")
        return {"status": "failed", "message": f"Invalid JSON in file: {file_path}"}
