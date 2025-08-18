import json
import time
from typing import Dict, Any, List, Tuple
from app.logging_config import central_logger
from app.db.clickhouse_base import ClickHouseDatabase

def _extract_all_column_names(flattened_records: list[dict]) -> list[str]:
    """Extract and order all unique column names from records."""
    all_column_names = set()
    for record in flattened_records:
        all_column_names.update(record.keys())
    return sorted(list(all_column_names))

def _handle_list_value(value) -> Any:
    """Handle list value transformation."""
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return value

def _handle_json_string_value(value) -> Any:
    """Handle JSON string value transformation."""
    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return value

def _transform_value(value) -> Any:
    """Apply auto-corrections to individual values."""
    value = _handle_list_value(value)
    value = _handle_json_string_value(value)
    return value

def _process_record_to_row(record: dict, ordered_columns: list[str]) -> list:
    """Process a single record into a row with ordered columns."""
    row = []
    for col in ordered_columns:
        value = record.get(col)
        transformed_value = _transform_value(value)
        row.append(transformed_value)
    return row

def _build_data_rows(flattened_records: list[dict], ordered_columns: list[str]) -> list[list]:
    """Build all data rows from flattened records."""
    data_for_insert = []
    for record in flattened_records:
        row = _process_record_to_row(record, ordered_columns)
        data_for_insert.append(row)
    return data_for_insert

def prepare_data_for_insert(flattened_records: list[dict]) -> tuple[list[str], list[list]]:
    """Prepares a list of dictionaries for database insertion by ensuring consistent column order and applying auto-corrections."""
    if not flattened_records:
        return [], []
    ordered_columns = _extract_all_column_names(flattened_records)
    data_for_insert = _build_data_rows(flattened_records, ordered_columns)
    return ordered_columns, data_for_insert

def _process_nested_dict_item(items: Dict[str, Any], key: str, value: dict, sep: str) -> None:
    """Process nested dictionary items and add to items dict."""
    for sub_k, sub_v in value.items():
        items[f"{key}{sep}{sub_k}"] = sub_v

def _process_flat_dict_item(items: Dict[str, Any], key: str, value: Any) -> None:
    """Process flat dictionary items and add to items dict."""
    items[key] = value

def _init_flattening_result(nested_json: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize flattening result with validation."""
    if not isinstance(nested_json, dict):
        return {}
    return {}

def _flatten_json_first_level(nested_json: Dict[str, Any], sep: str = '_') -> Dict[str, Any]:
    """Flattens the first level of a nested dictionary."""
    items = _init_flattening_result(nested_json)
    if not items and not isinstance(nested_json, dict):
        return items
    for k, v in nested_json.items():
        if isinstance(v, dict):
            _process_nested_dict_item(items, k, v, sep)
        else:
            _process_flat_dict_item(items, k, v)
    return items

def _validate_ingestion_input(records: list[dict]) -> bool:
    """Validate ingestion input and log warnings if invalid."""
    if not records or not isinstance(records, list):
        central_logger.get_logger(__name__).warning("No records provided or format is incorrect. Skipping ingestion.")
        return False
    return True

def _prepare_flattened_records(records: list[dict]) -> list[dict]:
    """Prepare flattened records from input records."""
    return [_flatten_json_first_level(record[0] if isinstance(record, list) and record else record) for record in records]

def _validate_prepared_data(data_for_insert: list[list]) -> bool:
    """Validate prepared data and log warnings if empty."""
    if not data_for_insert:
        central_logger.get_logger(__name__).warning("Data preparation resulted in no records to insert for this batch.")
        return False
    return True

async def _execute_data_insertion(client: ClickHouseDatabase, table_name: str, data_for_insert: list[list], ordered_columns: list[str], record_count: int) -> int:
    """Execute the actual data insertion with logging."""
    await client.insert_data(table_name, data_for_insert, column_names=ordered_columns)
    central_logger.get_logger(__name__).info(f"Successfully inserted batch of {record_count} records.")
    return record_count

async def ingest_records(client: ClickHouseDatabase, records: list[dict], table_name: str) -> int:
    """Ingests a list of in-memory records into a specified ClickHouse table using an active client."""
    if not _validate_ingestion_input(records):
        return 0
    central_logger.get_logger(__name__).info(f"Ingesting batch of {len(records)} records into '{table_name}'...")
    flattened_records = _prepare_flattened_records(records)
    ordered_columns, data_for_insert = prepare_data_for_insert(flattened_records)
    if not _validate_prepared_data(data_for_insert):
        return 0
    return await _execute_data_insertion(client, table_name, data_for_insert, ordered_columns, len(flattened_records))