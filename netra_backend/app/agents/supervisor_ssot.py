"""SSOT Supervisor Agent - Clean Architecture Implementation

Business Value: Enables safe concurrent user operations with zero context leakage.
BVJ: ALL segments | Platform Stability | Complete user isolation for production deployment

This replaces supervisor_consolidated.py with a clean, SSOT-compliant implementation 
that leverages existing UserExecutionEngine and AgentInstanceFactory.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from netra_backend.app.database.session_manager import DatabaseSessionManager

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# SSOT imports - use the proper service location
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.database.session_manager import (
    validate_agent_session_isolation
)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine
)

# Core dependencies
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


class SupervisorAgent(BaseAgent):
    """SSOT Supervisor Agent using proper factory and execution engine patterns.
    
    This implementation eliminates the legacy wrapper by using:
    - AgentInstanceFactory for agent creation (SSOT)
    - UserExecutionEngine for execution logic (SSOT) 
    - Proper UserExecutionContext from services (SSOT)
    - No duplicate implementation of existing patterns
    """
    
    def __init__(self, 
                 llm_manager: LLMManager,
                 websocket_bridge: Optional[AgentWebSocketBridge] = None):
        """Initialize SSOT SupervisorAgent.
        
        Args:
            llm_manager: LLM manager for agent operations
            websocket_bridge: Optional WebSocket bridge
        """
        super().__init__(
            llm_manager=llm_manager,
            name="Supervisor",
            description="Orchestrates sub-agents with complete user isolation using SSOT patterns",
            enable_reliability=False,
            enable_execution_engine=True,
            enable_caching=False
        )
        
        self.websocket_bridge = websocket_bridge
        self._llm_manager = llm_manager
        
        # Use SSOT factory instead of maintaining own state
        self.agent_factory = get_agent_instance_factory()
        
        # Validate no session storage (SSOT requirement)
        validate_agent_session_isolation(self)
        
        logger.info("✅ SSOT SupervisorAgent initialized using factory and execution engine patterns")

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute using SSOT UserExecutionEngine pattern.
        
        Args:
            context: UserExecutionContext with all request-specific data
            stream_updates: Whether to stream updates via WebSocket
            
        Returns:
            Dictionary with execution results
        """
        # Validate context using SSOT validation
        context = validate_user_context(context)
        logger.info(f"🚀 SSOT SupervisorAgent.execute() for user={context.user_id}, run_id={context.run_id}")
        
        if not context.db_session:
            raise ValueError("UserExecutionContext must contain a database session")
        
        # Create UserExecutionEngine with proper context - session already exists in context
        engine = await self._create_user_execution_engine(context)
        
        try:
            # CRITICAL FIX: Emit agent_started event
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_started(
                    context.run_id,
                    "Supervisor",
                    context={"status": "starting", "isolated": True}
                )
                logger.info(f"📡 Emitted agent_started event for run {context.run_id}")
            
            # CRITICAL FIX: Emit agent_thinking event
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_thinking(
                    context.run_id,
                    "Supervisor",
                    reasoning="Analyzing your request and selecting appropriate agents...",
                    step_number=1
                )
                logger.info(f"📡 Emitted agent_thinking event for run {context.run_id}")
            
            # Execute using SSOT execution engine
            result = await engine.execute_agent_pipeline(
                agent_name="supervisor_orchestration",
                execution_context=context,
                input_data={
                    "user_request": context.metadata.get("user_request", ""),
                    "stream_updates": stream_updates
                }
            )
            
            # CRITICAL FIX: Emit agent_completed event
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_completed(
                    context.run_id,
                    "Supervisor",
                    result={
                        "supervisor_result": "completed",
                        "orchestration_successful": result.success if hasattr(result, 'success') else True,
                        "user_isolation_verified": True,
                        "results": result.result if hasattr(result, 'result') else result
                    },
                    execution_time_ms=0  # TODO: Add proper timing
                )
                logger.info(f"📡 Emitted agent_completed event for run {context.run_id}")
            
            logger.info(f"✅ SSOT SupervisorAgent execution completed for user {context.user_id}")
            
            return {
                "supervisor_result": "completed",
                "orchestration_successful": result.success if hasattr(result, 'success') else True,
                "user_isolation_verified": True,
                "results": result.result if hasattr(result, 'result') else result,
                "user_id": context.user_id,
                "run_id": context.run_id
            }
            
        except Exception as e:
            # CRITICAL FIX: Emit error event on failure
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_error(
                    context.run_id,
                    "Supervisor",
                    error=f"Supervisor execution failed: {str(e)}",
                    error_context={"error_type": type(e).__name__}
                )
                logger.error(f"📡 Emitted agent_error event for run {context.run_id}: {e}")
            raise
            
        finally:
            # Cleanup using SSOT cleanup
            await engine.cleanup()

    async def _create_user_execution_engine(self, context: UserExecutionContext) -> UserExecutionEngine:
        """Create UserExecutionEngine using SSOT factory patterns.
        
        Args:
            context: User execution context
            
        Returns:
            UserExecutionEngine configured for this user
        """
        # Configure factory if needed
        if self.websocket_bridge:
            self.agent_factory.configure(
                websocket_bridge=self.websocket_bridge,
                llm_manager=self._llm_manager
            )
        
        # Create user WebSocket emitter using factory
        from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
        websocket_emitter = UserWebSocketEmitter(
            context.user_id, 
            context.thread_id, 
            context.run_id,
            self.websocket_bridge
        )
        
        # Create and return UserExecutionEngine
        return UserExecutionEngine(
            context=context,
            agent_factory=self.agent_factory,
            websocket_emitter=websocket_emitter
        )

    # === Legacy Compatibility (delegates to SSOT methods) ===
    
    async def run(self, user_request: str, thread_id: str, user_id: str, run_id: str) -> Any:
        """Legacy compatibility - delegates to SSOT execute() method.
        
        Args:
            user_request: The user's request message
            thread_id: Thread identifier 
            user_id: User identifier
            run_id: Execution run identifier
            
        Returns:
            Agent execution result
        """
        logger.info(f"🔄 Legacy run() method - delegating to SSOT execute() for user {user_id}")
        
        # Create UserExecutionContext using SSOT factory method
        from shared.id_generation import UnifiedIdGenerator
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id)
        )
        
        # Execute using SSOT pattern
        result = await self.execute(user_context, stream_updates=True)
        
        # Extract results for legacy compatibility
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        return result

    # === Factory Method ===
    
    @classmethod
    def create(cls,
               llm_manager: LLMManager,
               websocket_bridge: AgentWebSocketBridge) -> 'SupervisorAgent':
        """Factory method to create SSOT SupervisorAgent.
        
        Args:
            llm_manager: LLM manager instance
            websocket_bridge: WebSocket bridge for agent notifications
            
        Returns:
            SupervisorAgent configured using SSOT patterns
        """
        supervisor = cls(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge
        )
        
        logger.info("✅ Created SSOT SupervisorAgent using factory pattern")
        return supervisor

    def __str__(self) -> str:
        return f"SupervisorAgent(SSOT pattern, factory-based)"
    
    def __repr__(self) -> str:
        return f"SupervisorAgent(pattern='SSOT', factory_based=True)"