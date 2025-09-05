# Team E: Implementation Agent - Checkpoint System for ReportingSubAgent

## COPY THIS ENTIRE PROMPT:

You are implementing the checkpoint system for ReportingSubAgent resilience, integrating with recent SSOT consolidations.

CRITICAL: You must be aware of recent SSOT changes including unified classes, consolidated managers, and the factory pattern architecture.

## MANDATORY FIRST ACTIONS:

1. READ `USER_CONTEXT_ARCHITECTURE.md` - Factory patterns and unified architecture
2. READ `netra_backend/app/agents/supervisor/agent_registry.py` - Unified registry patterns
3. READ `netra_backend/app/websocket_core/unified_manager.py` - Unified WebSocket manager
4. READ `netra_backend/app/websocket_core/unified_emitter.py` - WebSocket emitter
5. READ `SPEC/learnings/ssot_consolidation_20250825.xml` - Recent consolidations
6. VERIFY these unified classes exist:
   - `netra_backend/app/agents/triage/unified_triage_agent.py` - UnifiedTriageAgent
   - `netra_backend/app/agents/data/unified_data_agent.py` - UnifiedDataAgent
   - `test_framework/unified_docker_manager.py` - UnifiedDockerManager

## RECENT SSOT CONTEXT:

Based on recent consolidations (VERIFIED TO EXIST):
- **UnifiedDataAgent** at `netra_backend/app/agents/data/unified_data_agent.py`
- **UnifiedTriageAgent** at `netra_backend/app/agents/triage/unified_triage_agent.py`  
- **UnifiedDockerManager** at `test_framework/unified_docker_manager.py`
- **UnifiedWebSocketManager** at `netra_backend/app/websocket_core/unified_manager.py`
- **EnhancedToolExecutionEngine** at `netra_backend/app/agents/unified_tool_execution.py`
- **AgentWebSocketBridge** at `netra_backend/app/services/agent_websocket_bridge.py`
- **Factory pattern** is MANDATORY for all agent creation
- **AgentRegistry** provides centralized agent management

## YOUR CHECKPOINT IMPLEMENTATION TASK:

### 1. Checkpoint Manager Implementation

```python
# Location: netra_backend/app/agents/reporting_checkpoint_manager.py

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import asyncio

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.services.cache.redis_manager import get_redis_manager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer
)

logger = central_logger.get_logger(__name__)


class ReportCheckpointManager:
    """Manages report generation checkpoints for resilience
    
    SSOT compliant checkpoint system that:
    - Integrates with unified Redis manager
    - Uses factory pattern for instance creation
    - Maintains user isolation via UserExecutionContext
    - Supports atomic operations
    """
    
    CHECKPOINT_TTL = 3600  # 1 hour
    KEY_PREFIX = "report_checkpoint"
    
    def __init__(self, context: UserExecutionContext):
        """Initialize with user context for isolation
        
        Args:
            context: User execution context for proper isolation
        """
        self.context = context
        self.user_id = context.user_id
        self.run_id = context.run_id
        self.redis_manager = None  # Lazy init
        self._lock = asyncio.Lock()
        
        # Use unified JSON handler for serialization
        self.json_parser = LLMResponseParser()
        self.json_fixer = JSONErrorFixer()
        
    async def _ensure_redis(self):
        """Ensure Redis connection using unified manager"""
        if not self.redis_manager:
            # Use SSOT Redis manager pattern
            self.redis_manager = await get_redis_manager()
            
    def _generate_key(self, section: str) -> str:
        """Generate checkpoint key with user isolation
        
        Pattern: report_checkpoint:user_id:run_id:section
        """
        return f"{self.KEY_PREFIX}:{self.user_id}:{self.run_id}:{section}"
    
    def _generate_progress_key(self) -> str:
        """Generate progress tracking key"""
        return f"{self.KEY_PREFIX}:progress:{self.user_id}:{self.run_id}"
    
    async def save_section(self, section: str, content: Dict[str, Any]) -> bool:
        """Save a report section checkpoint atomically
        
        Args:
            section: Section name (e.g., 'summary', 'data_analysis')
            content: Section content to save
            
        Returns:
            bool: True if saved successfully
        """
        async with self._lock:
            try:
                await self._ensure_redis()
                
                # Serialize content (handle Pydantic models)
                if hasattr(content, 'model_dump'):
                    content = content.model_dump(mode='json', exclude_none=True)
                elif hasattr(content, 'dict'):
                    content = content.dict(exclude_none=True)
                
                # Create checkpoint data
                checkpoint = {
                    'section': section,
                    'content': content,
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': self.user_id,
                    'run_id': self.run_id
                }
                
                # Save atomically with TTL
                key = self._generate_key(section)
                await self.redis_manager.setex(
                    key,
                    self.CHECKPOINT_TTL,
                    json.dumps(checkpoint)
                )
                
                # Update progress tracking
                await self._update_progress(section, 'completed')
                
                logger.info(f"Checkpoint saved: {section} for run {self.run_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint {section}: {e}")
                return False
    
    async def load_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Load a specific section checkpoint
        
        Args:
            section: Section name to load
            
        Returns:
            Section content if exists, None otherwise
        """
        try:
            await self._ensure_redis()
            
            key = self._generate_key(section)
            data = await self.redis_manager.get(key)
            
            if data:
                checkpoint = json.loads(data)
                logger.info(f"Checkpoint loaded: {section} for run {self.run_id}")
                return checkpoint['content']
                
        except Exception as e:
            logger.warning(f"Failed to load checkpoint {section}: {e}")
            
        return None
    
    async def load_all_sections(self) -> Dict[str, Any]:
        """Load all checkpoints for current report
        
        Returns:
            Dict mapping section names to content
        """
        sections = {}
        
        try:
            await self._ensure_redis()
            
            # Get all checkpoint keys for this run
            pattern = f"{self.KEY_PREFIX}:{self.user_id}:{self.run_id}:*"
            keys = await self.redis_manager.keys(pattern)
            
            # Load each checkpoint
            for key in keys:
                section = key.split(':')[-1]
                content = await self.load_section(section)
                if content:
                    sections[section] = content
            
            logger.info(f"Loaded {len(sections)} checkpoints for run {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to load checkpoints: {e}")
            
        return sections
    
    async def get_progress(self) -> Dict[str, Any]:
        """Get current progress status
        
        Returns:
            Progress information including completed sections
        """
        try:
            await self._ensure_redis()
            
            key = self._generate_progress_key()
            data = await self.redis_manager.get(key)
            
            if data:
                return json.loads(data)
            
            return {
                'completed_sections': [],
                'in_progress': None,
                'total_sections': 0,
                'last_update': None
            }
            
        except Exception as e:
            logger.warning(f"Failed to get progress: {e}")
            return {}
    
    async def _update_progress(self, section: str, status: str):
        """Update progress tracking"""
        try:
            progress = await self.get_progress()
            
            if status == 'completed':
                if section not in progress['completed_sections']:
                    progress['completed_sections'].append(section)
                if progress['in_progress'] == section:
                    progress['in_progress'] = None
            elif status == 'in_progress':
                progress['in_progress'] = section
            
            progress['last_update'] = datetime.utcnow().isoformat()
            
            key = self._generate_progress_key()
            await self.redis_manager.setex(
                key,
                self.CHECKPOINT_TTL,
                json.dumps(progress)
            )
            
        except Exception as e:
            logger.warning(f"Failed to update progress: {e}")
    
    async def cleanup(self) -> bool:
        """Clean up all checkpoints after successful completion
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            await self._ensure_redis()
            
            # Get all checkpoint keys
            pattern = f"{self.KEY_PREFIX}:{self.user_id}:{self.run_id}:*"
            keys = await self.redis_manager.keys(pattern)
            
            # Add progress key
            keys.append(self._generate_progress_key())
            
            # Delete all keys
            if keys:
                await self.redis_manager.delete(*keys)
                
            logger.info(f"Cleaned up {len(keys)} checkpoints for run {self.run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")
            return False
    
    async def has_checkpoints(self) -> bool:
        """Check if any checkpoints exist for current run
        
        Returns:
            bool: True if checkpoints exist
        """
        try:
            await self._ensure_redis()
            
            pattern = f"{self.KEY_PREFIX}:{self.user_id}:{self.run_id}:*"
            keys = await self.redis_manager.keys(pattern)
            
            return len(keys) > 0
            
        except Exception as e:
            logger.warning(f"Failed to check checkpoints: {e}")
            return False
    
    async def get_checkpoint_age(self) -> Optional[float]:
        """Get age of oldest checkpoint in seconds
        
        Returns:
            Age in seconds, None if no checkpoints
        """
        try:
            progress = await self.get_progress()
            if progress.get('last_update'):
                last_update = datetime.fromisoformat(progress['last_update'])
                age = (datetime.utcnow() - last_update).total_seconds()
                return age
                
        except Exception as e:
            logger.warning(f"Failed to get checkpoint age: {e}")
            
        return None


class CheckpointFactory:
    """Factory for creating checkpoint managers per request
    
    Ensures proper isolation and SSOT compliance
    """
    
    @staticmethod
    def create_for_context(context: UserExecutionContext) -> ReportCheckpointManager:
        """Create checkpoint manager for user context
        
        Args:
            context: User execution context
            
        Returns:
            Configured checkpoint manager
        """
        return ReportCheckpointManager(context)
```

### 2. Integration with ReportingSubAgent

```python
# ADD to ReportingSubAgent class:

from netra_backend.app.agents.reporting_checkpoint_manager import CheckpointFactory

class ReportingSubAgent(BaseAgent):
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        # Existing init...
        
        # ADD: Checkpoint manager (lazy init)
        self._checkpoint_manager = None
        
    def _get_checkpoint_manager(self) -> ReportCheckpointManager:
        """Get or create checkpoint manager using factory"""
        if not self._checkpoint_manager and self._user_context:
            self._checkpoint_manager = CheckpointFactory.create_for_context(
                self._user_context
            )
        return self._checkpoint_manager
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with checkpoint support"""
        
        # Check for existing checkpoints
        checkpoint_mgr = self._get_checkpoint_manager()
        if checkpoint_mgr and await checkpoint_mgr.has_checkpoints():
            self.logger.info("Found existing checkpoints, resuming...")
            return await self._resume_from_checkpoints(context, stream_updates)
        
        # Normal execution with checkpoint saves
        return await self._execute_with_checkpoints(context, stream_updates)
    
    async def _execute_with_checkpoints(self, context: UserExecutionContext, 
                                       stream_updates: bool) -> Dict[str, Any]:
        """Execute with checkpoint saves at each section"""
        
        checkpoint_mgr = self._get_checkpoint_manager()
        sections = {}
        
        try:
            # Generate sections with checkpoints
            for section_name in ['summary', 'data_analysis', 'recommendations', 'action_items']:
                if stream_updates:
                    await self.emit_thinking(f"Generating {section_name}...")
                
                # Generate section
                section_content = await self._generate_section(section_name, context)
                sections[section_name] = section_content
                
                # Save checkpoint
                if checkpoint_mgr:
                    await checkpoint_mgr.save_section(section_name, section_content)
            
            # Success - cleanup checkpoints
            if checkpoint_mgr:
                await checkpoint_mgr.cleanup()
            
            return {
                'success': True,
                'report': sections,
                'checkpoints_used': False
            }
            
        except Exception as e:
            # Checkpoints remain for retry
            self.logger.error(f"Report generation failed, checkpoints preserved: {e}")
            raise
    
    async def _resume_from_checkpoints(self, context: UserExecutionContext,
                                      stream_updates: bool) -> Dict[str, Any]:
        """Resume report generation from checkpoints"""
        
        checkpoint_mgr = self._get_checkpoint_manager()
        
        # Load existing sections
        sections = await checkpoint_mgr.load_all_sections()
        
        if stream_updates:
            await self.emit_thinking(f"Resumed from {len(sections)} checkpoints...")
        
        # Determine remaining sections
        all_sections = ['summary', 'data_analysis', 'recommendations', 'action_items']
        remaining = [s for s in all_sections if s not in sections]
        
        # Generate remaining sections
        for section_name in remaining:
            if stream_updates:
                await self.emit_thinking(f"Generating remaining section: {section_name}")
            
            section_content = await self._generate_section(section_name, context)
            sections[section_name] = section_content
            
            # Save checkpoint
            await checkpoint_mgr.save_section(section_name, section_content)
        
        # Cleanup on success
        await checkpoint_mgr.cleanup()
        
        return {
            'success': True,
            'report': sections,
            'checkpoints_used': True,
            'resumed_sections': len(sections) - len(remaining)
        }
```

### 3. Integration with Unified Systems

```python
# Integration points with unified systems:

# 1. AgentRegistry integration
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

registry = AgentRegistry()
registry.register_agent('reporting', ReportingSubAgent)

# 2. Unified WebSocket integration
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

websocket_mgr = UnifiedWebSocketManager()
await websocket_mgr.emit_event('checkpoint_saved', {'section': section_name})

# 3. Unified Docker (for testing)
from netra_backend.app.core.docker.unified_docker_manager import UnifiedDockerManager

docker_mgr = UnifiedDockerManager()
await docker_mgr.ensure_redis()  # Ensure Redis for checkpoints
```

## DELIVERABLES:

1. **reporting_checkpoint_manager.py** - Complete checkpoint implementation
2. **checkpoint_integration.py** - Integration with ReportingSubAgent  
3. **test_checkpoint_system.py** - Comprehensive tests
4. **checkpoint_monitoring.py** - Metrics and monitoring

## VALIDATION CHECKLIST:

- [ ] Uses factory pattern for creation
- [ ] Integrates with UserExecutionContext
- [ ] Uses unified Redis manager
- [ ] Atomic checkpoint operations
- [ ] TTL enforced (1 hour)
- [ ] User isolation maintained
- [ ] Cleanup after success
- [ ] Resume capability works
- [ ] Performance < 100ms overhead
- [ ] Integrates with unified systems
- [ ] No global state
- [ ] Thread-safe operations

Remember: Checkpoints must integrate with ALL recent SSOT consolidations and unified systems.