"""Core compensation handlers for different operation types.

Implements concrete handlers for database, filesystem, cache, and external services.
All functions strictly adhere to 25-line limit.
"""

import os
import shutil
import aiohttp
from typing import List, Dict, Any, Optional

from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.services.database.rollback_manager import rollback_manager
from netra_backend.app.logging_config import central_logger

from netra_backend.app.compensation_models import (
    BaseCompensationHandler,
    CompensationAction
)

logger = central_logger.get_logger(__name__)


class DatabaseCompensationHandler(BaseCompensationHandler):
    """Handles compensation for database operations."""
    
    def __init__(self):
        """Initialize database compensation handler."""
        self.rollback_manager = rollback_manager
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate database operations."""
        return context.operation_type in [
            OperationType.DATABASE_WRITE,
            OperationType.DATABASE_READ
        ]
    
    def _create_session_metadata(self, action: CompensationAction) -> Dict[str, Any]:
        """Create metadata for rollback session."""
        return {
            'compensation_action_id': action.action_id,
            'original_operation_id': action.operation_id
        }
    
    async def _create_rollback_session(self, action: CompensationAction) -> str:
        """Create rollback session for compensation."""
        metadata = self._create_session_metadata(action)
        return await self.rollback_manager.create_rollback_session(metadata)
    
    async def _add_rollback_operations(self, session_id: str, operations: List[Dict]) -> None:
        """Add rollback operations to session."""
        for rollback_op in operations:
            await self.rollback_manager.add_rollback_operation(
                session_id=session_id,
                table_name=rollback_op['table_name'],
                operation_type=rollback_op['operation_type'],
                rollback_data=rollback_op['rollback_data']
            )
    
    async def _execute_database_rollback(self, session_id: str, action_id: str) -> bool:
        """Execute database rollback and log result."""
        success = await self.rollback_manager.execute_rollback_session(session_id)
        if success:
            logger.info(f"Database compensation completed: {action_id}")
        else:
            logger.error(f"Database compensation failed: {action_id}")
        return success
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute database rollback compensation."""
        try:
            session_id = await self._create_rollback_session(action)
            rollback_ops = action.compensation_data.get('rollback_operations', [])
            await self._add_rollback_operations(session_id, rollback_ops)
            return await self._execute_database_rollback(session_id, action.action_id)
        except Exception as e:
            logger.error(f"Database compensation error: {action.action_id}: {e}")
            return False
    
    def get_priority(self) -> int:
        """Database operations have high priority for compensation."""
        return 1


class FileSystemCompensationHandler(BaseCompensationHandler):
    """Handles compensation for file system operations."""
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate file operations."""
        return context.operation_type == OperationType.FILE_OPERATION
    
    def _delete_file_if_exists(self, file_path: str) -> None:
        """Delete file if it exists."""
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
    
    def _restore_file_from_backup(self, operation: Dict[str, Any]) -> None:
        """Restore file from backup path."""
        backup_path = operation.get('backup_path')
        file_path = operation.get('file_path')
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            logger.debug(f"Restored file: {file_path}")
    
    def _delete_directory_if_exists(self, file_path: str) -> None:
        """Delete directory if it exists."""
        if os.path.exists(file_path) and os.path.isdir(file_path):
            shutil.rmtree(file_path)
            logger.debug(f"Deleted directory: {file_path}")
    
    def _execute_file_operation(self, operation: Dict[str, Any]) -> None:
        """Execute single file operation based on type."""
        op_type = operation.get('type')
        file_path = operation.get('file_path')
        
        if op_type == 'delete_file':
            self._delete_file_if_exists(file_path)
        elif op_type == 'restore_file':
            self._restore_file_from_backup(operation)
        elif op_type == 'delete_directory':
            self._delete_directory_if_exists(file_path)
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute file system compensation."""
        try:
            file_operations = action.compensation_data.get('file_operations', [])
            for operation in file_operations:
                self._execute_file_operation(operation)
            logger.info(f"File system compensation completed: {action.action_id}")
            return True
        except Exception as e:
            logger.error(f"File system compensation error: {action.action_id}: {e}")
            return False
    
    def get_priority(self) -> int:
        """File operations have medium priority."""
        return 3


class CacheCompensationHandler(BaseCompensationHandler):
    """Handles compensation for cache operations."""
    
    def __init__(self, cache_manager=None):
        """Initialize cache compensation handler."""
        self.cache_manager = cache_manager
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate cache operations."""
        return context.operation_type == OperationType.CACHE_OPERATION
    
    def _check_cache_manager_available(self, action_id: str) -> bool:
        """Check if cache manager is available for compensation."""
        if not self.cache_manager:
            logger.warning("No cache manager available for compensation")
            return False
        return True
    
    async def _execute_cache_operation(self, operation: Dict[str, Any]) -> None:
        """Execute single cache operation."""
        op_type = operation.get('type')
        key = operation.get('key')
        
        if op_type == 'delete' and key:
            await self.cache_manager.delete(key)
        elif op_type == 'set' and key:
            value = operation.get('value')
            await self.cache_manager.set(key, value)
        elif op_type == 'invalidate' and key:
            await self.cache_manager.invalidate(key)
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute cache compensation."""
        if not self._check_cache_manager_available(action.action_id):
            return True  # Skip compensation
        
        try:
            cache_operations = action.compensation_data.get('cache_operations', [])
            for operation in cache_operations:
                await self._execute_cache_operation(operation)
            logger.info(f"Cache compensation completed: {action.action_id}")
            return True
        except Exception as e:
            logger.error(f"Cache compensation error: {action.action_id}: {e}")
            return False
    
    def get_priority(self) -> int:
        """Cache operations have low priority."""
        return 2


class ExternalServiceCompensationHandler(BaseCompensationHandler):
    """Handles compensation for external service operations."""
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate external service calls."""
        return context.operation_type == OperationType.EXTERNAL_API
    
    def _validate_http_operation(self, operation: Dict[str, Any]) -> bool:
        """Validate HTTP operation has required fields."""
        return bool(operation.get('url'))
    
    async def _execute_http_request(
        self, 
        session: aiohttp.ClientSession, 
        operation: Dict[str, Any]
    ) -> None:
        """Execute single HTTP compensation request."""
        method = operation.get('method', 'POST')
        url = operation.get('url')
        data = operation.get('data')
        headers = operation.get('headers', {})
        
        async with session.request(
            method=method, url=url, json=data, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status < 400:
                logger.debug(f"External compensation call succeeded: {url}")
            else:
                logger.warning(f"External compensation call failed: {url} (status: {response.status})")
    
    async def _process_http_operations(self, operations: List[Dict[str, Any]]) -> None:
        """Process all HTTP compensation operations."""
        async with aiohttp.ClientSession() as session:
            for operation in operations:
                if not self._validate_http_operation(operation):
                    continue
                try:
                    await self._execute_http_request(session, operation)
                except Exception as e:
                    url = operation.get('url', 'unknown')
                    logger.warning(f"External compensation call error: {url}: {e}")
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute external service compensation."""
        try:
            http_operations = action.compensation_data.get('http_operations', [])
            await self._process_http_operations(http_operations)
            logger.info(f"External service compensation completed: {action.action_id}")
            return True
        except Exception as e:
            logger.error(f"External service compensation error: {action.action_id}: {e}")
            return False
    
    def get_priority(self) -> int:
        """External services have medium-low priority."""
        return 4