"""
ClickHouse operations for corpus management
Handles table creation, management, and database-specific operations
"""

import asyncio
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db import models_postgres as models
from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.corpus.base import (
    ClickHouseOperationError,
    CorpusStatus,
)
from netra_backend.app.services.corpus.clickhouse_helpers import (
    build_column_info,
    build_error_notification_payload,
    build_schema_query,
    build_success_notification_payload,
    build_table_exists_query,
    build_table_size_query,
    create_clickhouse_operation_error,
    initialize_schema_dict,
    log_schema_error,
    log_table_exists_error,
    log_table_operation_error,
    log_table_operation_success,
    process_schema_row,
    process_table_exists_result,
    process_table_size_result,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class CorpusClickHouseOperations:
    """Handles ClickHouse-specific operations for corpus management"""
    
    def __init__(self, user_context: Optional[UserExecutionContext] = None):
        """Initialize with optional user context for WebSocket notifications.
        
        Args:
            user_context: Optional user context for WebSocket isolation.
                         If provided, enables WebSocket notifications.
                         If None, notifications are logged only.
        """
        self.user_context = user_context
        self._websocket_manager = None
        
        # Initialize isolated WebSocket manager if user context is provided
        if self.user_context:
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                self._websocket_manager = create_websocket_manager(self.user_context)
                central_logger.info(
                    f"Initialized CorpusClickHouseOperations with WebSocket support for user {user_context.user_id[:8]}..."
                )
            except Exception as e:
                central_logger.warning(
                    f"Failed to initialize WebSocket manager for corpus operations: {e}. "
                    "Notifications will be logged only."
                )
                self._websocket_manager = None
        else:
            central_logger.debug(
                "CorpusClickHouseOperations initialized without user context. "
                "WebSocket notifications disabled."
            )
    
    def _get_table_columns(self) -> str:
        """Get table column definitions"""
        columns = [
            "record_id UUID", "workload_type String", "prompt String",
            "response String", "metadata String", "domain String",
            "created_at DateTime64(3) DEFAULT now()", "version UInt32 DEFAULT 1"
        ]
        return ", ".join(columns)

    def _get_table_engine_config(self) -> str:
        """Get table engine and partitioning configuration"""
        return (
            "ENGINE = MergeTree() "
            "PARTITION BY toYYYYMM(created_at) "
            "ORDER BY (workload_type, created_at, record_id)"
        )

    def _build_create_table_query(self, table_name: str) -> str:
        """Build CREATE TABLE SQL query for ClickHouse"""
        columns = self._get_table_columns()
        engine_config = self._get_table_engine_config()
        return (
            f"CREATE TABLE IF NOT EXISTS {table_name} ({columns}) "
            f"{engine_config}"
        )

    async def _execute_table_creation(self, table_name: str, query: str):
        """Execute table creation in ClickHouse"""
        async with get_clickhouse_client() as client:
            await client.execute(query)

    async def _update_corpus_status_success(self, corpus_id: str, db: AsyncSession):
        """Update corpus status to AVAILABLE in PostgreSQL"""
        from sqlalchemy import update
        
        query = update(models.Corpus).where(
            models.Corpus.id == corpus_id
        ).values(status=CorpusStatus.AVAILABLE.value)
        
        await db.execute(query)
        await db.commit()

    def _build_success_payload(self, corpus_id: str, table_name: str) -> Dict:
        """Build success notification payload"""
        payload_data = {
            "corpus_id": corpus_id, "table_name": table_name,
            "status": CorpusStatus.AVAILABLE.value
        }
        return {"type": "corpus:created", "payload": payload_data}

    async def _send_success_notification(self, corpus_id: str, table_name: str):
        """Send WebSocket notification for successful corpus creation"""
        payload = self._build_success_payload(corpus_id, table_name)
        
        if self._websocket_manager:
            try:
                await self._websocket_manager.emit_critical_event(
                    event_type="corpus:created",
                    data=payload["payload"]
                )
                central_logger.info(f"Sent corpus creation notification via WebSocket: {payload}")
            except Exception as e:
                central_logger.error(f"Failed to send WebSocket notification: {e}")
                central_logger.info(f"Corpus creation notification (fallback to log): {payload}")
        else:
            central_logger.info(f"Corpus creation notification (WebSocket not available): {payload}")

    def _log_creation_success(self, corpus_id: str, table_name: str):
        """Log successful table creation"""
        central_logger.info(
            f"Created ClickHouse table {table_name} for corpus {corpus_id}"
        )

    async def _update_corpus_status_failed(self, corpus_id: str, db: AsyncSession):
        """Update corpus status to FAILED in PostgreSQL"""
        from sqlalchemy import update
        
        query = update(models.Corpus).where(
            models.Corpus.id == corpus_id
        ).values(status=CorpusStatus.FAILED.value)
        
        await db.execute(query)
        await db.commit()

    def _build_error_payload(self, corpus_id: str, error: Exception) -> Dict:
        """Build error notification payload"""
        payload_data = {"corpus_id": corpus_id, "error": str(error)}
        return {"type": "corpus:error", "payload": payload_data}

    async def _send_error_notification(self, corpus_id: str, error: Exception):
        """Send WebSocket notification for corpus creation error"""
        payload = self._build_error_payload(corpus_id, error)
        
        if self._websocket_manager:
            try:
                await self._websocket_manager.emit_critical_event(
                    event_type="corpus:error",
                    data=payload["payload"]
                )
                central_logger.error(f"Sent corpus error notification via WebSocket: {payload}")
            except Exception as e:
                central_logger.error(f"Failed to send WebSocket error notification: {e}")
                central_logger.error(f"Corpus error notification (fallback to log): {payload}")
        else:
            central_logger.error(f"Corpus error notification (WebSocket not available): {payload}")

    def _log_creation_error(self, corpus_id: str, error: Exception):
        """Log table creation error"""
        central_logger.error(
            f"Failed to create ClickHouse table for corpus {corpus_id}: {str(error)}"
        )

    async def _handle_creation_error(
        self, corpus_id: str, error: Exception, db: AsyncSession
    ):
        """Handle corpus table creation error"""
        self._log_creation_error(corpus_id, error)
        await self._update_corpus_status_failed(corpus_id, db)
        await self._send_error_notification(corpus_id, error)
        raise ClickHouseOperationError(f"Failed to create table: {str(error)}")

    async def _execute_success_flow(
        self, corpus_id: str, table_name: str, db: AsyncSession
    ):
        """Execute successful table creation flow"""
        await self._update_corpus_status_success(corpus_id, db)
        await self._send_success_notification(corpus_id, table_name)
        self._log_creation_success(corpus_id, table_name)

    async def create_corpus_table(self, corpus_id: str, table_name: str, db: AsyncSession):
        """Create ClickHouse table for corpus content"""
        try:
            query = self._build_create_table_query(table_name)
            await self._execute_table_creation(table_name, query)
            await self._execute_success_flow(corpus_id, table_name, db)
        except Exception as e:
            await self._handle_creation_error(corpus_id, e, db)
    
    async def delete_corpus_table(self, table_name: str):
        """Delete ClickHouse table for corpus"""
        try:
            async with get_clickhouse_client() as client:
                await client.execute(f"DROP TABLE IF EXISTS {table_name}")
                log_table_operation_success("Deleted", table_name)
        except Exception as e:
            log_table_operation_error("delete", table_name, e)
            raise create_clickhouse_operation_error("delete table", e)
    
    def _build_table_exists_query(self, table_name: str) -> str:
        """Build query to check table existence"""
        return build_table_exists_query(table_name)

    def _process_table_exists_result(self, result) -> bool:
        """Process table existence query result"""
        return process_table_exists_result(result)

    async def _execute_table_exists_query(self, table_name: str) -> bool:
        """Execute table existence query"""
        async with get_clickhouse_client() as client:
            query = self._build_table_exists_query(table_name)
            result = await client.execute(query)
            return self._process_table_exists_result(result)

    def _handle_table_exists_error(self, table_name: str, error: Exception) -> None:
        """Handle table existence check errors"""
        log_table_exists_error(table_name, error)
        raise create_clickhouse_operation_error("check table existence", error)

    async def check_table_exists(self, table_name: str) -> bool:
        """Check if ClickHouse table exists"""
        try:
            return await self._execute_table_exists_query(table_name)
        except Exception as e:
            self._handle_table_exists_error(table_name, e)
    
    def _build_schema_query(self, table_name: str) -> str:
        """Build schema query for table columns"""
        return build_schema_query(table_name)

    def _initialize_schema_dict(self) -> Dict:
        """Initialize empty schema dictionary structure"""
        return initialize_schema_dict()

    def _build_column_info(self, row) -> Dict:
        """Build column information from result row"""
        return build_column_info(row)

    def _process_schema_row(self, schema: Dict, row) -> None:
        """Process single schema row and update schema dict"""
        process_schema_row(schema, row)

    def _process_schema_results(self, result) -> Dict:
        """Process all schema query results into schema dictionary"""
        schema = self._initialize_schema_dict()
        for row in result:
            self._process_schema_row(schema, row)
        return schema

    async def _execute_schema_query(self, table_name: str) -> Dict:
        """Execute schema query and return processed results"""
        async with get_clickhouse_client() as client:
            query = self._build_schema_query(table_name)
            result = await client.execute(query)
            return self._process_schema_results(result)

    def _handle_schema_error(self, table_name: str, error: Exception) -> None:
        """Handle and log schema retrieval errors"""
        log_schema_error(table_name, error)
        raise create_clickhouse_operation_error("get table schema", error)

    async def get_table_schema(self, table_name: str) -> Dict:
        """Get ClickHouse table schema information"""
        try:
            return await self._execute_schema_query(table_name)
        except Exception as e:
            self._handle_schema_error(table_name, e)
    
    async def optimize_table(self, table_name: str):
        """Optimize ClickHouse table for better performance"""
        try:
            async with get_clickhouse_client() as client:
                await client.execute(f"OPTIMIZE TABLE {table_name}")
                log_table_operation_success("Optimized", table_name)
        except Exception as e:
            log_table_operation_error("optimize", table_name, e)
            raise create_clickhouse_operation_error("optimize table", e)
    
    async def get_table_size(self, table_name: str) -> Dict:
        """Get ClickHouse table size information"""
        try:
            async with get_clickhouse_client() as client:
                query = build_table_size_query(table_name)
                result = await client.execute(query)
                return process_table_size_result(result)
        except Exception as e:
            log_table_operation_error("get size for", table_name, e)
            raise create_clickhouse_operation_error("get table size", e)


# Backward compatibility alias
ClickHouseOperations = CorpusClickHouseOperations