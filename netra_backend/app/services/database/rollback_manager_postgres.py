"""PostgreSQL-specific rollback operations.

Contains all PostgreSQL rollback execution logic and query builders.
Handles transaction management and SQL generation for rollbacks.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from netra_backend.app.db.postgres import get_postgres_session
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.rollback_manager_core import (
    RollbackOperation,
    RollbackState,
)

logger = central_logger.get_logger(__name__)


class PostgresRollbackExecutor:
    """Executes PostgreSQL rollback operations."""
    
    def __init__(self):
        """Initialize PostgreSQL rollback executor."""
        self.active_connections: Dict[str, Any] = {}
    
    async def execute_rollback(
        self,
        operation: RollbackOperation,
        session_id: str
    ) -> bool:
        """Execute a single PostgreSQL rollback operation."""
        try:
            session = await self._get_session(session_id)
            success = await self._execute_operation_by_type(session, operation)
            self._update_operation_state(operation, success)
            return success
            
        except Exception as e:
            self._handle_operation_error(operation, e)
            return False
    
    async def _get_session(self, session_id: str):
        """Get or create database session for rollback."""
        if session_id not in self.active_connections:
            session = await get_postgres_session()
            self.active_connections[session_id] = session
            await session.begin()
        return self.active_connections[session_id]
    
    async def _execute_operation_by_type(self, session, operation: RollbackOperation) -> bool:
        """Route operation to appropriate handler based on type."""
        operation_handlers = {
            "INSERT": self._rollback_insert,
            "UPDATE": self._rollback_update,
            "DELETE": self._rollback_delete
        }
        
        handler = operation_handlers.get(operation.operation_type)
        if not handler:
            logger.error(f"Unknown operation type: {operation.operation_type}")
            return False
        
        return await handler(session, operation)
    
    def _update_operation_state(self, operation: RollbackOperation, success: bool) -> None:
        """Update operation state based on execution result."""
        if success:
            operation.state = RollbackState.COMPLETED
            operation.executed_at = datetime.now()
            logger.debug(f"Rollback completed: {operation.operation_id}")
        else:
            operation.state = RollbackState.FAILED
    
    def _handle_operation_error(self, operation: RollbackOperation, error: Exception) -> None:
        """Handle operation execution error."""
        operation.state = RollbackState.FAILED
        operation.error = str(error)
        logger.error(f"Rollback execution failed: {operation.operation_id}: {error}")
    
    async def _rollback_insert(self, session, operation: RollbackOperation) -> bool:
        """Rollback an INSERT operation by deleting the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            where_conditions, where_values = self._build_where_clause_for_insert(rollback_data)
            if not where_conditions:
                logger.error("No conditions available for INSERT rollback")
                return False
            
            query = f"DELETE FROM {table_name} WHERE {' AND '.join(where_conditions)}"
            result = await session.execute(query, where_values)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Insert rollback failed: {e}")
            return False
    
    def _build_where_clause_for_insert(self, rollback_data: Dict) -> Tuple[List[str], List[Any]]:
        """Build WHERE clause for INSERT rollback using primary key or all data."""
        where_conditions = []
        where_values = []
        
        primary_key = rollback_data.get('primary_key', {})
        if primary_key:
            for key, value in primary_key.items():
                where_conditions.append(f"{key} = %s")
                where_values.append(value)
        else:
            data = rollback_data.get('data', {})
            for key, value in data.items():
                where_conditions.append(f"{key} = %s")
                where_values.append(value)
        
        return where_conditions, where_values
    
    async def _rollback_update(self, session, operation: RollbackOperation) -> bool:
        """Rollback an UPDATE operation by restoring original values."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            original_data = rollback_data.get('original_data', {})
            primary_key = rollback_data.get('primary_key', {})
            
            if not original_data or not primary_key:
                logger.error("Insufficient data for UPDATE rollback")
                return False
            
            set_clauses, set_values = self._build_set_clause(original_data)
            where_conditions, where_values = self._build_where_clause(primary_key)
            
            query = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE {' AND '.join(where_conditions)}
            """
            
            result = await session.execute(query, set_values + where_values)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Update rollback failed: {e}")
            return False
    
    def _build_set_clause(self, original_data: Dict) -> Tuple[List[str], List[Any]]:
        """Build SET clause for UPDATE operations."""
        set_clauses = []
        set_values = []
        for key, value in original_data.items():
            set_clauses.append(f"{key} = %s")
            set_values.append(value)
        return set_clauses, set_values
    
    def _build_where_clause(self, primary_key: Dict) -> Tuple[List[str], List[Any]]:
        """Build WHERE clause for operations."""
        where_conditions = []
        where_values = []
        for key, value in primary_key.items():
            where_conditions.append(f"{key} = %s")
            where_values.append(value)
        return where_conditions, where_values
    
    async def _rollback_delete(self, session, operation: RollbackOperation) -> bool:
        """Rollback a DELETE operation by restoring the record."""
        try:
            table_name = operation.table_name
            rollback_data = operation.rollback_data
            
            original_data = rollback_data.get('original_data', {})
            if not original_data:
                logger.error("No original data for DELETE rollback")
                return False
            
            columns = list(original_data.keys())
            values = list(original_data.values())
            placeholders = ', '.join(['%s'] * len(values))
            
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            await session.execute(query, values)
            return True
            
        except Exception as e:
            logger.error(f"Delete rollback failed: {e}")
            return False
    
    async def commit_session(self, session_id: str) -> None:
        """Commit rollback session."""
        if session_id in self.active_connections:
            session = self.active_connections[session_id]
            await session.commit()
            await session.close()
            del self.active_connections[session_id]
    
    async def rollback_session(self, session_id: str) -> None:
        """Rollback the rollback session (undo rollbacks)."""
        if session_id in self.active_connections:
            session = self.active_connections[session_id]
            await session.rollback()
            await session.close()
            del self.active_connections[session_id]