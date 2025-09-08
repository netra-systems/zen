"""Data interfaces - Single source of truth.

Consolidated ClickHouse operations for both simple data fetching
and complex corpus table management with notifications and status tracking.
Follows 450-line limit and 25-line functions.
"""

import asyncio
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusStatus(Enum):
    """Corpus status enumeration."""
    CREATING = "creating"
    AVAILABLE = "available"
    FAILED = "failed"
    DELETING = "deleting"


class ClickHouseOperationError(Exception):
    """Exception for ClickHouse operation failures."""
    pass


class CoreClickHouseOperations:
    """Unified ClickHouse operations for data fetching and corpus management."""
    
    def __init__(self):
        """Initialize ClickHouse operations handler."""
        pass
    
    # Simple data operations
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a table with security validation."""
        if not self._is_valid_table_name(table_name):
            logger.error(f"Invalid table name format: {table_name}")
            return None
        
        try:
            return await self._execute_schema_query(table_name)
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return None
    
    async def fetch_data(self, query: str, cache_key: Optional[str] = None,
                        redis_manager=None, cache_ttl: int = 300) -> Optional[List[Dict[str, Any]]]:
        """Execute ClickHouse query with caching support."""
        # Check cache first
        cached_result = await self._try_get_cached_data(cache_key, redis_manager)
        if cached_result:
            return cached_result
        
        try:
            result = await self._execute_data_query(query)
            if result and cache_key and redis_manager:
                await self._cache_query_result(cache_key, result, redis_manager, cache_ttl)
            return result
            
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            return None
    
    # Complex corpus operations
    
    async def create_corpus_table(self, corpus_id: str, table_name: str, db: Session, user_context=None):
        """Create ClickHouse table for corpus content with status management."""
        try:
            query = self._build_corpus_table_query(table_name)
            await self._execute_table_creation(table_name, query)
            await self._handle_corpus_creation_success(corpus_id, table_name, db, user_context)
        except Exception as e:
            await self._handle_corpus_creation_error(corpus_id, e, db, user_context)
    
    async def delete_corpus_table(self, table_name: str):
        """Delete ClickHouse table for corpus."""
        try:
            await self._execute_table_deletion(table_name)
            logger.info(f"Successfully deleted table {table_name}")
        except Exception as e:
            logger.error(f"Failed to delete table {table_name}: {e}")
            raise ClickHouseOperationError(f"Failed to delete table: {str(e)}")
    
    async def check_table_exists(self, table_name: str) -> bool:
        """Check if ClickHouse table exists."""
        try:
            return await self._execute_table_exists_check(table_name)
        except Exception as e:
            logger.error(f"Failed to check table existence for {table_name}: {e}")
            raise ClickHouseOperationError(f"Failed to check table existence: {str(e)}")
    
    async def optimize_table(self, table_name: str):
        """Optimize ClickHouse table for better performance."""
        try:
            await self._execute_table_optimization(table_name)
            logger.info(f"Successfully optimized table {table_name}")
        except Exception as e:
            logger.error(f"Failed to optimize table {table_name}: {e}")
            raise ClickHouseOperationError(f"Failed to optimize table: {str(e)}")
    
    async def get_table_size(self, table_name: str) -> Dict:
        """Get ClickHouse table size information."""
        try:
            return await self._execute_table_size_query(table_name)
        except Exception as e:
            logger.error(f"Failed to get table size for {table_name}: {e}")
            raise ClickHouseOperationError(f"Failed to get table size: {str(e)}")
    
    # Helper methods for simple operations
    
    def _is_valid_table_name(self, table_name: str) -> bool:
        """Validate table name to prevent SQL injection."""
        return (table_name and 
                table_name.replace('_', '').replace('.', '').isalnum())
    
    async def _execute_schema_query(self, table_name: str) -> Dict[str, Any]:
        """Execute schema query safely."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            query = "DESCRIBE TABLE {}"
            result = await client.execute_query(query.format(client.escape_identifier(table_name)))
            return {
                "columns": [{"name": row[0], "type": row[1]} for row in result],
                "table": table_name
            }
    
    async def _try_get_cached_data(self, cache_key: Optional[str], redis_manager) -> Optional[List[Dict[str, Any]]]:
        """Try to get data from cache."""
        if not cache_key or not redis_manager:
            return None
        
        try:
            cached = await redis_manager.get(cache_key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
            return None
    
    async def _execute_data_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute data query and return formatted results."""
        from netra_backend.app.database import get_clickhouse_client
        from netra_backend.app.db.clickhouse_init import (
            create_workload_events_table_if_missing,
        )
        
        await create_workload_events_table_if_missing()
        
        async with get_clickhouse_client() as client:
            result = await client.execute_query(query)
            return self._format_query_result(result)
    
    def _format_query_result(self, result) -> List[Dict[str, Any]]:
        """Format query result into list of dictionaries."""
        if not result:
            return []
        
        columns = result[0]._fields if hasattr(result[0], '_fields') else list(range(len(result[0])))
        return [dict(zip(columns, row)) for row in result]
    
    async def _cache_query_result(self, cache_key: str, result: List[Dict[str, Any]], 
                                 redis_manager, cache_ttl: int) -> None:
        """Cache query result if possible."""
        try:
            await redis_manager.set(cache_key, json.dumps(result, default=str), ex=cache_ttl)
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    # Helper methods for corpus operations
    
    def _build_corpus_table_query(self, table_name: str) -> str:
        """Build CREATE TABLE query for corpus."""
        columns = self._get_corpus_table_columns()
        engine_config = self._get_corpus_table_engine()
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({columns}) {engine_config}"
    
    def _get_corpus_table_columns(self) -> str:
        """Get corpus table column definitions."""
        columns = [
            "record_id UUID", "workload_type String", "prompt String",
            "response String", "metadata String", "domain String",
            "created_at DateTime64(3) DEFAULT now()", "version UInt32 DEFAULT 1"
        ]
        return ", ".join(columns)
    
    def _get_corpus_table_engine(self) -> str:
        """Get corpus table engine configuration."""
        return (
            "ENGINE = MergeTree() "
            "PARTITION BY toYYYYMM(created_at) "
            "ORDER BY (workload_type, created_at, record_id)"
        )
    
    async def _execute_table_creation(self, table_name: str, query: str):
        """Execute table creation in ClickHouse."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            await client.execute(query)
    
    async def _execute_table_deletion(self, table_name: str):
        """Execute table deletion in ClickHouse."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            await client.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    async def _execute_table_exists_check(self, table_name: str) -> bool:
        """Execute table existence check."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            query = f"EXISTS TABLE {table_name}"
            result = await client.execute(query)
            return bool(result[0][0]) if result else False
    
    async def _execute_table_optimization(self, table_name: str):
        """Execute table optimization."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            await client.execute(f"OPTIMIZE TABLE {table_name}")
    
    async def _execute_table_size_query(self, table_name: str) -> Dict:
        """Execute table size query."""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            query = f"""
                SELECT 
                    formatReadableSize(sum(bytes)) as size,
                    sum(rows) as rows,
                    count() as parts
                FROM system.parts 
                WHERE table = '{table_name}' AND active = 1
            """
            result = await client.execute(query)
            if result:
                return {"size": result[0][0], "rows": result[0][1], "parts": result[0][2]}
            return {"size": "0 B", "rows": 0, "parts": 0}
    
    # Status management methods
    
    async def _handle_corpus_creation_success(self, corpus_id: str, table_name: str, db: Session, user_context=None):
        """Handle successful corpus table creation."""
        self._update_corpus_status(corpus_id, CorpusStatus.AVAILABLE, db)
        await self._send_corpus_notification(corpus_id, table_name, "created", user_context=user_context)
        logger.info(f"Created ClickHouse table {table_name} for corpus {corpus_id}")
    
    async def _handle_corpus_creation_error(self, corpus_id: str, error: Exception, db: Session, user_context=None):
        """Handle corpus table creation error."""
        self._update_corpus_status(corpus_id, CorpusStatus.FAILED, db)
        await self._send_corpus_notification(corpus_id, None, "error", str(error), user_context=user_context)
        logger.error(f"Failed to create ClickHouse table for corpus {corpus_id}: {str(error)}")
        raise ClickHouseOperationError(f"Failed to create table: {str(error)}")
    
    def _update_corpus_status(self, corpus_id: str, status: CorpusStatus, db: Session):
        """Update corpus status in PostgreSQL."""
        from netra_backend.app.db import models_postgres as models
        
        db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).update({"status": status.value})
        db.commit()
    
    async def _send_corpus_notification(self, corpus_id: str, table_name: Optional[str], 
                                       event_type: str, error: Optional[str] = None, 
                                       user_context=None):
        """Send WebSocket notification for corpus events.
        
        Args:
            corpus_id: Corpus identifier
            table_name: Optional table name
            event_type: Type of event ('created' or 'error')
            error: Optional error message
            user_context: Optional user execution context for WebSocket notifications
        """
        try:
            if not user_context:
                logger.debug(f"Corpus notification not sent - no user context provided for {corpus_id}")
                return
                
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            manager = await create_websocket_manager(user_context)
            
            if event_type == "created":
                payload = {
                    "type": "corpus:created",
                    "payload": {
                        "corpus_id": corpus_id,
                        "table_name": table_name,
                        "status": CorpusStatus.AVAILABLE.value
                    }
                }
            else:  # error
                payload = {
                    "type": "corpus:error",
                    "payload": {"corpus_id": corpus_id, "error": error}
                }
            
            # Send to specific user instead of broadcast
            await manager.send_to_user(user_context.user_id, payload)
        except Exception as e:
            logger.error(f"Failed to send corpus notification: {e}")


# Factory functions
def create_clickhouse_operations() -> CoreClickHouseOperations:
    """Create ClickHouse operations instance."""
    return CoreClickHouseOperations()


def create_clickhouse_operation_error(operation: str, error: Exception) -> ClickHouseOperationError:
    """Create ClickHouse operation error."""
    return ClickHouseOperationError(f"Failed to {operation}: {str(error)}")