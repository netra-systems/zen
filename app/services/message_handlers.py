from typing import Dict, Any, Optional, List, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from app.db.models_postgres import Thread, Run

if TYPE_CHECKING:
    from app.agents.supervisor import SupervisorAgent
from app.services.thread_service import ThreadService
from app.schemas.websocket_types import (
    UserMessagePayload,
    CreateThreadPayload,
    SwitchThreadPayload,
    DeleteThreadPayload,
    ThreadHistoryResponse,
    AgentCompletedPayload,
    AgentStoppedPayload
)
from app.ws_manager import manager
import json

logger = central_logger.get_logger(__name__)

class MessageHandlerService:
    """Handles different types of WebSocket messages following conventions"""
    
    def __init__(self, supervisor: 'SupervisorAgent', thread_service: ThreadService):
        self.supervisor = supervisor
        self.thread_service = thread_service
    
    async def handle_start_agent(
        self,
        user_id: str,
        payload: Dict[str, Any],
        db_session: AsyncSession
    ) -> None:
        """Handle start_agent message type"""
        user_request = self._extract_user_request(payload)
        thread = await self._get_or_validate_thread(user_id, payload, db_session)
        if not thread:
            return
        await self._process_agent_request(user_id, user_request, thread, db_session)
    
    def _extract_user_request(self, payload: Dict[str, Any]) -> str:
        """Extract user request from payload"""
        request_data = payload.get("request", {})
        return request_data.get("query", "") or request_data.get("user_request", "")
    
    async def _get_or_validate_thread(
        self, user_id: str, payload: Dict[str, Any], db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get or validate thread for user"""
        thread_id = payload.get("thread_id", None)
        if thread_id:
            thread = await self._validate_thread_access(user_id, thread_id, db_session)
            if thread:
                return thread
        return await self._get_or_create_thread(user_id, db_session)
    
    async def _validate_thread_access(
        self, user_id: str, thread_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Validate user has access to thread"""
        thread = await self.thread_service.get_thread(thread_id, db_session)
        if thread and thread.metadata_.get("user_id") != user_id:
            await manager.send_error(user_id, "Access denied to thread")
            return None
        return thread
    
    async def _get_or_create_thread(
        self, user_id: str, db_session: AsyncSession
    ) -> Optional[Thread]:
        """Get or create thread for user"""
        thread = await self.thread_service.get_or_create_thread(user_id, db_session)
        if not thread:
            await manager.send_error(user_id, "Failed to create or retrieve thread")
        return thread
    
    async def _process_agent_request(
        self, user_id: str, user_request: str, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Process the agent request"""
        await self._create_user_message(thread, user_request, user_id, db_session)
        run = await self._create_run(thread, db_session)
        self._configure_supervisor(user_id, thread, db_session)
        response = await self._execute_supervisor(user_request, thread, user_id, run)
        await self._save_response(thread, response, run, db_session)
        await self._complete_run(run, db_session)
        await self._send_completion(user_id, response)
    
    async def _create_user_message(
        self, thread: Thread, content: str, user_id: str, db_session: AsyncSession
    ) -> None:
        """Create user message in thread"""
        await self.thread_service.create_message(
            thread.id, role="user", content=content,
            metadata={"user_id": user_id}, db=db_session
        )
    
    async def _create_run(
        self, thread: Thread, db_session: AsyncSession
    ) -> Run:
        """Create run for thread"""
        return await self.thread_service.create_run(
            thread.id, assistant_id="netra-assistant", model="gpt-4",
            instructions="You are Netra AI Workload Optimization Assistant",
            db=db_session
        )
    
    def _configure_supervisor(self, user_id: str, thread: Thread, db_session: AsyncSession) -> None:
        """Configure supervisor with context"""
        self.supervisor.thread_id = thread.id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = db_session
    
    async def _execute_supervisor(
        self, user_request: str, thread: Thread, user_id: str, run: Run
    ) -> Any:
        """Execute supervisor run"""
        return await self.supervisor.run(user_request, thread.id, user_id, run.id)
    
    async def _save_response(
        self, thread: Thread, response: Any, run: Run, db_session: AsyncSession
    ) -> None:
        """Save assistant response if present"""
        if not response:
            return
        content = json.dumps(response) if isinstance(response, dict) else str(response)
        await self.thread_service.create_message(
            thread.id, role="assistant", content=content,
            assistant_id="netra-assistant", run_id=run.id, db=db_session
        )
    
    async def _complete_run(self, run: Run, db_session: AsyncSession) -> None:
        """Mark run as completed"""
        await self.thread_service.update_run_status(
            run.id, status="completed", db=db_session
        )
    
    async def _send_completion(self, user_id: str, response: Any) -> None:
        """Send completion message to user"""
        await manager.send_message(
            user_id, {"type": "agent_completed", "payload": response}
        )
    
    async def handle_user_message(
        self,
        user_id: str,
        payload: UserMessagePayload,
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle user_message type"""
        text = payload.get("text", "")
        references = payload.get("references", [])
        thread_id = payload.get("thread_id", None)  # Get thread_id from payload
        logger.info(f"Received user message from {user_id}: {text}, thread_id: {thread_id}")
        
        thread = None
        run = None
        
        if db_session:
            try:
                # If thread_id provided, use it; otherwise get_or_create
                if thread_id:
                    thread = await self.thread_service.get_thread(thread_id, db_session)
                    # Verify user owns the thread
                    if thread and thread.metadata_.get("user_id") != user_id:
                        await manager.send_error(user_id, "Access denied to thread")
                        return
                
                if not thread:
                    thread = await self.thread_service.get_or_create_thread(user_id, db_session)
                
                if thread:
                    await self.thread_service.create_message(
                        thread.id,
                        role="user",
                        content=text,
                        metadata={"references": references} if references else None,
                        db=db_session
                    )
                    
                    run = await self.thread_service.create_run(
                        thread.id,
                        assistant_id="netra-assistant",
                        model="gpt-4",
                        instructions="You are Netra AI Workload Optimization Assistant",
                        db=db_session
                    )
                    
                    self.supervisor.thread_id = thread.id
                    self.supervisor.user_id = user_id
                    self.supervisor.db_session = db_session
                else:
                    logger.warning(f"Could not get/create thread for user {user_id}")
            except Exception as e:
                logger.error(f"Error setting up thread/run: {e}")
        
        try:
            run_id = run.id if run else user_id
            response = await self.supervisor.run(text, thread.id if thread else user_id, user_id, run_id)
            
            if db_session and response and thread:
                try:
                    await self.thread_service.create_message(
                        thread.id,
                        role="assistant",
                        content=str(response),
                        metadata={"type": "agent_response"},
                        assistant_id="netra-assistant",
                        run_id=run.id if run else None,
                        db=db_session
                    )
                    
                    if run:
                        await self.thread_service.update_run_status(
                            run.id,
                            status="completed",
                            db=db_session
                        )
                except Exception as e:
                    logger.error(f"Error persisting assistant message: {e}")
            
            # Convert response to dict if it's a DeepAgentState object or Pydantic model
            response_data = response
            if hasattr(response, 'model_dump'):
                response_data = response.model_dump()
            elif hasattr(response, 'dict'):
                response_data = response.dict()
            elif hasattr(response, '__dict__'):
                response_data = response.__dict__
            
            # Attempt to send the response, but handle disconnection gracefully
            try:
                await manager.send_message(
                    user_id,
                    {
                        "type": "agent_completed",
                        "payload": response_data
                    }
                )
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                logger.info(f"WebSocket disconnected when sending response to user {user_id}: {e}")
                # Don't re-raise, just log and continue
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id} during processing")
            # Don't try to send messages to disconnected WebSocket
        except RuntimeError as e:
            if "Cannot call" in str(e) or "close" in str(e).lower():
                logger.info(f"WebSocket already closed for user {user_id}: {e}")
            else:
                logger.error(f"Runtime error processing user message: {e}")
                try:
                    await manager.send_error(user_id, str(e))
                except Exception:
                    logger.debug(f"Could not send error to user {user_id}")
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            try:
                await manager.send_error(user_id, f"Internal server error: {str(e)}")
            except Exception:
                logger.debug(f"Could not send error to user {user_id}")
    
    async def handle_thread_history(
        self,
        user_id: str,
        db_session: Optional[AsyncSession]
    ) -> None:
        """Handle get_thread_history message type"""
        if not db_session:
            await manager.send_error(user_id, "Database session not available")
            return
        
        thread = await self.thread_service.get_or_create_thread(user_id, db_session)
        if not thread:
            await manager.send_error(user_id, "Failed to retrieve thread history")
            return
        
        messages = await self.thread_service.get_thread_messages(thread.id, db=db_session)
        history = []
        
        for msg in messages:
            content = msg.content[0]["text"]["value"] if msg.content else ""
            history.append({
                "role": msg.role,
                "content": content,
                "created_at": msg.created_at,
                "id": msg.id
            })
        
        await manager.send_message(
            user_id,
            {
                "type": "thread_history",
                "payload": {
                    "thread_id": thread.id,
                    "messages": history
                }
            }
        )
    
    async def handle_stop_agent(self, user_id: str) -> None:
        """Handle stop_agent message type"""
        logger.info(f"Received stop agent request from {user_id}")
        await manager.send_message(
            user_id,
            {
                "type": "agent_stopped",
                "payload": {"status": "stopped"}
            }
        )