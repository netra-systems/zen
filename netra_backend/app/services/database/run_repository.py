"""Run Repository Implementation

Handles all run-related database operations.
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Run
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

logger = central_logger.get_logger(__name__)

class RunRepository(BaseRepository[Run]):
    """Repository for Run entities"""
    
    def __init__(self):
        super().__init__(Run)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[Run]:
        """Find runs by user through thread relationship"""
        from netra_backend.app.db.models_postgres import Thread
        
        try:
            result = await db.execute(
                select(Run).join(Thread, Run.thread_id == Thread.id).where(
                    Thread.metadata_.op('->>')('user_id') == user_id
                ).order_by(desc(Run.created_at))
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding runs for user {user_id}: {e}")
            return []
    
    async def create_run(self,
                        db: AsyncSession,
                        thread_id: str,
                        assistant_id: str,
                        model: str = LLMModel.GEMINI_2_5_FLASH.value,
                        instructions: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[Run]:
        """Create a new run"""
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        return await self.create(
            db=db,
            id=UnifiedIDManager.generate_run_id(thread_id),
            object="thread.run",
            created_at=int(time.time()),
            thread_id=thread_id,
            assistant_id=assistant_id,
            status="in_progress",
            model=model,
            instructions=instructions,
            tools=[],
            file_ids=[],
            metadata_=metadata or {}
        )
    
    async def get_thread_runs(self,
                             db: AsyncSession,
                             thread_id: str,
                             limit: int = 10,
                             status_filter: Optional[str] = None) -> List[Run]:
        """Get runs for a thread with optional status filtering"""
        try:
            query = select(Run).where(Run.thread_id == thread_id)
            
            if status_filter:
                query = query.where(Run.status == status_filter)
            
            query = query.order_by(desc(Run.created_at)).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting runs for thread {thread_id}: {e}")
            return []
    
    async def update_status(self,
                          db: AsyncSession,
                          run_id: str,
                          status: str,
                          error: Optional[Dict[str, Any]] = None) -> Optional[Run]:
        """Update run status with proper timestamps"""
        run = await self.get_by_id(db, run_id)
        if not run:
            return None
        
        run.status = status
        
        if error:
            run.last_error = error
        
        if status == "completed":
            run.completed_at = int(time.time())
        elif status == "failed":
            run.failed_at = int(time.time())
        elif status == "cancelled":
            run.cancelled_at = int(time.time())
        
        try:
            await db.commit()
            await db.refresh(run)
            logger.info(f"Updated run {run_id} status to {status}")
            return run
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating run {run_id} status: {e}")
            return None
    
    async def get_active_runs(self, db: AsyncSession) -> List[Run]:
        """Get all currently active runs"""
        try:
            result = await db.execute(
                select(Run).where(
                    Run.status.in_(["in_progress", "queued", "requires_action"])
                ).order_by(Run.created_at)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting active runs: {e}")
            return []
    
    async def cancel_thread_runs(self, db: AsyncSession, thread_id: str) -> int:
        """Cancel all active runs for a thread"""
        try:
            active_runs = await self.get_thread_runs(
                db, thread_id, status_filter="in_progress"
            )
            
            cancelled_count = 0
            for run in active_runs:
                if await self.update_status(db, run.id, "cancelled"):
                    cancelled_count += 1
            
            return cancelled_count
        except Exception as e:
            logger.error(f"Error cancelling runs for thread {thread_id}: {e}")
            return 0