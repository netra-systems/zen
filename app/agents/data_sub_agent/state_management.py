"""State management for DataSubAgent."""

import pickle
from typing import Dict, Any
from datetime import datetime

from app.redis_manager import RedisManager
from app.logging_config import central_logger as logger


class StateManagementMixin:
    """Mixin providing state management capabilities."""
    
    async def save_state(self) -> None:
        """Save agent state for recovery and persistence"""
        
        # Initialize state if needed
        if not hasattr(self, 'state'):
            self.state = {}
        
        # Create saved state copy
        self._saved_state = getattr(self, 'state', {}).copy()
        
        try:
            # Persist to Redis for distributed recovery
            redis_manager = RedisManager()
            state_key = f"agent:state:{self.agent_type}:{getattr(self, 'agent_id', 'default')}"
            
            # Serialize state
            state_data = {
                'state': self._saved_state,
                'agent_type': self.agent_type,
                'timestamp': datetime.now().isoformat(),
                'checkpoints': getattr(self, '_checkpoints', [])
            }
            
            await redis_manager.set(
                state_key,
                pickle.dumps(state_data),
                expire=86400  # 24 hour TTL
            )
            
            logger.info(f"Saved state for {self.agent_type}")
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
            # Keep in-memory state as fallback
    
    async def load_state(self) -> None:
        """Load agent state from storage"""
        
        try:
            # Try to load from Redis
            redis_manager = RedisManager()
            state_key = f"agent:state:{self.agent_type}:{getattr(self, 'agent_id', 'default')}"
            
            state_data = await redis_manager.get(state_key)
            
            if state_data:
                # Deserialize state
                loaded_data = pickle.loads(state_data)
                self._saved_state = loaded_data.get('state', {})
                self.state = self._saved_state.copy()
                
                # Restore checkpoints if available
                if 'checkpoints' in loaded_data:
                    self._checkpoints = loaded_data['checkpoints']
                
                logger.info(f"Loaded state for {self.agent_type} from {loaded_data.get('timestamp')}")
            else:
                # Initialize empty state
                self._saved_state = {}
                self.state = {}
                self._checkpoints = []
                
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            # Initialize with empty state as fallback
            self._saved_state = {}
            self.state = {}
            self._checkpoints = []
    
    async def recover(self) -> None:
        """Recover from failure and resume from checkpoint"""
        await self.load_state()
        
        # Check for incomplete tasks in state
        if hasattr(self, 'state') and 'incomplete_tasks' in self.state:
            incomplete = self.state['incomplete_tasks']
            if incomplete:
                logger.info(f"Recovering {len(incomplete)} incomplete tasks")
                
                # Resume incomplete tasks
                for task in incomplete:
                    try:
                        # Re-queue task for processing
                        await self._resume_task(task)
                    except Exception as e:
                        logger.error(f"Failed to resume task {task.get('id')}: {e}")
                
                # Clear incomplete tasks after recovery attempt
                self.state['incomplete_tasks'] = []
                await self.save_state()
        
        # Restore any active connections or resources
        if hasattr(self, '_checkpoints') and self._checkpoints:
            latest_checkpoint = self._checkpoints[-1]
            logger.info(f"Resuming from checkpoint: {latest_checkpoint.get('timestamp')}")
    
    async def _resume_task(self, task: Dict[str, Any]) -> None:
        """Resume an incomplete task"""
        task_type = task.get('type', 'unknown')
        task_data = task.get('data', {})
        
        # Dispatch based on task type
        if task_type == 'process_data':
            await self.process_data(task_data)
        elif task_type == 'batch':
            await self.process_batch(task_data.get('items', []))
        else:
            logger.warning(f"Unknown task type for recovery: {task_type}")