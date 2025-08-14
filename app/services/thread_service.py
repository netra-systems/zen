from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database.unit_of_work import UnitOfWork, get_unit_of_work
from app.core.exceptions_database import DatabaseError, RecordNotFoundError
from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity
from app.db.models_postgres import Thread, Message, Assistant, Run
from app.logging_config import central_logger
from app.ws_manager import manager
import uuid
import time

logger = central_logger.get_logger(__name__)

class ThreadService:
    """Service for managing conversation threads and messages"""
    
    async def get_or_create_thread(self, user_id: str, db: Optional[AsyncSession] = None) -> Thread:
        """Get existing thread for user or create a new one using repository pattern"""
        try:
            if db:
                # Use provided session
                async with get_unit_of_work(db) as uow:
                    thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
                    if not thread:
                        raise DatabaseError(
                            message=f"Failed to get or create thread for user {user_id}",
                            context={"user_id": user_id}
                        )
                    
                    # Send thread_created event if it's new
                    thread_id = f"thread_{user_id}"
                    await manager.send_message(
                        user_id,
                        {
                            "type": "thread_created",
                            "payload": {
                                "thread_id": thread_id,
                                "timestamp": time.time()
                            }
                        }
                    )
                    return thread
            else:
                # Create new UnitOfWork
                async with get_unit_of_work() as uow:
                    thread = await uow.threads.get_or_create_for_user(uow.session, user_id)
                    if not thread:
                        raise DatabaseError(
                            message=f"Failed to get or create thread for user {user_id}",
                            context={"user_id": user_id}
                        )
                    
                    # Send thread_created event if it's new
                    thread_id = f"thread_{user_id}"
                    await manager.send_message(
                        user_id,
                        {
                            "type": "thread_created",
                            "payload": {
                                "thread_id": thread_id,
                                "timestamp": time.time()
                            }
                        }
                    )
                    return thread
                    
        except NetraException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_or_create_thread for user {user_id}: {e}")
            raise DatabaseError(
                message=f"Failed to get or create thread for user {user_id}",
                context={"user_id": user_id, "error": str(e)}
            )
    
    async def get_thread(self, thread_id: str, db: Optional[AsyncSession] = None) -> Optional[Thread]:
        """Get a thread by ID using repository pattern"""
        try:
            if db:
                async with get_unit_of_work(db) as uow:
                    return await uow.threads.get_by_id(db, thread_id)
            else:
                async with uow_context() as uow:
                    return await uow.threads.get_by_id(uow.session, thread_id)
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            return None
    
    async def create_message(
        self, 
        thread_id: str,
        role: str,
        content: str,
        assistant_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Message:
        """Create a new message in a thread using repository pattern"""
        try:
            message_data = {
                "id": f"msg_{uuid.uuid4()}",
                "object": "thread.message",
                "created_at": int(time.time()),
                "thread_id": thread_id,
                "role": role,
                "content": [{"type": "text", "text": {"value": content}}],
                "assistant_id": assistant_id,
                "run_id": run_id,
                "file_ids": [],
                "metadata_": metadata or {}
            }
            
            if db:
                # Use provided session
                async with get_unit_of_work(db) as uow:
                    message = await uow.messages.create(**message_data)
                    if not message:
                        raise DatabaseError(
                            message=f"Failed to create message in thread {thread_id}",
                            context={"thread_id": thread_id, "role": role}
                        )
                    return message
            else:
                # Create new UnitOfWork
                async with get_unit_of_work() as uow:
                    message = await uow.messages.create(**message_data)
                    if not message:
                        raise DatabaseError(
                            message=f"Failed to create message in thread {thread_id}",
                            context={"thread_id": thread_id, "role": role}
                        )
                    return message
                    
        except NetraException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating message in thread {thread_id}: {e}")
            raise DatabaseError(
                message=f"Failed to create message in thread {thread_id}",
                context={"thread_id": thread_id, "role": role, "error": str(e)}
            )
    
    async def get_thread_messages(
        self,
        thread_id: str,
        limit: int = 50,
        db: Optional[AsyncSession] = None
    ) -> List[Message]:
        """Get messages for a thread using repository pattern"""
        try:
            if db:
                # Use provided session
                async with get_unit_of_work(db) as uow:
                    messages = await uow.messages.get_by_thread(uow.session, thread_id, limit)
                    return messages
            else:
                # Create new UnitOfWork
                async with get_unit_of_work() as uow:
                    messages = await uow.messages.get_by_thread(uow.session, thread_id, limit)
                    return messages
                    
        except NetraException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting messages for thread {thread_id}: {e}")
            raise DatabaseError(
                message=f"Failed to get messages for thread {thread_id}",
                context={"thread_id": thread_id, "error": str(e)}
            )
    
    async def create_run(
        self,
        thread_id: str,
        assistant_id: str,
        model: str = "gpt-4",
        instructions: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Run:
        """Create a new run for a thread using repository pattern"""
        try:
            run_id = f"run_{uuid.uuid4()}"
            run_data = {
                "id": run_id,
                "object": "thread.run",
                "created_at": int(time.time()),
                "thread_id": thread_id,
                "assistant_id": assistant_id,
                "status": "in_progress",
                "model": model,
                "instructions": instructions,
                "tools": [],
                "file_ids": [],
                "metadata_": {}
            }
            
            if db:
                # Use provided session
                async with get_unit_of_work(db) as uow:
                    run = await uow.runs.create(**run_data)
                    if not run:
                        raise DatabaseError(
                            message=f"Failed to create run for thread {thread_id}",
                            context={"thread_id": thread_id, "assistant_id": assistant_id}
                        )
                    
                    # Get thread to extract user_id for WebSocket event
                    thread = await uow.threads.get_by_id(uow.session, thread_id)
                    if thread and thread.metadata_:
                        user_id = thread.metadata_.get("user_id")
                        if user_id:
                            await manager.send_message(
                                user_id,
                                {
                                    "type": "agent_started",
                                    "payload": {
                                        "run_id": run_id,
                                        "thread_id": thread_id,
                                        "timestamp": time.time()
                                    }
                                }
                            )
                    return run
            else:
                # Create new UnitOfWork
                async with get_unit_of_work() as uow:
                    run = await uow.runs.create(**run_data)
                    if not run:
                        raise DatabaseError(
                            message=f"Failed to create run for thread {thread_id}",
                            context={"thread_id": thread_id, "assistant_id": assistant_id}
                        )
                    
                    # Get thread to extract user_id for WebSocket event
                    thread = await uow.threads.get_by_id(uow.session, thread_id)
                    if thread and thread.metadata_:
                        user_id = thread.metadata_.get("user_id")
                        if user_id:
                            await manager.send_message(
                                user_id,
                                {
                                    "type": "agent_started",
                                    "payload": {
                                        "run_id": run_id,
                                        "thread_id": thread_id,
                                        "timestamp": time.time()
                                    }
                                }
                            )
                    return run
                    
        except NetraException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating run for thread {thread_id}: {e}")
            raise DatabaseError(
                message=f"Failed to create run for thread {thread_id}",
                context={"thread_id": thread_id, "assistant_id": assistant_id, "error": str(e)}
            )
    
    async def update_run_status(
        self,
        run_id: str,
        status: str,
        error: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Run:
        """Update the status of a run using repository pattern"""
        try:
            update_data = {"status": status}
            
            if error:
                update_data["last_error"] = error
            if status == "completed":
                update_data["completed_at"] = int(time.time())
            elif status == "failed":
                update_data["failed_at"] = int(time.time())
            
            if db:
                # Use provided session
                async with get_unit_of_work(db) as uow:
                    run = await uow.runs.update(uow.session, run_id, **update_data)
                    if not run:
                        raise RecordNotFoundError("Run", run_id)
                    return run
            else:
                # Create new UnitOfWork
                async with get_unit_of_work() as uow:
                    run = await uow.runs.update(uow.session, run_id, **update_data)
                    if not run:
                        raise RecordNotFoundError("Run", run_id)
                    return run
                    
        except NetraException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating run {run_id} status: {e}")
            raise DatabaseError(
                message=f"Failed to update run {run_id} status",
                context={"run_id": run_id, "status": status, "error": str(e)}
            )