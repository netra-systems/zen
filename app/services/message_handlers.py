from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from app.logging_config import central_logger
from app.services.thread_service import ThreadService
from app.ws_manager import manager
import json

logger = central_logger.get_logger(__name__)

class MessageHandlerService:
    """Handles different types of WebSocket messages following conventions"""
    
    def __init__(self, supervisor, thread_service: ThreadService):
        self.supervisor = supervisor
        self.thread_service = thread_service
    
    async def handle_start_agent(
        self,
        user_id: str,
        payload: Dict[str, Any],
        db_session: AsyncSession
    ) -> None:
        """Handle start_agent message type"""
        request_data = payload.get("request", {})
        user_request = request_data.get("query", "") or request_data.get("user_request", "")
        thread_id = payload.get("thread_id", None)  # Get thread_id from payload
        
        # If thread_id provided, use it; otherwise get_or_create
        if thread_id:
            thread = await self.thread_service.get_thread(db_session, thread_id)
            # Verify user owns the thread
            if thread and thread.metadata_.get("user_id") != user_id:
                await manager.send_error(user_id, "Access denied to thread")
                return
        
        if not thread_id or not thread:
            thread = await self.thread_service.get_or_create_thread(db_session, user_id)
        if not thread:
            await manager.send_error(user_id, "Failed to create or retrieve thread")
            return
        
        await self.thread_service.create_message(
            db_session,
            thread_id=thread.id,
            role="user",
            content=user_request,
            metadata={"user_id": user_id}
        )
        
        run = await self.thread_service.create_run(
            db_session,
            thread_id=thread.id,
            assistant_id="netra-assistant",
            model="gpt-4",
            instructions="You are Netra AI Workload Optimization Assistant"
        )
        
        self.supervisor.thread_id = thread.id
        self.supervisor.user_id = user_id
        self.supervisor.db_session = db_session
        
        response = await self.supervisor.run(user_request, run.id, stream_updates=True)
        
        if response:
            await self.thread_service.create_message(
                db_session,
                thread_id=thread.id,
                role="assistant",
                content=json.dumps(response) if isinstance(response, dict) else str(response),
                assistant_id="netra-assistant",
                run_id=run.id
            )
        
        await self.thread_service.update_run_status(
            db_session,
            run_id=run.id,
            status="completed"
        )
        
        await manager.send_message(
            user_id,
            {
                "type": "agent_completed",
                "payload": response
            }
        )
    
    async def handle_user_message(
        self,
        user_id: str,
        payload: Dict[str, Any],
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
                    thread = await self.thread_service.get_thread(db_session, thread_id)
                    # Verify user owns the thread
                    if thread and thread.metadata_.get("user_id") != user_id:
                        await manager.send_error(user_id, "Access denied to thread")
                        return
                
                if not thread:
                    thread = await self.thread_service.get_or_create_thread(db_session, user_id)
                
                if thread:
                    await self.thread_service.create_message(
                        db_session,
                        thread.id,
                        role="user",
                        content=text,
                        metadata={"references": references} if references else None
                    )
                    
                    run = await self.thread_service.create_run(
                        db_session,
                        thread_id=thread.id,
                        assistant_id="netra-assistant",
                        model="gpt-4",
                        instructions="You are Netra AI Workload Optimization Assistant"
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
            response = await self.supervisor.run(text, run_id, stream_updates=True)
            
            if db_session and response and thread:
                try:
                    await self.thread_service.create_message(
                        db_session,
                        thread.id,
                        role="assistant",
                        content=str(response),
                        metadata={"type": "agent_response"},
                        assistant_id="netra-assistant",
                        run_id=run.id if run else None
                    )
                    
                    if run:
                        await self.thread_service.update_run_status(
                            db_session,
                            run_id=run.id,
                            status="completed"
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
        
        thread = await self.thread_service.get_or_create_thread(db_session, user_id)
        if not thread:
            await manager.send_error(user_id, "Failed to retrieve thread history")
            return
        
        messages = await self.thread_service.get_thread_messages(db_session, thread.id)
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