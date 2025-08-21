import json
import time
from typing import Any, Dict, List, Tuple

from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from netra_backend.app.logging_config import central_logger


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
    if not _is_json_string(value):
        return value
    return _parse_json_safely(value)

def _is_json_string(value) -> bool:
    """Check if value is a JSON string."""
    return isinstance(value, str) and (value.startswith('{') or value.startswith('['))

def _parse_json_safely(value: str) -> Any:
    """Parse JSON string safely with fallback."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
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
    return _process_all_dict_items(nested_json, items, sep)

def _process_all_dict_items(nested_json: Dict[str, Any], items: Dict[str, Any], sep: str) -> Dict[str, Any]:
    """Process all dictionary items for flattening."""
    for k, v in nested_json.items():
        if isinstance(v, dict):
            _process_nested_dict_item(items, k, v, sep)
        else:
            _process_flat_dict_item(items, k, v)
    return items

def _validate_ingestion_input(records: list[dict]) -> bool:
    """Validate ingestion input and log warnings if invalid."""
    if not records or not isinstance(records, list):
        _log_invalid_input_warning()
        return False
    return True

def _log_invalid_input_warning() -> None:
    """Log warning for invalid input."""
    central_logger.get_logger(__name__).warning("No records provided or format is incorrect. Skipping ingestion.")

def _prepare_flattened_records(records: list[dict]) -> list[dict]:
    """Prepare flattened records from input records."""
    return [_flatten_json_first_level(record[0] if isinstance(record, list) and record else record) for record in records]

def _validate_prepared_data(data_for_insert: list[list]) -> bool:
    """Validate prepared data and log warnings if empty."""
    if not data_for_insert:
        _log_empty_data_warning()
        return False
    return True

def _log_empty_data_warning() -> None:
    """Log warning for empty prepared data."""
    central_logger.get_logger(__name__).warning("Data preparation resulted in no records to insert for this batch.")

async def _execute_data_insertion(client: ClickHouseDatabase, table_name: str, data_for_insert: list[list], ordered_columns: list[str], record_count: int) -> int:
    """Execute the actual data insertion with logging."""
    await client.insert_data(table_name, data_for_insert, column_names=ordered_columns)
    central_logger.get_logger(__name__).info(f"Successfully inserted batch of {record_count} records.")
    return record_count

async def ingest_records(client: ClickHouseDatabase, records: list[dict], table_name: str) -> int:
    """Ingests a list of in-memory records into a specified ClickHouse table using an active client."""
    if not _validate_ingestion_input(records):
        return 0
    _log_ingestion_start(len(records), table_name)
    return await _process_ingestion_workflow(client, records, table_name)

def _log_ingestion_start(record_count: int, table_name: str) -> None:
    """Log ingestion process start."""
    central_logger.get_logger(__name__).info(f"Ingesting batch of {record_count} records into '{table_name}'...")

async def _process_ingestion_workflow(client: ClickHouseDatabase, records: list[dict], table_name: str) -> int:
    """Process the ingestion workflow."""
    flattened_records = _prepare_flattened_records(records)
    ordered_columns, data_for_insert = prepare_data_for_insert(flattened_records)
    if not _validate_prepared_data(data_for_insert):
        return 0
    return await _execute_data_insertion(client, table_name, data_for_insert, ordered_columns, len(flattened_records))