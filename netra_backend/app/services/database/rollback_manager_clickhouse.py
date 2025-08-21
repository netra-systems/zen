"""ClickHouse-specific rollback operations.

Contains ClickHouse compensation patterns and rollback execution logic.
Handles immutable table constraints through compensation strategies.
"""

from datetime import datetime
from typing import Dict

from app.db.clickhouse import get_clickhouse_client
from app.logging_config import central_logger
from netra_backend.app.rollback_manager_core import RollbackOperation, RollbackState

logger = central_logger.get_logger(__name__)


class ClickHouseRollbackExecutor:
    """Executes ClickHouse rollback operations using compensation."""
    
    def __init__(self):
        """Initialize ClickHouse rollback executor."""
        pass
    
    async def execute_rollback(
        self,
        operation: RollbackOperation,
        session_id: str
    ) -> bool:
        """Execute ClickHouse rollback using compensation patterns."""
        try:
            client = await get_clickhouse_client()
            success = await self._execute_compensation_by_type(client, operation)
            self._update_operation_state(operation, success)
            return success
            
        except Exception as e:
            self._handle_operation_error(operation, e)
            return False
    
    async def _execute_compensation_by_type(self, client, operation: RollbackOperation) -> bool:
        """Route operation to appropriate compensation handler."""
        compensation_handlers = {
            "INSERT": self._compensate_insert,
            "UPDATE": self._compensate_update,
            "DELETE": self._compensate_delete
        }
        
        handler = compensation_handlers.get(operation.operation_type)
        if not handler:
            logger.error(f"Unknown operation type: {operation.operation_type}")
            return False
        
        return await handler(client, operation)
    
    def _update_operation_state(self, operation: RollbackOperation, success: bool) -> None:
        """Update operation state based on execution result."""
        if success:
            operation.state = RollbackState.COMPLETED
            operation.executed_at = datetime.now()
        else:
            operation.state = RollbackState.FAILED
    
    def _handle_operation_error(self, operation: RollbackOperation, error: Exception) -> None:
        """Handle operation execution error."""
        operation.state = RollbackState.FAILED
        operation.error = str(error)
        logger.error(f"ClickHouse rollback failed: {operation.operation_id}: {error}")
    
    async def _compensate_insert(self, client, operation: RollbackOperation) -> bool:
        """Compensate INSERT by marking as deleted."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            deletion_table = f"{table_name}_deletions"
            compensation_data = self._create_deletion_compensation(rollback_data, operation.operation_id)
            
            await client.insert(deletion_table, [compensation_data])
            logger.debug(f"ClickHouse INSERT compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse INSERT compensation failed: {e}")
            return False
    
    def _create_deletion_compensation(self, rollback_data: Dict, operation_id: str) -> Dict:
        """Create compensation record for deletion."""
        return {
            **rollback_data.get('primary_key', {}),
            'deleted_at': datetime.now(),
            'deletion_reason': 'rollback_compensation',
            'operation_id': operation_id
        }
    
    async def _compensate_update(self, client, operation: RollbackOperation) -> bool:
        """Compensate UPDATE by inserting correction record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            correction_table = f"{table_name}_corrections"
            correction_data = self._create_update_compensation(rollback_data, operation.operation_id)
            
            await client.insert(correction_table, [correction_data])
            logger.debug(f"ClickHouse UPDATE compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse UPDATE compensation failed: {e}")
            return False
    
    def _create_update_compensation(self, rollback_data: Dict, operation_id: str) -> Dict:
        """Create compensation record for update."""
        return {
            **rollback_data.get('primary_key', {}),
            **rollback_data.get('original_data', {}),
            'corrected_at': datetime.now(),
            'correction_reason': 'rollback_compensation',
            'operation_id': operation_id
        }
    
    async def _compensate_delete(self, client, operation: RollbackOperation) -> bool:
        """Compensate DELETE by re-inserting the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            original_data = rollback_data.get('original_data', {})
            if not original_data:
                logger.error("No original data for DELETE compensation")
                return False
            
            restore_data = self._create_delete_compensation(original_data, operation.operation_id)
            await client.insert(table_name, [restore_data])
            logger.debug(f"ClickHouse DELETE compensated: {operation.operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse DELETE compensation failed: {e}")
            return False
    
    def _create_delete_compensation(self, original_data: Dict, operation_id: str) -> Dict:
        """Create compensation record for delete restoration."""
        return {
            **original_data,
            'restored_at': datetime.now(),
            'restore_reason': 'rollback_compensation',
            'operation_id': operation_id
        }