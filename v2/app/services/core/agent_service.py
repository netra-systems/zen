"""Refactored Agent Service

Uses dependency injection and proper separation of concerns.
"""

from typing import Optional, Dict, Any, Union
from app.logging_config import central_logger
from app.services.core.service_container import ServiceContainer
from app.services.database.unit_of_work import UnitOfWork
from app.services.websocket.message_handler import MessageHandlerService
from app.services.cache.llm_cache import LLMCacheManager
from app.agents.orchestration.supervisor import SupervisorAgent
from app.schemas import RequestModel
import json

logger = central_logger.get_logger(__name__)

class IAgentService:
    """Interface for agent service"""
    
    async def run(self, request_model: RequestModel, run_id: str, stream_updates: bool = False) -> Any:
        raise NotImplementedError
    
    async def handle_websocket_message(self, user_id: str, message: Union[str, Dict]) -> None:
        raise NotImplementedError
    
    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        raise NotImplementedError

class AgentService(IAgentService):
    """Service for managing agent interactions"""
    
    def __init__(self,
                 supervisor: SupervisorAgent,
                 message_handler: MessageHandlerService,
                 unit_of_work: UnitOfWork,
                 cache_manager: LLMCacheManager):
        self.supervisor = supervisor
        self.message_handler = message_handler
        self.unit_of_work = unit_of_work
        self.cache_manager = cache_manager
        self._active_runs: Dict[str, Dict[str, Any]] = {}
    
    async def run(self, request_model: RequestModel, run_id: str, stream_updates: bool = False) -> Any:
        """Start agent processing"""
        try:
            user_request = self._extract_user_request(request_model)
            
            cached_response = await self.cache_manager.get_cached_response(
                user_request, "supervisor", {"run_id": run_id}
            )
            
            if cached_response:
                logger.info(f"Using cached response for run {run_id}")
                return cached_response
            
            self._active_runs[run_id] = {
                "status": "running",
                "started_at": datetime.utcnow()
            }
            
            result = await self.supervisor.run(user_request, run_id, stream_updates)
            
            await self.cache_manager.cache_response(
                user_request, result, "supervisor", {"run_id": run_id}
            )
            
            self._active_runs[run_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.utcnow()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Agent run failed for {run_id}: {e}")
            self._active_runs[run_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow()
            }
            raise
    
    async def handle_websocket_message(self, user_id: str, message: Union[str, Dict]) -> None:
        """Handle incoming WebSocket message"""
        try:
            parsed_message = self._parse_message(message)
            await self.message_handler.handle_message(user_id, parsed_message)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from user {user_id}: {e}")
            await self._send_error(user_id, "Invalid message format")
        except Exception as e:
            logger.error(f"Error handling message from {user_id}: {e}")
            await self._send_error(user_id, "Internal server error")
    
    async def get_agent_state(self, run_id: str) -> Dict[str, Any]:
        """Get current state of an agent run"""
        if run_id in self._active_runs:
            return self._active_runs[run_id]
        
        return await self.supervisor.get_stats()
    
    def _extract_user_request(self, request_model: RequestModel) -> str:
        """Extract user request from model"""
        if hasattr(request_model, 'user_request'):
            return request_model.user_request
        return str(request_model.model_dump())
    
    def _parse_message(self, message: Union[str, Dict]) -> Dict[str, Any]:
        """Parse incoming message"""
        if isinstance(message, str):
            data = json.loads(message)
            if isinstance(data, str):
                data = json.loads(data)
            return data
        return message
    
    async def _send_error(self, user_id: str, error_message: str) -> None:
        """Send error message to user"""
        from app.ws_manager import manager
        await manager.send_error(user_id, error_message)

class AgentServiceFactory:
    """Factory for creating agent service instances"""
    
    @staticmethod
    def create(container: ServiceContainer) -> AgentService:
        """Create agent service with dependencies"""
        supervisor = container.resolve(SupervisorAgent)
        message_handler = container.resolve(MessageHandlerService)
        unit_of_work = container.resolve(UnitOfWork)
        cache_manager = container.resolve(LLMCacheManager)
        
        return AgentService(
            supervisor=supervisor,
            message_handler=message_handler,
            unit_of_work=unit_of_work,
            cache_manager=cache_manager
        )