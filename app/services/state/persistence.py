"""State Persistence Service

Handles persisting state across different storage backends with proper abstraction.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import central_logger
from app.services.state.state_manager import StateManager, StateStorage
from app.services.database.unit_of_work import UnitOfWork
from app.agents.state import DeepAgentState
import json
import pickle
import base64

logger = central_logger.get_logger(__name__)

class StatePersistenceService:
    """Service for persisting agent and application state"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.state_prefix = "agent_state"
        self.thread_prefix = "thread_context"
        self.result_prefix = "agent_result"
    
    async def save_agent_state(self,
                              run_id: str,
                              thread_id: str,
                              user_id: str,
                              state: DeepAgentState,
                              uow: UnitOfWork) -> bool:
        """Save agent state with transaction support"""
        try:
            async with self.state_manager.transaction() as txn_id:
                state_key = f"{self.state_prefix}:{run_id}"
                state_data = {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "state": state.model_dump(),
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
                await self.state_manager.set(state_key, state_data, txn_id)
                
                thread_key = f"{self.thread_prefix}:{thread_id}"
                thread_context = await self.state_manager.get(thread_key, {})
                thread_context.update({
                    "current_run_id": run_id,
                    "user_id": user_id,
                    "last_updated": datetime.now(UTC).isoformat(),
                    "state_summary": self._create_state_summary(state)
                })
                
                await self.state_manager.set(thread_key, thread_context, txn_id)
                
                if uow and uow.session:
                    run = await uow.runs.get_by_id(uow.session, run_id)
                    if run:
                        run.metadata_ = run.metadata_ or {}
                        run.metadata_["state"] = state.model_dump()
                        run.metadata_["thread_id"] = thread_id
                        run.metadata_["user_id"] = user_id
                        await uow.commit()
                
                logger.info(f"Saved agent state for run {run_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save agent state for run {run_id}: {e}")
            if uow:
                await uow.rollback()
            return False
    
    async def load_agent_state(self,
                              run_id: str,
                              uow: Optional[UnitOfWork] = None) -> Optional[DeepAgentState]:
        """Load agent state from storage"""
        try:
            state_key = f"{self.state_prefix}:{run_id}"
            state_data = await self.state_manager.get(state_key)
            
            if state_data:
                logger.info(f"Loaded agent state for run {run_id} from cache")
                return DeepAgentState(**state_data["state"])
            
            if uow and uow.session:
                run = await uow.runs.get_by_id(uow.session, run_id)
                if run and run.metadata_ and "state" in run.metadata_:
                    state_dict = run.metadata_["state"]
                    logger.info(f"Loaded agent state for run {run_id} from database")
                    
                    await self.state_manager.set(state_key, {
                        "run_id": run_id,
                        "thread_id": run.thread_id,
                        "user_id": run.metadata_.get("user_id"),
                        "state": state_dict,
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                    
                    return DeepAgentState(**state_dict)
            
            logger.warning(f"No agent state found for run {run_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load agent state for run {run_id}: {e}")
            return None
    
    async def get_thread_context(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread context"""
        try:
            thread_key = f"{self.thread_prefix}:{thread_id}"
            return await self.state_manager.get(thread_key)
        except Exception as e:
            logger.error(f"Failed to get thread context for {thread_id}: {e}")
            return None
    
    async def save_sub_agent_result(self,
                                   run_id: str,
                                   agent_name: str,
                                   result: Dict[str, Any],
                                   uow: Optional[UnitOfWork] = None) -> bool:
        """Save individual sub-agent results"""
        try:
            result_key = f"{self.result_prefix}:{run_id}:{agent_name}"
            result_data = {
                "run_id": run_id,
                "agent_name": agent_name,
                "result": result,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            await self.state_manager.set(result_key, result_data)
            
            if uow and uow.session:
                reference_id = f"ref_{run_id}_{agent_name}"
                await uow.references.create_reference(
                    uow.session,
                    reference_id=reference_id,
                    reference_type="agent_result",
                    content=json.dumps(result),
                    metadata={
                        "run_id": run_id,
                        "agent_name": agent_name,
                        "created_at": datetime.now(UTC).isoformat()
                    }
                )
                await uow.commit()
            
            logger.info(f"Saved {agent_name} result for run {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save {agent_name} result for run {run_id}: {e}")
            if uow:
                await uow.rollback()
            return False
    
    async def get_sub_agent_result(self,
                                  run_id: str,
                                  agent_name: str,
                                  uow: Optional[UnitOfWork] = None) -> Optional[Dict[str, Any]]:
        """Get individual sub-agent results"""
        try:
            result_key = f"{self.result_prefix}:{run_id}:{agent_name}"
            result_data = await self.state_manager.get(result_key)
            
            if result_data:
                return result_data["result"]
            
            if uow and uow.session:
                reference_id = f"ref_{run_id}_{agent_name}"
                reference = await uow.references.get_by_id(uow.session, reference_id)
                if reference:
                    return json.loads(reference.content)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get {agent_name} result for run {run_id}: {e}")
            return None
    
    async def list_thread_runs(self,
                              thread_id: str,
                              uow: UnitOfWork,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """List all runs for a thread"""
        try:
            runs = await uow.runs.get_thread_runs(
                uow.session,
                thread_id,
                limit=limit
            )
            
            run_list = []
            for run in runs:
                state_key = f"{self.state_prefix}:{run.id}"
                has_cached_state = await self.state_manager.get(state_key) is not None
                
                run_info = {
                    "id": run.id,
                    "status": run.status,
                    "created_at": run.created_at,
                    "completed_at": run.completed_at,
                    "has_state": has_cached_state or "state" in (run.metadata_ or {}),
                    "cached": has_cached_state
                }
                run_list.append(run_info)
            
            return run_list
            
        except Exception as e:
            logger.error(f"Failed to list runs for thread {thread_id}: {e}")
            return []
    
    async def cleanup_old_states(self, days_old: int = 7) -> int:
        """Cleanup old state entries"""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            all_state = await self.state_manager.get_all()
            
            cleaned_count = 0
            for key, value in all_state.items():
                if key.startswith(self.state_prefix):
                    if isinstance(value, dict) and "timestamp" in value:
                        timestamp = datetime.fromisoformat(value["timestamp"])
                        if timestamp < cutoff_date:
                            await self.state_manager.delete(key)
                            cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old state entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old states: {e}")
            return 0
    
    async def export_state(self, run_id: str) -> Optional[str]:
        """Export state as base64 encoded string"""
        try:
            state = await self.load_agent_state(run_id)
            if state:
                serialized = pickle.dumps(state.model_dump())
                return base64.b64encode(serialized).decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Failed to export state for run {run_id}: {e}")
            return None
    
    async def import_state(self, run_id: str, encoded_state: str) -> bool:
        """Import state from base64 encoded string"""
        try:
            serialized = base64.b64decode(encoded_state.encode('utf-8'))
            state_dict = pickle.loads(serialized)
            state = DeepAgentState(**state_dict)
            
            state_key = f"{self.state_prefix}:{run_id}"
            await self.state_manager.set(state_key, {
                "run_id": run_id,
                "state": state.model_dump(),
                "timestamp": datetime.now(UTC).isoformat(),
                "imported": True
            })
            
            logger.info(f"Imported state for run {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import state for run {run_id}: {e}")
            return False
    
    def _create_state_summary(self, state: DeepAgentState) -> Dict[str, bool]:
        """Create a summary of state completeness"""
        return {
            "has_triage": state.triage_result is not None,
            "has_data": state.data_result is not None,
            "has_optimizations": state.optimizations_result is not None,
            "has_action_plan": state.action_plan_result is not None,
            "has_report": state.report_result is not None
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        all_state = await self.state_manager.get_all()
        
        stats = {
            "total_states": sum(1 for k in all_state.keys() if k.startswith(self.state_prefix)),
            "total_threads": sum(1 for k in all_state.keys() if k.startswith(self.thread_prefix)),
            "total_results": sum(1 for k in all_state.keys() if k.startswith(self.result_prefix)),
            "state_manager": self.state_manager.get_stats()
        }
        
        return stats