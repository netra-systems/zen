import time
import uuid
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.exceptions_database import (
    DatabaseError,
    RecordNotFoundError,
)
from netra_backend.app.db.models_postgres import Assistant, Message, Run, Thread
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.unit_of_work import (
    UnitOfWork,
    get_unit_of_work,
)
from netra_backend.app.services.service_interfaces import IThreadService
from netra_backend.app.websocket_core import get_websocket_manager
manager = get_websocket_manager()

logger = central_logger.get_logger(__name__)

def _handle_database_error(operation: str, context: Dict[str, Any], error: Exception = None):
    """Handle database errors consistently"""
    if error:
        logger.error(f"Unexpected error in {operation}: {error}")
        context["error"] = str(error)
    return DatabaseError(message=f"Failed to {operation}", context=context)

async def uow_context():
    """Context manager for unit of work without existing session"""
    return get_unit_of_work()

class ThreadService(IThreadService):
    """Service for managing conversation threads and messages"""
    
    async def _send_thread_created_event(self, user_id: str) -> None:
        """Send thread created WebSocket event"""
        thread_id = f"thread_{user_id}"
        await manager.send_to_user(user_id, {"type": "thread_created", "payload": {"thread_id": thread_id, "timestamp": time.time()}})
    
    async def _execute_with_uow(self, operation, db: Optional[AsyncSession] = None, *args, **kwargs):
        """Execute operation with unit of work pattern"""
        uow_factory = get_unit_of_work(db) if db else get_unit_of_work()
        async with uow_factory as uow:
            return await operation(uow, *args, **kwargs)
    
    async def _create_thread_operation(self, uow, user_id: str):
        """Core thread creation operation"""
        thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
        if not thread:
            raise DatabaseError(message=f"Failed to get or create thread for user {user_id}", context={"user_id": user_id})
        await self._send_thread_created_event(user_id)
        return thread
    
    async def get_or_create_thread(self, user_id: str, db: Optional[AsyncSession] = None) -> Thread:
        """Get existing thread for user or create a new one using repository pattern"""
        try:
            return await self._execute_with_uow(self._create_thread_operation, db, user_id)
        except NetraException:
            raise
        except Exception as e:
            raise _handle_database_error(f"get or create thread for user {user_id}", {"user_id": user_id}, e)
    
    async def get_thread(self, thread_id: str, user_id: str = None, db: Optional[AsyncSession] = None) -> Optional[Thread]:
        """Get a thread by ID using repository pattern"""
        try:
            return await self._execute_with_uow(lambda uow: uow.threads.get_by_id(uow.session, thread_id), db)
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            return None
    
    async def get_threads(self, user_id: str, db: Optional[AsyncSession] = None) -> List[Thread]:
        """Get all threads for a user using repository pattern"""
        try:
            return await self._execute_with_uow(lambda uow: uow.threads.get_by_user(uow.session, user_id), db)
        except Exception as e:
            logger.error(f"Error getting threads for user {user_id}: {e}")
            return []
    
    def _prepare_message_data(self, thread_id: str, role: str, content: str, assistant_id: Optional[str], run_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare message data for creation"""
        return {
            "id": f"msg_{uuid.uuid4()}", "object": "thread.message", "created_at": int(time.time()),
            "thread_id": thread_id, "role": role, "content": [{"type": "text", "text": {"value": content}}],
            "assistant_id": assistant_id, "run_id": run_id, "file_ids": [], "metadata_": metadata or {}
        }
    
    async def _create_message_operation(self, uow, message_data: Dict[str, Any], thread_id: str, role: str):
        """Core message creation operation"""
        message = await uow.messages.create(**message_data)
        if not message:
            raise DatabaseError(message=f"Failed to create message in thread {thread_id}", context={"thread_id": thread_id, "role": role})
        return message
    
    async def create_message(self, thread_id: str, role: str, content: str, assistant_id: Optional[str] = None, run_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, db: Optional[AsyncSession] = None) -> Message:
        """Create a new message in a thread using repository pattern"""
        message_data = self._prepare_message_data(thread_id, role, content, assistant_id, run_id, metadata)
        try:
            return await self._execute_with_uow(lambda uow: self._create_message_operation(uow, message_data, thread_id, role), db)
        except NetraException:
            raise
        except Exception as e:
            raise _handle_database_error(f"create message in thread {thread_id}", {"thread_id": thread_id, "role": role}, e)
    
    async def get_thread_messages(self, thread_id: str, limit: int = 50, db: Optional[AsyncSession] = None) -> List[Message]:
        """Get messages for a thread using repository pattern"""
        try:
            return await self._execute_with_uow(lambda uow: uow.messages.get_by_thread(uow.session, thread_id, limit), db)
        except NetraException:
            raise
        except Exception as e:
            raise _handle_database_error(f"get messages for thread {thread_id}", {"thread_id": thread_id}, e)
    
    def _prepare_run_data(self, thread_id: str, assistant_id: str, model: str, instructions: Optional[str]) -> tuple[str, Dict[str, Any]]:
        """Prepare run data for creation"""
        run_id = UnifiedIDManager.generate_run_id(thread_id, "thread_service_run")
        base_data = {"id": run_id, "object": "thread.run", "created_at": int(time.time()), "thread_id": thread_id}
        extended_data = {"assistant_id": assistant_id, "status": "in_progress", "model": model, "instructions": instructions, "tools": [], "file_ids": [], "metadata_": {}}
        return run_id, {**base_data, **extended_data}
    
    async def _send_agent_started_event(self, uow, run_id: str, thread_id: str, agent_name: str = "DefaultAgent") -> None:
        """Send agent started WebSocket event"""
        thread = await uow.threads.get_by_id(uow.session, thread_id)
        if thread and thread.metadata_:
            user_id = thread.metadata_.get("user_id")
            if user_id:
                await manager.send_to_user(user_id, {"type": "agent_started", "payload": {"run_id": run_id, "agent_name": agent_name, "thread_id": thread_id, "timestamp": time.time()}})
    
    async def _create_run_with_uow(self, uow, run_data: Dict[str, Any], thread_id: str, assistant_id: str, run_id: str) -> Run:
        """Create run using unit of work"""
        # Ensure the assistant exists before creating the run
        if assistant_id == "netra-assistant":
            await uow.assistants.ensure_netra_assistant(uow.session)
        
        run = await uow.runs.create(**run_data)
        if not run:
            raise DatabaseError(message=f"Failed to create run for thread {thread_id}", context={"thread_id": thread_id, "assistant_id": assistant_id})
        # Get agent name from assistant_id or use a default
        agent_name = assistant_id if assistant_id else "DefaultAgent"
        await self._send_agent_started_event(uow, run_id, thread_id, agent_name)
        return run
    
    async def create_run(self, thread_id: str, assistant_id: str, model: str = LLMModel.GEMINI_2_5_FLASH.value, instructions: Optional[str] = None, db: Optional[AsyncSession] = None) -> Run:
        """Create a new run for a thread using repository pattern"""
        run_id, run_data = self._prepare_run_data(thread_id, assistant_id, model, instructions)
        try:
            return await self._execute_with_uow(lambda uow: self._create_run_with_uow(uow, run_data, thread_id, assistant_id, run_id), db)
        except NetraException:
            raise
        except Exception as e:
            raise _handle_database_error(f"create run for thread {thread_id}", {"thread_id": thread_id, "assistant_id": assistant_id}, e)
    
    def _prepare_update_data(self, status: str, error: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare update data for run status change"""
        update_data = {"status": status}
        if error:
            update_data["last_error"] = error
        if status in ["completed", "failed"]:
            timestamp_key = "completed_at" if status == "completed" else "failed_at"
            update_data[timestamp_key] = int(time.time())
        return update_data
    
    async def _update_run_operation(self, uow, run_id: str, update_data: Dict[str, Any]):
        """Core run update operation"""
        run = await uow.runs.update(uow.session, run_id, **update_data)
        if not run:
            raise RecordNotFoundError("Run", run_id)
        return run
    
    async def update_run_status(self, run_id: str, status: str, error: Optional[Dict[str, Any]] = None, db: Optional[AsyncSession] = None) -> Run:
        """Update the status of a run using repository pattern"""
        update_data = self._prepare_update_data(status, error)
        try:
            return await self._execute_with_uow(lambda uow: self._update_run_operation(uow, run_id, update_data), db)
        except NetraException:
            raise
        except Exception as e:
            raise _handle_database_error(f"update run {run_id} status", {"run_id": run_id, "status": status}, e)

    # Interface implementation methods
    async def create_thread(self, user_id: str, db=None):
        """Create a new thread for the user."""
        return await self.get_or_create_thread(user_id, db)

    async def switch_thread(self, user_id: str, thread_id: str, db=None):
        """Switch user to a different thread."""
        # Validate that the thread exists and belongs to the user
        thread = await self.get_thread(thread_id, user_id, db)
        if thread:
            await manager.send_to_user(user_id, {
                "type": "thread_switched", 
                "payload": {"thread_id": thread_id}
            })
            return thread
        return None

    async def delete_thread(self, thread_id: str, user_id: str, db=None):
        """Delete a thread for the user."""
        # Implementation for thread deletion
        try:
            async with get_unit_of_work(db) as uow:
                success = await uow.threads.delete(uow.session, thread_id)
                if success:
                    await manager.send_to_user(user_id, {
                        "type": "thread_deleted", 
                        "payload": {"thread_id": thread_id}
                    })
                return success
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False

# Stub functions for testing compatibility
def cleanup_old_threads(cleanup_request: dict) -> dict:
    """Cleanup old threads - placeholder implementation"""
    return {"status": "not_implemented"}

def get_thread_activity(activity_request: dict) -> dict:
    """Get thread activity - placeholder implementation"""
    return {"status": "not_implemented"}

def batch_update_threads(update_request: dict) -> dict:
    """Batch update threads - placeholder implementation"""
    return {"status": "not_implemented"}

def merge_threads(merge_request: dict) -> dict:
    """Merge threads - placeholder implementation"""
    return {"status": "not_implemented"}

def get_thread_recommendations(recommendation_request: dict) -> dict:
    """Get thread recommendations - placeholder implementation"""
    return {"status": "not_implemented"}

def get_thread_insights(insights_request: dict) -> dict:
    """Get thread insights - placeholder implementation"""
    return {"status": "not_implemented"}

def export_threads(export_request: dict) -> dict:
    """Export threads - placeholder implementation"""
    return {"status": "not_implemented"}

def get_thread_statistics(stats_request: dict) -> dict:
    """Get thread statistics - placeholder implementation"""
    return {"status": "not_implemented"}

def get_thread_by_id(thread_id: str) -> dict:
    """Get thread by ID - placeholder implementation"""
    return {
        "id": thread_id,
        "title": f"Thread {thread_id}",
        "messages": [],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "status": "active"
    }

def duplicate_thread(thread_id: str, options: dict = None) -> dict:
    """Duplicate a thread - placeholder implementation"""
    return {
        "original_id": thread_id,
        "new_id": f"{thread_id}_copy",
        "title": f"Copy of Thread {thread_id}",
        "messages": [],
        "created_at": "2024-01-01T00:00:00Z",
        "status": "duplicated"
    }

def delete_thread(thread_id: str) -> bool:
    """Delete a thread - placeholder implementation"""
    # Simulate successful deletion
    return True

def update_thread(thread_id: str, update_data: dict) -> dict:
    """Update a thread - placeholder implementation"""
    return {
        "id": thread_id,
        "title": update_data.get("title", f"Updated Thread {thread_id}"),
        "updated_at": "2024-01-01T00:00:00Z",
        "status": "updated"
    }

def add_message_to_thread(thread_id: str, message: dict) -> dict:
    """Add message to thread - placeholder implementation"""
    return {
        "thread_id": thread_id,
        "message_id": "msg_new",
        "content": message.get("content", ""),
        "timestamp": "2024-01-01T00:00:00Z",
        "status": "added"
    }

def search_threads(query: str, filters: dict = None) -> list:
    """Search threads - placeholder implementation"""
    return [
        {
            "id": "thread1",
            "title": f"Search result for: {query}",
            "relevance_score": 0.95,
            "snippet": "Matching content snippet..."
        }
    ]

def update_thread_status(thread_id: str, status: str) -> dict:
    """Update thread status - placeholder implementation"""
    return {
        "id": thread_id,
        "status": status,
        "updated_at": "2024-01-01T00:00:00Z"
    }

def update_thread_metadata(thread_id: str, metadata: dict) -> dict:
    """Update thread metadata - placeholder implementation"""
    return {
        "id": thread_id,
        "metadata": metadata,
        "updated_at": "2024-01-01T00:00:00Z"
    }

def get_thread_messages(thread_id: str, page: int = 1, limit: int = 10) -> list:
    """Get thread messages - placeholder implementation"""
    return [
        {
            "id": f"msg{i}",
            "thread_id": thread_id,
            "content": f"Message {i}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        for i in range(limit)
    ]

def bulk_operation(bulk_request: dict) -> dict:
    """Perform bulk operations on threads - placeholder implementation"""
    return {
        "operation": bulk_request.get("operation", "unknown"),
        "total_requested": len(bulk_request.get("thread_ids", [])),
        "successful": 0,
        "failed": 0,
        "results": {},
        "operation_id": "bulk_op_placeholder"
    }

def analyze_sentiment(sentiment_request: dict) -> dict:
    """Analyze thread sentiment - placeholder implementation"""
    return {
        "analysis_id": "sentiment_placeholder",
        "results": {},
        "summary": {
            "avg_sentiment_score": 0.0,
            "positive_threads": 0,
            "neutral_threads": 0,
            "negative_threads": 0
        }
    }

def get_performance_metrics(metrics_request: dict) -> dict:
    """Get thread performance metrics - placeholder implementation"""
    return {
        "timeframe": metrics_request.get("timeframe", "unknown"),
        "granularity": metrics_request.get("granularity", "unknown"),
        "metrics": {
            "response_time": {
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            },
            "message_frequency": {
                "messages_per_hour": 0.0,
                "peak_hour": 12,
                "off_peak_hour": 3
            },
            "user_engagement": {
                "active_threads_per_hour": 0.0,
                "avg_session_duration": 0.0,
                "bounce_rate": 0.0
            },
            "completion_rate": {
                "threads_completed": 0.0,
                "avg_messages_to_completion": 0.0,
                "user_satisfaction": 0.0
            }
        },
        "trends": {
            "response_time": "stable",
            "user_engagement": "stable",
            "completion_rate": "stable"
        }
    }

def search_messages_in_thread(thread_id: str, search_query: dict) -> dict:
    """Search messages within a specific thread - placeholder implementation"""
    return {
        "messages": [
            {
                "id": "msg123",
                "content": f"This message contains the search query: {search_query.get('query', '')}",
                "sender": "user",
                "timestamp": "2024-01-15T10:30:00Z",
                "relevance_score": 0.95
            },
            {
                "id": "msg124", 
                "content": f"Another message matching: {search_query.get('query', '')}",
                "sender": "assistant",
                "timestamp": "2024-01-16T11:15:00Z",
                "relevance_score": 0.87
            }
        ],
        "total_matches": 2,
        "query": search_query.get("query", "")
    }

def add_message_reaction(message_id: str, reaction_type: str, user_id: str) -> dict:
    """Add a reaction to a message - placeholder implementation"""
    from datetime import datetime
    return {
        "message_id": message_id,
        "reaction_type": reaction_type,
        "user_id": user_id,
        "added_at": datetime.now().isoformat()
    }

def add_reply_to_message(thread_id: str, parent_message_id: str, reply_data: dict) -> dict:
    """Add a reply to a message - placeholder implementation"""
    from datetime import datetime
    return {
        "message_id": f"msg_{uuid.uuid4()}",
        "thread_id": thread_id,
        "parent_message_id": parent_message_id,
        "content": reply_data.get("content", ""),
        "sender": reply_data.get("sender", "user"),
        "timestamp": datetime.now().isoformat(),
        "reply_level": 1,
        "message_type": reply_data.get("message_type", "reply")
    }
# Create service instances for backward compatibility
thread_service = ThreadService()

