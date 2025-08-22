"""
Specific compensation handlers for different operation types.
Contains implementations for database, filesystem, cache, and external service compensation.
"""

import os
import shutil
from typing import Optional

from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.compensation_base import BaseCompensationHandler
from netra_backend.app.services.compensation_types import CompensationAction
from netra_backend.app.services.database.rollback_manager import rollback_manager

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
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute database rollback compensation."""
        try:
            if not self._validate_compensation_requirements(action):
                return False
            
            session_id = await self._create_rollback_session(action)
            await self._add_rollback_operations(action, session_id)
            return await self._execute_and_log_rollback(action, session_id)
            
        except Exception as e:
            logger.error(f"Database compensation error: {action.action_id}: {e}")
            return False
    
    def _validate_compensation_requirements(self, action: CompensationAction) -> bool:
        """Validate required compensation data"""
        return self.validate_compensation_data(
            action.compensation_data,
            ['rollback_operations']
        )
    
    async def _create_rollback_session(self, action: CompensationAction) -> str:
        """Create rollback session for compensation"""
        return await self.rollback_manager.create_rollback_session({
            'compensation_action_id': action.action_id,
            'original_operation_id': action.operation_id
        })
    
    async def _add_rollback_operations(self, action: CompensationAction, session_id: str) -> None:
        """Add rollback operations from compensation data"""
        rollback_ops = action.compensation_data.get('rollback_operations', [])
        for rollback_op in rollback_ops:
            await self._add_single_rollback_operation(session_id, rollback_op)
    
    async def _add_single_rollback_operation(self, session_id: str, rollback_op: Dict) -> None:
        """Add a single rollback operation"""
        await self.rollback_manager.add_rollback_operation(
            session_id=session_id,
            table_name=rollback_op['table_name'],
            operation_type=rollback_op['operation_type'],
            rollback_data=rollback_op['rollback_data']
        )
    
    async def _execute_and_log_rollback(self, action: CompensationAction, session_id: str) -> bool:
        """Execute rollback and log results"""
        success = await self.rollback_manager.execute_rollback_session(session_id)
        self._log_rollback_result(action, success)
        return success
    
    def _log_rollback_result(self, action: CompensationAction, success: bool) -> None:
        """Log rollback execution result"""
        if success:
            logger.info(f"Database compensation completed: {action.action_id}")
        else:
            logger.error(f"Database compensation failed: {action.action_id}")
    
    def get_priority(self) -> int:
        """Database operations have high priority for compensation."""
        return 1


class FileSystemCompensationHandler(BaseCompensationHandler):
    """Handles compensation for file system operations."""
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate file operations."""
        return context.operation_type == OperationType.FILE_OPERATION
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute file system compensation."""
        try:
            # Validate required compensation data
            if not self.validate_compensation_data(
                action.compensation_data,
                ['file_operations']
            ):
                return False
            
            file_operations = action.compensation_data.get('file_operations', [])
            
            for operation in file_operations:
                await self._execute_file_operation(operation)
            
            logger.info(f"File system compensation completed: {action.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"File system compensation error: {action.action_id}: {e}")
            return False
    
    async def _execute_file_operation(self, operation: dict) -> None:
        """Execute a single file operation."""
        op_type = operation.get('type')
        file_path = operation.get('file_path')
        
        if op_type == 'delete_file' and os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
            
        elif op_type == 'restore_file':
            backup_path = operation.get('backup_path')
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
                logger.debug(f"Restored file: {file_path}")
                
        elif op_type == 'delete_directory':
            if os.path.exists(file_path) and os.path.isdir(file_path):
                shutil.rmtree(file_path)
                logger.debug(f"Deleted directory: {file_path}")
        
        elif op_type == 'create_directory':
            if not os.path.exists(file_path):
                os.makedirs(file_path)
                logger.debug(f"Created directory: {file_path}")
    
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
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute cache compensation."""
        if not self.cache_manager:
            logger.warning("No cache manager available for compensation")
            return True  # Skip compensation
        
        try:
            # Validate required compensation data
            if not self.validate_compensation_data(
                action.compensation_data,
                ['cache_operations']
            ):
                return False
            
            cache_operations = action.compensation_data.get('cache_operations', [])
            
            for operation in cache_operations:
                await self._execute_cache_operation(operation)
            
            logger.info(f"Cache compensation completed: {action.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache compensation error: {action.action_id}: {e}")
            return False
    
    async def _execute_cache_operation(self, operation: dict) -> None:
        """Execute a single cache operation."""
        op_type = operation.get('type')
        cache_key = operation.get('cache_key')
        
        if op_type == 'invalidate' and cache_key:
            await self.cache_manager.delete(cache_key)
            logger.debug(f"Invalidated cache key: {cache_key}")
            
        elif op_type == 'restore' and cache_key:
            restore_value = operation.get('restore_value')
            if restore_value is not None:
                await self.cache_manager.set(cache_key, restore_value)
                logger.debug(f"Restored cache key: {cache_key}")
        
        elif op_type == 'clear_pattern':
            pattern = operation.get('pattern')
            if pattern:
                await self.cache_manager.clear_pattern(pattern)
                logger.debug(f"Cleared cache pattern: {pattern}")
    
    def get_priority(self) -> int:
        """Cache operations have low priority."""
        return 5


class ExternalServiceCompensationHandler(BaseCompensationHandler):
    """Handles compensation for external service calls."""
    
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if can compensate external API calls."""
        return context.operation_type == OperationType.EXTERNAL_API
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute external service compensation."""
        try:
            # Validate required compensation data
            if not self.validate_compensation_data(
                action.compensation_data,
                ['api_operations']
            ):
                return False
            
            import aiohttp
            
            api_operations = action.compensation_data.get('api_operations', [])
            
            async with aiohttp.ClientSession() as session:
                for operation in api_operations:
                    await self._execute_api_operation(session, operation)
            
            logger.info(f"External service compensation completed: {action.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"External service compensation error: {action.action_id}: {e}")
            return False
    
    async def _execute_api_operation(self, session, operation: dict) -> None:
        """Execute a single API compensation operation."""
        method = operation.get('method', 'POST')
        url = operation.get('url')
        data = operation.get('data', {})
        headers = operation.get('headers', {})
        
        if not url:
            return
        
        try:
            import aiohttp
            async with session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status < 400:
                    logger.debug(f"External compensation call succeeded: {url}")
                else:
                    logger.warning(
                        f"External compensation call failed: {url} "
                        f"(status: {response.status})"
                    )
        except Exception as e:
            logger.warning(f"External compensation call error: {url}: {e}")
    
    def get_priority(self) -> int:
        """External services have medium-low priority."""
        return 4


def create_default_handlers(cache_manager=None) -> list[BaseCompensationHandler]:
    """Create list of default compensation handlers."""
    return [
        DatabaseCompensationHandler(),
        FileSystemCompensationHandler(),
        CacheCompensationHandler(cache_manager),
        ExternalServiceCompensationHandler()
    ]