"""Compensation engine for handling partial failures in distributed operations.

Provides saga pattern implementation with automatic compensation for failed
distributed transactions across multiple services and data stores.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable, Union

from app.core.error_recovery import OperationType, RecoveryContext
from app.services.transaction_manager import transaction_manager
from app.services.database.rollback_manager import rollback_manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CompensationState(Enum):
    """States of compensation operations."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SagaState(Enum):
    """States of saga execution."""
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class CompensationAction:
    """Represents a compensation action for a failed operation."""
    action_id: str
    operation_id: str
    action_type: str
    compensation_data: Dict[str, Any]
    handler: Callable[..., Awaitable[bool]]
    state: CompensationState = CompensationState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SagaStep:
    """Represents a step in a saga with forward and compensation actions."""
    step_id: str
    name: str
    forward_action: Callable[..., Awaitable[Any]]
    compensation_action: Callable[..., Awaitable[bool]]
    forward_params: Dict[str, Any] = field(default_factory=dict)
    compensation_params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    executed: bool = False
    compensated: bool = False
    error: Optional[str] = None


@dataclass
class Saga:
    """Represents a saga transaction with multiple steps."""
    saga_id: str
    name: str
    steps: List[SagaStep] = field(default_factory=list)
    state: SagaState = SagaState.RUNNING
    created_at: datetime = field(default_factory=datetime.now)
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if saga has expired."""
        return datetime.now() - self.created_at > self.timeout
    
    @property
    def executed_steps(self) -> List[SagaStep]:
        """Get all executed steps."""
        return [step for step in self.steps if step.executed]
    
    @property
    def failed_steps(self) -> List[SagaStep]:
        """Get all failed steps."""
        return [step for step in self.steps if step.error is not None]


class BaseCompensationHandler(ABC):
    """Abstract base class for compensation handlers."""
    
    @abstractmethod
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if this handler can compensate the given operation."""
        pass
    
    @abstractmethod
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute the compensation action."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get handler priority (lower number = higher priority)."""
        pass


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
            # Create rollback session
            session_id = await self.rollback_manager.create_rollback_session({
                'compensation_action_id': action.action_id,
                'original_operation_id': action.operation_id
            })
            
            # Add rollback operations from compensation data
            rollback_ops = action.compensation_data.get('rollback_operations', [])
            for rollback_op in rollback_ops:
                await self.rollback_manager.add_rollback_operation(
                    session_id=session_id,
                    table_name=rollback_op['table_name'],
                    operation_type=rollback_op['operation_type'],
                    rollback_data=rollback_op['rollback_data']
                )
            
            # Execute rollback
            success = await self.rollback_manager.execute_rollback_session(session_id)
            
            if success:
                logger.info(f"Database compensation completed: {action.action_id}")
            else:
                logger.error(f"Database compensation failed: {action.action_id}")
            
            return success
            
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
    
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute file system compensation."""
        try:
            import os
            import shutil
            
            file_operations = action.compensation_data.get('file_operations', [])
            
            for operation in file_operations:
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
            cache_operations = action.compensation_data.get('cache_operations', [])
            
            for operation in cache_operations:
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
            
            logger.info(f"Cache compensation completed: {action.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cache compensation error: {action.action_id}: {e}")
            return False
    
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
            import aiohttp
            
            api_operations = action.compensation_data.get('api_operations', [])
            
            async with aiohttp.ClientSession() as session:
                for operation in api_operations:
                    method = operation.get('method', 'POST')
                    url = operation.get('url')
                    data = operation.get('data', {})
                    headers = operation.get('headers', {})
                    
                    if not url:
                        continue
                    
                    try:
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
            
            logger.info(f"External service compensation completed: {action.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"External service compensation error: {action.action_id}: {e}")
            return False
    
    def get_priority(self) -> int:
        """External services have medium-low priority."""
        return 4


class CompensationEngine:
    """Engine for executing compensation actions."""
    
    def __init__(self):
        """Initialize compensation engine."""
        self.handlers: List[BaseCompensationHandler] = []
        self.active_compensations: Dict[str, CompensationAction] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default compensation handlers."""
        self.handlers = [
            DatabaseCompensationHandler(),
            FileSystemCompensationHandler(),
            CacheCompensationHandler(),
            ExternalServiceCompensationHandler(),
        ]
        
        # Sort by priority
        self.handlers.sort(key=lambda h: h.get_priority())
    
    def register_handler(self, handler: BaseCompensationHandler) -> None:
        """Register a new compensation handler."""
        self.handlers.append(handler)
        self.handlers.sort(key=lambda h: h.get_priority())
    
    async def create_compensation_action(
        self,
        operation_id: str,
        context: RecoveryContext,
        compensation_data: Dict[str, Any]
    ) -> str:
        """Create a new compensation action."""
        action_id = str(uuid.uuid4())
        
        # Find appropriate handler
        handler = None
        for h in self.handlers:
            if await h.can_compensate(context):
                handler = h
                break
        
        if not handler:
            logger.warning(f"No compensation handler found for operation: {operation_id}")
            return action_id
        
        action = CompensationAction(
            action_id=action_id,
            operation_id=operation_id,
            action_type=context.operation_type.value,
            compensation_data=compensation_data,
            handler=handler.execute_compensation,
            metadata={
                'context': context,
                'handler_class': type(handler).__name__
            }
        )
        
        self.active_compensations[action_id] = action
        logger.debug(f"Created compensation action: {action_id}")
        return action_id
    
    async def execute_compensation(self, action_id: str) -> bool:
        """Execute a specific compensation action."""
        action = self.active_compensations.get(action_id)
        if not action:
            logger.error(f"Compensation action not found: {action_id}")
            return False
        
        action.state = CompensationState.EXECUTING
        
        try:
            context = action.metadata.get('context')
            success = await action.handler(action, context)
            
            if success:
                action.state = CompensationState.COMPLETED
                action.executed_at = datetime.now()
                logger.info(f"Compensation action completed: {action_id}")
            else:
                action.state = CompensationState.FAILED
                logger.error(f"Compensation action failed: {action_id}")
            
            return success
            
        except Exception as e:
            action.state = CompensationState.FAILED
            action.error = str(e)
            logger.error(f"Compensation action error: {action_id}: {e}")
            return False
    
    async def execute_batch_compensation(
        self,
        action_ids: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, bool]:
        """Execute multiple compensation actions concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(action_id: str) -> tuple[str, bool]:
            async with semaphore:
                result = await self.execute_compensation(action_id)
                return action_id, result
        
        tasks = [execute_with_semaphore(action_id) for action_id in action_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        compensation_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch compensation error: {result}")
                continue
            
            action_id, success = result
            compensation_results[action_id] = success
        
        success_count = sum(1 for success in compensation_results.values() if success)
        logger.info(
            f"Batch compensation completed",
            total_actions=len(action_ids),
            successes=success_count,
            failures=len(action_ids) - success_count
        )
        
        return compensation_results


class SagaOrchestrator:
    """Orchestrator for saga pattern transactions."""
    
    def __init__(self, compensation_engine: CompensationEngine):
        """Initialize saga orchestrator."""
        self.compensation_engine = compensation_engine
        self.active_sagas: Dict[str, Saga] = {}
    
    async def create_saga(
        self,
        name: str,
        steps: List[SagaStep],
        metadata: Optional[Dict] = None
    ) -> str:
        """Create a new saga."""
        saga_id = str(uuid.uuid4())
        saga = Saga(
            saga_id=saga_id,
            name=name,
            steps=steps,
            metadata=metadata or {}
        )
        
        self.active_sagas[saga_id] = saga
        logger.info(f"Created saga: {saga_id} ({name})")
        return saga_id
    
    async def execute_saga(self, saga_id: str) -> bool:
        """Execute a saga with automatic compensation on failure."""
        saga = self.active_sagas.get(saga_id)
        if not saga:
            logger.error(f"Saga not found: {saga_id}")
            return False
        
        logger.info(f"Executing saga: {saga_id} ({saga.name})")
        
        try:
            # Execute forward steps
            for step_idx, step in enumerate(saga.steps):
                try:
                    logger.debug(f"Executing saga step: {step.name}")
                    
                    step.result = await step.forward_action(**step.forward_params)
                    step.executed = True
                    
                    logger.debug(f"Saga step completed: {step.name}")
                    
                except Exception as e:
                    step.error = str(e)
                    logger.error(f"Saga step failed: {step.name}: {e}")
                    
                    # Start compensation
                    saga.state = SagaState.COMPENSATING
                    compensation_success = await self._compensate_saga(
                        saga, step_idx - 1
                    )
                    
                    if compensation_success:
                        saga.state = SagaState.ABORTED
                        logger.info(f"Saga aborted with successful compensation: {saga_id}")
                    else:
                        saga.state = SagaState.FAILED
                        logger.error(f"Saga failed with compensation errors: {saga_id}")
                    
                    return False
            
            # All steps completed successfully
            saga.state = SagaState.COMPLETED
            logger.info(f"Saga completed successfully: {saga_id}")
            return True
            
        except Exception as e:
            saga.state = SagaState.FAILED
            logger.error(f"Saga execution error: {saga_id}: {e}")
            return False
        finally:
            # Clean up saga
            await self._cleanup_saga(saga_id)
    
    async def _compensate_saga(self, saga: Saga, last_executed_step: int) -> bool:
        """Execute compensation for executed steps in reverse order."""
        logger.info(f"Starting saga compensation: {saga.saga_id}")
        
        compensation_success = True
        
        # Compensate in reverse order
        for step_idx in range(last_executed_step, -1, -1):
            step = saga.steps[step_idx]
            
            if not step.executed:
                continue
            
            try:
                logger.debug(f"Compensating saga step: {step.name}")
                
                success = await step.compensation_action(**step.compensation_params)
                step.compensated = success
                
                if success:
                    logger.debug(f"Saga step compensation completed: {step.name}")
                else:
                    logger.error(f"Saga step compensation failed: {step.name}")
                    compensation_success = False
                
            except Exception as e:
                logger.error(f"Saga step compensation error: {step.name}: {e}")
                compensation_success = False
        
        if compensation_success:
            logger.info(f"Saga compensation completed successfully: {saga.saga_id}")
        else:
            logger.error(f"Saga compensation had failures: {saga.saga_id}")
        
        return compensation_success
    
    async def _cleanup_saga(self, saga_id: str) -> None:
        """Clean up saga resources."""
        if saga_id in self.active_sagas:
            del self.active_sagas[saga_id]
    
    def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get status of saga execution."""
        saga = self.active_sagas.get(saga_id)
        if not saga:
            return None
        
        return {
            'saga_id': saga_id,
            'name': saga.name,
            'state': saga.state.value,
            'total_steps': len(saga.steps),
            'executed_steps': len(saga.executed_steps),
            'failed_steps': len(saga.failed_steps),
            'created_at': saga.created_at.isoformat(),
            'is_expired': saga.is_expired
        }


# Global instances
compensation_engine = CompensationEngine()
saga_orchestrator = SagaOrchestrator(compensation_engine)