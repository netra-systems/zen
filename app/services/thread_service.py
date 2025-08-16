from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database.unit_of_work import UnitOfWork, get_unit_of_work
from app.services.service_locator import IThreadService
from app.core.exceptions_database import DatabaseError, RecordNotFoundError
from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity
from app.db.models_postgres import Thread, Message, Assistant, Run
from app.logging_config import central_logger
from app.ws_manager import manager
import uuid
import time

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
        await manager.send_message(user_id, {"type": "thread_created", "payload": {"thread_id": thread_id, "timestamp": time.time()}})
    
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
    
    async def get_thread(self, thread_id: str, db: Optional[AsyncSession] = None) -> Optional[Thread]:
        """Get a thread by ID using repository pattern"""
        try:
            return await self._execute_with_uow(lambda uow: uow.threads.get_by_id(uow.session, thread_id), db)
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            return None
    
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
        run_id = f"run_{uuid.uuid4()}"
        base_data = {"id": run_id, "object": "thread.run", "created_at": int(time.time()), "thread_id": thread_id}
        extended_data = {"assistant_id": assistant_id, "status": "in_progress", "model": model, "instructions": instructions, "tools": [], "file_ids": [], "metadata_": {}}
        return run_id, {**base_data, **extended_data}
    
    async def _send_agent_started_event(self, uow, run_id: str, thread_id: str) -> None:
        """Send agent started WebSocket event"""
        thread = await uow.threads.get_by_id(uow.session, thread_id)
        if thread and thread.metadata_:
            user_id = thread.metadata_.get("user_id")
            if user_id:
                await manager.send_message(user_id, {"type": "agent_started", "payload": {"run_id": run_id, "thread_id": thread_id, "timestamp": time.time()}})
    
    async def _create_run_with_uow(self, uow, run_data: Dict[str, Any], thread_id: str, assistant_id: str, run_id: str) -> Run:
        """Create run using unit of work"""
        run = await uow.runs.create(**run_data)
        if not run:
            raise DatabaseError(message=f"Failed to create run for thread {thread_id}", context={"thread_id": thread_id, "assistant_id": assistant_id})
        await self._send_agent_started_event(uow, run_id, thread_id)
        return run
    
    async def create_run(self, thread_id: str, assistant_id: str, model: str = "gpt-4", instructions: Optional[str] = None, db: Optional[AsyncSession] = None) -> Run:
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
        thread = await self.get_thread(thread_id, db)
        if thread:
            await manager.send_message(user_id, {
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
                    await manager.send_message(user_id, {
                        "type": "thread_deleted", 
                        "payload": {"thread_id": thread_id}
                    })
                return success
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False