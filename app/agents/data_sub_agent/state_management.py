"""State management for DataSubAgent."""

import pickle
from typing import Dict, Any, Optional
from datetime import datetime

from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger


class StateManagementMixin:
    """Mixin providing state management capabilities."""
    
    async def save_state(self) -> None:
        """Save agent state for recovery and persistence"""
        self._prepare_state_for_saving()
        try:
            await self._persist_state_to_redis()
            logger.info(f"Saved state for {self.agent_type}")
        except Exception as e:
            await self._handle_state_save_error(e)
    
    def _prepare_state_for_saving(self) -> None:
        """Prepare state data for saving."""
        # Initialize state if needed
        if not hasattr(self, 'state'):
            self.state = {}
        
        # Create saved state copy
        self._saved_state = getattr(self, 'state', {}).copy()
    
    async def _persist_state_to_redis(self) -> None:
        """Persist state data to Redis."""
        redis_manager = RedisManager()
        state_key = self._get_state_key()
        state_data = self._build_state_data()
        serialized_data = pickle.dumps(state_data)
        await redis_manager.set(state_key, serialized_data, expire=86400)
    
    def _get_state_key(self) -> str:
        """Get Redis key for state storage."""
        return f"agent:state:{self.agent_type}:{getattr(self, 'agent_id', 'default')}"
    
    def _build_state_data(self) -> Dict[str, Any]:
        """Build state data dictionary for serialization."""
        return {
            'state': self._saved_state,
            'agent_type': self.agent_type,
            'timestamp': datetime.now().isoformat(),
            'checkpoints': getattr(self, '_checkpoints', [])
        }
    
    async def load_state(self) -> None:
        """Load agent state from storage"""
        try:
            state_data = await self._fetch_state_from_redis()
            await self._process_loaded_state(state_data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self._initialize_empty_state()
    
    async def _fetch_state_from_redis(self) -> Optional[bytes]:
        """Fetch state data from Redis."""
        redis_manager = RedisManager()
        state_key = self._get_state_key()
        return await redis_manager.get(state_key)
    
    def _deserialize_and_restore_state(self, state_data: bytes) -> None:
        """Deserialize state data and restore state."""
        loaded_data = pickle.loads(state_data)
        self._restore_state_data(loaded_data)
        self._restore_checkpoints(loaded_data)
        self._log_state_loaded(loaded_data)
    
    def _restore_state_data(self, loaded_data: Dict[str, Any]) -> None:
        """Restore main state data."""
        self._saved_state = loaded_data.get('state', {})
        self.state = self._saved_state.copy()
    
    def _restore_checkpoints(self, loaded_data: Dict[str, Any]) -> None:
        """Restore checkpoints if available."""
        if 'checkpoints' in loaded_data:
            self._checkpoints = loaded_data['checkpoints']
    
    def _log_state_loaded(self, loaded_data: Dict[str, Any]) -> None:
        """Log that state was successfully loaded."""
        logger.info(f"Loaded state for {self.agent_type} from {loaded_data.get('timestamp')}")
    
    def _initialize_empty_state(self) -> None:
        """Initialize empty state as fallback."""
        self._saved_state = {}
        self.state = {}
        self._checkpoints = []
    
    async def recover(self) -> None:
        """Recover from failure and resume from checkpoint"""
        await self.load_state()
        await self._recover_incomplete_tasks()
        await self._resume_from_checkpoint()
    
    async def _recover_incomplete_tasks(self) -> None:
        """Recover and resume incomplete tasks from state."""
        if not self._has_incomplete_tasks():
            return
        incomplete = self.state['incomplete_tasks']
        logger.info(f"Recovering {len(incomplete)} incomplete tasks")
        await self._process_incomplete_tasks(incomplete)
        await self._clear_incomplete_tasks_after_recovery()
    
    async def _process_incomplete_tasks(self, incomplete_tasks: list) -> None:
        """Process all incomplete tasks with error handling."""
        for task in incomplete_tasks:
            try:
                await self._resume_task(task)
            except Exception as e:
                logger.error(f"Failed to resume task {task.get('id')}: {e}")
    
    async def _clear_incomplete_tasks_after_recovery(self) -> None:
        """Clear incomplete tasks after recovery attempt."""
        self.state['incomplete_tasks'] = []
        await self.save_state()
    
    async def _resume_from_checkpoint(self) -> None:
        """Resume from the latest checkpoint if available."""
        if not self._has_available_checkpoints():
            return
        latest_checkpoint = self._checkpoints[-1]
        timestamp = latest_checkpoint.get('timestamp')
        logger.info(f"Resuming from checkpoint: {timestamp}")
    
    async def _resume_task(self, task: Dict[str, Any]) -> None:
        """Resume an incomplete task"""
        task_type = task.get('type', 'unknown')
        task_data = task.get('data', {})
        
        await self._dispatch_task_by_type(task_type, task_data)
    
    async def _dispatch_task_by_type(self, task_type: str, task_data: Dict[str, Any]) -> None:
        """Dispatch task based on type."""
        if task_type == 'process_data':
            await self.process_data(task_data)
        elif task_type == 'batch':
            await self.process_batch(task_data.get('items', []))
        else:
            logger.warning(f"Unknown task type for recovery: {task_type}")
    
    async def _handle_state_save_error(self, error: Exception) -> None:
        """Handle state saving errors with fallback."""
        logger.error(f"Failed to persist state: {error}")
        # Keep in-memory state as fallback
    
    async def _process_loaded_state(self, state_data: Optional[bytes]) -> None:
        """Process loaded state data or initialize empty state."""
        if state_data:
            self._deserialize_and_restore_state(state_data)
        else:
            self._initialize_empty_state()
    
    def _has_incomplete_tasks(self) -> bool:
        """Check if there are incomplete tasks to recover."""
        has_state = hasattr(self, 'state') and 'incomplete_tasks' in self.state
        if not has_state:
            return False
        return bool(self.state['incomplete_tasks'])
    
    def _has_available_checkpoints(self) -> bool:
        """Check if checkpoints are available for resumption."""
        return hasattr(self, '_checkpoints') and bool(self._checkpoints)