"""ClickHouse operations manager with compensation support.

Manages ClickHouse operations and provides compensation mechanisms
for distributed transaction rollback.
"""

from datetime import datetime
from typing import Dict, List

from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ClickHouseOperationManager:
    """Manages ClickHouse operations with compensation."""
    
    def __init__(self):
        """Initialize ClickHouse operation manager."""
        self.operation_records: Dict[str, List[Dict]] = {}
    
    async def record_insert(self, operation_id: str, table: str, data: Dict) -> None:
        """Record ClickHouse insert for potential compensation."""
        self._ensure_records_exist(operation_id)
        record = self._create_insert_record(table, data)
        self.operation_records[operation_id].append(record)
        logger.debug(f"Recorded ClickHouse insert: {operation_id}")
    
    def _ensure_records_exist(self, operation_id: str) -> None:
        """Ensure operation records list exists."""
        if operation_id not in self.operation_records:
            self.operation_records[operation_id] = []
    
    def _create_insert_record(self, table: str, data: Dict) -> Dict:
        """Create insert record for compensation."""
        return {
            'action': 'insert',
            'table': table,
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def compensate_inserts(self, operation_id: str) -> bool:
        """Compensate ClickHouse inserts by marking as deleted."""
        if not self._has_records(operation_id):
            return True
        return await self._attempt_compensation(operation_id)
    
    def _has_records(self, operation_id: str) -> bool:
        """Check if operation has records to compensate."""
        return operation_id in self.operation_records
    
    async def _attempt_compensation(self, operation_id: str) -> bool:
        """Attempt compensation with error handling."""
        try:
            success = await self._execute_compensation(operation_id)
            self._handle_compensation_result(operation_id, success)
            return success
        except Exception as e:
            logger.error(f"ClickHouse compensation failed: {e}")
            return False
    
    def _handle_compensation_result(self, operation_id: str, success: bool) -> None:
        """Handle compensation result."""
        if success:
            self._cleanup_operation_records(operation_id)
    
    def _cleanup_operation_records(self, operation_id: str) -> None:
        """Clean up operation records after successful compensation."""
        del self.operation_records[operation_id]
        logger.debug(f"Compensated ClickHouse operations: {operation_id}")
    
    async def _execute_compensation(self, operation_id: str) -> bool:
        """Execute compensation for operation records."""
        client = await get_clickhouse_client()
        records = self.operation_records[operation_id]
        await self._process_compensation_records(client, records)
        return True
    
    async def _process_compensation_records(self, client, records: List[Dict]) -> None:
        """Process all compensation records."""
        for record in records:
            if self._is_insert_record(record):
                await self._mark_as_deleted(client, record)
    
    def _is_insert_record(self, record: Dict) -> bool:
        """Check if record is an insert operation."""
        return record['action'] == 'insert'
    
    async def _mark_as_deleted(self, client, record: Dict) -> None:
        """Mark ClickHouse record as deleted."""
        compensation_data = self._create_compensation_data(record['data'])
        deleted_table = self._get_deleted_table_name(record['table'])
        await client.insert(deleted_table, [compensation_data])
    
    def _get_deleted_table_name(self, table_name: str) -> str:
        """Get name of deleted records table."""
        return f"{table_name}_deleted"
    
    def _create_compensation_data(self, original_data: Dict) -> Dict:
        """Create compensation record data."""
        return {
            **original_data,
            'deleted_at': datetime.now(),
            'deleted_by_compensation': True
        }