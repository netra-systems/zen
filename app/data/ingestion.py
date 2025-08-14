import json
import time
from typing import Dict, Any, List, Tuple
from app.logging_config import central_logger
from app.db.clickhouse_base import ClickHouseDatabase

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

def _flatten_json_first_level(nested_json: Dict[str, Any], sep: str = '_') -> Dict[str, Any]:
    """Flattens the first level of a nested dictionary."""
    items: Dict[str, Any] = {}
    if not isinstance(nested_json, dict):
        return {}
    for k, v in nested_json.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                items[f"{k}{sep}{sub_k}"] = sub_v
        else:
            items[k] = v
    return items

async def ingest_records(client: ClickHouseDatabase, records: list[dict], table_name: str) -> int:
    """
    Ingests a list of in-memory records into a specified ClickHouse table using an active client.
    """
    if not records or not isinstance(records, list):
        central_logger.get_logger(__name__).warning("No records provided or format is incorrect. Skipping ingestion.")
        return 0

    central_logger.get_logger(__name__).info(f"Ingesting batch of {len(records)} records into '{table_name}'...")
    
    flattened_records = [_flatten_json_first_level(record[0] if isinstance(record, list) and record else record) for record in records]
    ordered_columns, data_for_insert = prepare_data_for_insert(flattened_records)

    if not data_for_insert:
        logging.warning("Data preparation resulted in no records to insert for this batch.")
        return 0

    await client.insert_data(table_name, data_for_insert, column_names=ordered_columns)
    central_logger.get_logger(__name__).info(f"Successfully inserted batch of {len(flattened_records)} records.")
    return len(flattened_records)