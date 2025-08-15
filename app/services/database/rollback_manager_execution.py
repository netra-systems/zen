"""Batch execution logic for rollback operations.

Contains the batch execution coordinator and result processing
for concurrent rollback operation execution.
"""

import asyncio
from typing import Any, Dict, List

from app.logging_config import central_logger
from .rollback_manager_core import RollbackOperation, RollbackState

logger = central_logger.get_logger(__name__)


class BatchExecutor:
    """Executes batches of rollback operations concurrently."""
    
    def __init__(self, postgres_executor, clickhouse_executor):
        """Initialize with database executors."""
        self.postgres_executor = postgres_executor
        self.clickhouse_executor = clickhouse_executor
    
    async def execute_all_batches(
        self, 
        session_id: str, 
        execution_batches: List[List[RollbackOperation]]
    ) -> Dict[str, Any]:
        """Execute all operation batches and track results."""
        success_count = 0
        failed_operations = []
        
        for batch_idx, batch in enumerate(execution_batches):
            batch_result = await self._execute_single_batch(
                session_id, batch, batch_idx, len(execution_batches)
            )
            success_count += batch_result['successes']
            failed_operations.extend(batch_result['failures'])
        
        return {
            'success_count': success_count, 
            'failed_operations': failed_operations
        }
    
    async def _execute_single_batch(
        self, 
        session_id: str, 
        batch: List[RollbackOperation], 
        batch_idx: int, 
        total_batches: int
    ) -> Dict[str, Any]:
        """Execute a single batch of operations concurrently."""
        batch_tasks = [
            self._create_execution_task(operation, session_id) 
            for operation in batch
        ]
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        result = self._process_batch_results(batch, batch_results)
        self._log_batch_completion(batch_idx, total_batches, len(batch), result)
        
        return result
    
    def _create_execution_task(self, operation: RollbackOperation, session_id: str):
        """Create execution task for operation based on table type."""
        if operation.table_name.startswith('clickhouse_'):
            return self.clickhouse_executor.execute_rollback(operation, session_id)
        return self.postgres_executor.execute_rollback(operation, session_id)
    
    def _process_batch_results(
        self, 
        batch: List[RollbackOperation], 
        batch_results: List[Any]
    ) -> Dict[str, Any]:
        """Process batch execution results and update operation states."""
        successes = 0
        failures = []
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                self._handle_operation_exception(batch[i], result, failures)
            elif result:
                successes += 1
            else:
                failures.append(batch[i])
        
        return {'successes': successes, 'failures': failures}
    
    def _handle_operation_exception(
        self, 
        operation: RollbackOperation, 
        exception: Exception, 
        failures: List[RollbackOperation]
    ) -> None:
        """Handle operation exception and update state."""
        operation.state = RollbackState.FAILED
        operation.error = str(exception)
        failures.append(operation)
    
    def _log_batch_completion(
        self, 
        batch_idx: int, 
        total_batches: int, 
        batch_size: int, 
        result: Dict[str, Any]
    ) -> None:
        """Log batch completion statistics."""
        logger.info(
            f"Completed rollback batch {batch_idx + 1}/{total_batches}",
            batch_size=batch_size,
            successes=result['successes'],
            failures=len(result['failures'])
        )