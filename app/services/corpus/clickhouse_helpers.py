"""ClickHouse operation helpers for function decomposition.

Decomposes large ClickHouse functions into 8-line focused helpers.
"""

from typing import Dict, Any, Optional, Tuple
from app.logging_config import central_logger
from .base import ClickHouseOperationError

logger = central_logger


def build_table_size_query(table_name: str) -> str:
    """Build table size query for ClickHouse."""
    return f"""
        SELECT 
            sum(rows) as total_rows,
            sum(bytes_on_disk) as bytes_on_disk,
            sum(data_compressed_bytes) as data_compressed_bytes,
            sum(data_uncompressed_bytes) as data_uncompressed_bytes
        FROM system.parts 
        WHERE table = '{table_name}' AND active = 1
    """


def calculate_compression_ratio(compressed: int, uncompressed: int) -> float:
    """Calculate compression ratio safely."""
    if compressed and uncompressed:
        return uncompressed / compressed
    return 1.0


def process_table_size_row(row: Tuple) -> Dict[str, Any]:
    """Process table size query result row."""
    return {
        "total_rows": row[0] or 0,
        "bytes_on_disk": row[1] or 0,
        "data_compressed_bytes": row[2] or 0,
        "data_uncompressed_bytes": row[3] or 0,
        "compression_ratio": calculate_compression_ratio(row[2], row[3])
    }


def get_empty_table_size_result() -> Dict[str, Any]:
    """Get empty table size result."""
    return {
        "total_rows": 0,
        "bytes_on_disk": 0,
        "data_compressed_bytes": 0,
        "data_uncompressed_bytes": 0,
        "compression_ratio": 1.0
    }


def process_table_size_result(result) -> Dict[str, Any]:
    """Process table size query result."""
    if result and result[0]:
        return process_table_size_row(result[0])
    return get_empty_table_size_result()


def log_table_operation_success(operation: str, table_name: str) -> None:
    """Log successful table operation."""
    central_logger.info(f"{operation} ClickHouse table {table_name}")


def log_table_operation_error(operation: str, table_name: str, error: Exception) -> None:
    """Log table operation error."""
    central_logger.error(f"Failed to {operation.lower()} ClickHouse table {table_name}: {str(error)}")


def create_clickhouse_operation_error(operation: str, error: Exception) -> ClickHouseOperationError:
    """Create ClickHouse operation error."""
    return ClickHouseOperationError(f"Failed to {operation.lower()}: {str(error)}")


def log_schema_error(table_name: str, error: Exception) -> None:
    """Log schema retrieval error."""
    central_logger.error(f"Failed to get schema for table {table_name}: {str(error)}")


def log_table_exists_error(table_name: str, error: Exception) -> None:
    """Log table existence check error."""
    central_logger.error(f"Failed to check table existence {table_name}: {str(error)}")


def build_success_notification_payload(corpus_id: str, table_name: str) -> Dict[str, Any]:
    """Build success notification payload."""
    return {
        "type": "corpus:created", 
        "payload": {
            "corpus_id": corpus_id, 
            "table_name": table_name,
            "status": "AVAILABLE"
        }
    }


def build_error_notification_payload(corpus_id: str, error: Exception) -> Dict[str, Any]:
    """Build error notification payload."""
    return {
        "type": "corpus:error", 
        "payload": {
            "corpus_id": corpus_id, 
            "error": str(error)
        }
    }


def build_table_exists_query(table_name: str) -> str:
    """Build table existence check query."""
    return f"""
        SELECT COUNT(*) FROM system.tables 
        WHERE name = '{table_name}'
    """


def process_table_exists_result(result) -> bool:
    """Process table existence query result."""
    return result[0][0] > 0 if result else False


def build_schema_query(table_name: str) -> str:
    """Build schema query for table columns."""
    return f"""
        SELECT column, type, is_in_primary_key
        FROM system.columns 
        WHERE table = '{table_name}'
        ORDER BY position
    """


def initialize_schema_dict() -> Dict[str, Any]:
    """Initialize empty schema dictionary structure."""
    return {
        "columns": [],
        "primary_key_columns": []
    }


def build_column_info(row: Tuple) -> Dict[str, Any]:
    """Build column information from result row."""
    return {
        "name": row[0],
        "type": row[1],
        "is_primary_key": bool(row[2])
    }


def process_schema_row(schema: Dict, row: Tuple) -> None:
    """Process single schema row and update schema dict."""
    column_info = build_column_info(row)
    schema["columns"].append(column_info)
    if column_info["is_primary_key"]:
        schema["primary_key_columns"].append(column_info["name"])