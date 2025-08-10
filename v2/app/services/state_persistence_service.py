"""Agent State Persistence Service

This service handles persisting agent state to Redis for fast access
and PostgreSQL for long-term storage and querying.
"""

import json
import time
from typing import Any, Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models_postgres import Run, Reference
from app.redis_manager import redis_manager
from app.logging_config import central_logger
from app.agents.state import DeepAgentState
import pickle

logger = central_logger.get_logger(__name__)

class StatePersistenceService:
    """Service for persisting and retrieving agent state"""
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.redis_ttl = 3600  # 1 hour TTL for Redis cache
    
    async def save_agent_state(
        self,
        run_id: str,
        thread_id: str,
        user_id: str,
        state: DeepAgentState,
        db_session: AsyncSession
    ) -> bool:
        """Save agent state to both Redis and PostgreSQL"""
        try:
            # Serialize state for storage
            state_dict = state.model_dump()
            state_json = json.dumps(state_dict)
            
            # Save to Redis for fast access
            redis_key = f"agent_state:{run_id}"
            redis_client = await self.redis_manager.get_client()
            if redis_client:
                await redis_client.set(
                    redis_key,
                    state_json,
                    ex=self.redis_ttl
                )
            
            # Also save thread context
            thread_key = f"thread_context:{thread_id}"
            thread_context = {
                "current_run_id": run_id,
                "user_id": user_id,
                "last_updated": time.time(),
                "state_summary": {
                    "has_triage": state.triage_result is not None,
                    "has_data": state.data_result is not None,
                    "has_optimizations": state.optimizations_result is not None,
                    "has_action_plan": state.action_plan_result is not None,
                    "has_report": state.report_result is not None
                }
            }
            if redis_client:
                await redis_client.set(
                    thread_key,
                    json.dumps(thread_context),
                    ex=self.redis_ttl * 24  # Keep thread context for 24 hours
                )
            
            # Update Run metadata in PostgreSQL
            if db_session:
                result = await db_session.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run:
                    run.metadata_ = run.metadata_ or {}
                    run.metadata_["state"] = state_dict
                    run.metadata_["thread_id"] = thread_id
                    run.metadata_["user_id"] = user_id
                    await db_session.commit()
                    logger.info(f"Persisted state for run {run_id} to database")
            
            logger.info(f"Successfully saved agent state for run {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save agent state for run {run_id}: {e}")
            return False
    
    async def load_agent_state(
        self,
        run_id: str,
        db_session: Optional[AsyncSession] = None
    ) -> Optional[DeepAgentState]:
        """Load agent state from Redis or PostgreSQL"""
        try:
            # Try Redis first
            redis_key = f"agent_state:{run_id}"
            redis_client = await self.redis_manager.get_client()
            state_json = None
            if redis_client:
                state_json = await redis_client.get(redis_key)
            
            if state_json:
                state_dict = json.loads(state_json)
                logger.info(f"Loaded agent state for run {run_id} from Redis")
                return DeepAgentState(**state_dict)
            
            # Fall back to PostgreSQL
            if db_session:
                result = await db_session.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run and run.metadata_ and "state" in run.metadata_:
                    state_dict = run.metadata_["state"]
                    logger.info(f"Loaded agent state for run {run_id} from database")
                    
                    # Re-cache in Redis
                    if redis_client:
                        await redis_client.set(
                            redis_key,
                            json.dumps(state_dict),
                            ex=self.redis_ttl
                        )
                    
                    return DeepAgentState(**state_dict)
            
            logger.warning(f"No agent state found for run {run_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load agent state for run {run_id}: {e}")
            return None
    
    async def get_thread_context(
        self,
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get thread context from Redis"""
        try:
            thread_key = f"thread_context:{thread_id}"
            redis_client = await self.redis_manager.get_client()
            context_json = None
            if redis_client:
                context_json = await redis_client.get(thread_key)
            
            if context_json:
                return json.loads(context_json)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get thread context for {thread_id}: {e}")
            return None
    
    async def save_sub_agent_result(
        self,
        run_id: str,
        agent_name: str,
        result: Dict[str, Any],
        db_session: Optional[AsyncSession] = None
    ) -> bool:
        """Save individual sub-agent results"""
        try:
            # Save to Redis with agent-specific key
            redis_key = f"agent_result:{run_id}:{agent_name}"
            redis_client = await self.redis_manager.get_client()
            if redis_client:
                await redis_client.set(
                    redis_key,
                    json.dumps(result),
                    ex=self.redis_ttl
                )
            
            # Also save as a Reference in PostgreSQL for querying
            if db_session:
                reference = Reference(
                    id=f"ref_{run_id}_{agent_name}",
                    name=f"{agent_name}_result_{run_id[:8]}",
                    friendly_name=f"{agent_name} Result",
                    description=f"Result from {agent_name} for run {run_id}",
                    type="agent_result",
                    value=json.dumps(result),
                    version="1.0"
                )
                db_session.add(reference)
                await db_session.commit()
                logger.info(f"Saved {agent_name} result for run {run_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save {agent_name} result for run {run_id}: {e}")
            if db_session:
                await db_session.rollback()
            return False
    
    async def get_sub_agent_result(
        self,
        run_id: str,
        agent_name: str,
        db_session: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """Get individual sub-agent results"""
        try:
            # Try Redis first
            redis_key = f"agent_result:{run_id}:{agent_name}"
            redis_client = await self.redis_manager.get_client()
            result_json = None
            if redis_client:
                result_json = await redis_client.get(redis_key)
            
            if result_json:
                return json.loads(result_json)
            
            # Fall back to PostgreSQL
            if db_session:
                result = await db_session.execute(
                    select(Reference).where(
                        Reference.id == f"ref_{run_id}_{agent_name}"
                    )
                )
                reference = result.scalar_one_or_none()
                if reference:
                    return json.loads(reference.content)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get {agent_name} result for run {run_id}: {e}")
            return None
    
    async def list_thread_runs(
        self,
        thread_id: str,
        db_session: AsyncSession,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List all runs for a thread"""
        try:
            result = await db_session.execute(
                select(Run)
                .where(Run.thread_id == thread_id)
                .order_by(Run.created_at.desc())
                .limit(limit)
            )
            runs = result.scalars().all()
            
            run_list = []
            for run in runs:
                run_info = {
                    "id": run.id,
                    "status": run.status,
                    "created_at": run.created_at,
                    "completed_at": run.completed_at,
                    "has_state": "state" in (run.metadata_ or {})
                }
                run_list.append(run_info)
            
            return run_list
            
        except Exception as e:
            logger.error(f"Failed to list runs for thread {thread_id}: {e}")
            return []

# Global instance
state_persistence_service = StatePersistenceService()