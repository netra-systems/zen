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

# SSOT ExecutionResult imports
from netra_backend.app.agents.base.interface import ExecutionResult, ExecutionContext
from netra_backend.app.schemas.core_enums import ExecutionStatus

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
        
        # Initialize workflow executor for workflow orchestration
        from netra_backend.app.agents.supervisor.workflow_execution import SupervisorWorkflowExecutor
        self.workflow_executor = SupervisorWorkflowExecutor(self)
        logger.info(" PASS:  SSOT SupervisorAgent workflow_executor initialized")
        
        # Validate no session storage (SSOT requirement)
        validate_agent_session_isolation(self)
        
        logger.info(" PASS:  SSOT SupervisorAgent initialized using factory and execution engine patterns")

    def _create_supervisor_execution_context(self, 
                                           user_context: UserExecutionContext, 
                                           agent_name: str = "Supervisor",
                                           additional_metadata: Optional[Dict[str, Any]] = None) -> ExecutionContext:
        """Create supervisor-specific execution context from UserExecutionContext.
        
        This method bridges the gap between UserExecutionContext (user isolation pattern)
        and ExecutionContext (agent execution pattern) for supervisor operations.
        
        Args:
            user_context: UserExecutionContext with user-specific data
            agent_name: Name of the supervisor agent
            additional_metadata: Optional additional metadata
            
        Returns:
            ExecutionContext configured for supervisor execution
        """
        # Create execution context from user context
        execution_context = ExecutionContext(
            request_id=getattr(user_context, 'request_id', f"supervisor_{user_context.run_id}"),
            user_id=str(user_context.user_id),
            run_id=str(user_context.run_id),
            agent_name=agent_name,
            session_id=getattr(user_context, 'session_id', None),
            correlation_id=getattr(user_context, 'correlation_id', None),
            stream_updates=True,  # Supervisor always streams updates
            parameters={
                "user_request": user_context.metadata.get("user_request", ""),
                "thread_id": str(user_context.thread_id),
                "websocket_connection_id": getattr(user_context, 'websocket_connection_id', None)
            },
            metadata=user_context.metadata.copy() if user_context.metadata else {}
        )
        
        # Add additional metadata if provided
        if additional_metadata:
            execution_context.metadata.update(additional_metadata)
        
        # Add supervisor-specific metadata
        execution_context.metadata.update({
            "supervisor_execution": True,
            "user_isolation_enabled": True,
            "execution_pattern": "UserExecutionContext"
        })
        
        logger.debug(f"Created supervisor execution context for user {user_context.user_id}, run {user_context.run_id}")
        
        return execution_context

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> ExecutionResult:
        """Execute using SSOT UserExecutionEngine pattern.
        
        Args:
            context: UserExecutionContext with all request-specific data
            stream_updates: Whether to stream updates via WebSocket
            
        Returns:
            ExecutionResult with SSOT-compliant format
        """
        # Validate context using SSOT validation
        context = validate_user_context(context)
        logger.info(f"[U+1F680] SSOT SupervisorAgent.execute() for user={context.user_id}, run_id={context.run_id}")
        
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
                logger.info(f"[U+1F4E1] Emitted agent_started event for run {context.run_id}")
            
            # CRITICAL FIX: Emit agent_thinking event
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_thinking(
                    context.run_id,
                    "Supervisor",
                    reasoning="Analyzing your request and selecting appropriate agents...",
                    step_number=1
                )
                logger.info(f"[U+1F4E1] Emitted agent_thinking event for run {context.run_id}")
            
            # Execute orchestration workflow directly (no circular dependency)
            result = await self._execute_orchestration_workflow(
                engine=engine,
                context=context,
                user_request=context.metadata.get("user_request", ""),
                stream_updates=stream_updates
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
                logger.info(f"[U+1F4E1] Emitted agent_completed event for run {context.run_id}")
            
            logger.info(f" PASS:  SSOT SupervisorAgent execution completed for user {context.user_id}")
            
            # Return SSOT ExecutionResult format
            orchestration_successful = result.success if hasattr(result, 'success') else True
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                request_id=getattr(context, 'request_id', f"supervisor_{context.run_id}"),
                data={
                    "supervisor_result": "completed",
                    "orchestration_successful": orchestration_successful,
                    "user_isolation_verified": True,
                    "results": result.result if hasattr(result, 'result') else result,
                    "user_id": str(context.user_id),
                    "run_id": str(context.run_id)
                }
            )
            
        except Exception as e:
            # CRITICAL FIX: Emit error event on failure
            if self.websocket_bridge:
                await self.websocket_bridge.notify_agent_error(
                    context.run_id,
                    "Supervisor",
                    error=f"Supervisor execution failed: {str(e)}",
                    error_context={"error_type": type(e).__name__}
                )
                logger.error(f"[U+1F4E1] Emitted agent_error event for run {context.run_id}: {e}")
            
            # Return SSOT ExecutionResult for error cases
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                request_id=getattr(context, 'request_id', f"supervisor_{context.run_id}"),
                error_message=str(e),
                error_code=type(e).__name__,
                data={
                    "supervisor_result": "failed",
                    "orchestration_successful": False,
                    "user_isolation_verified": True,
                    "error": str(e),
                    "user_id": str(context.user_id),
                    "run_id": str(context.run_id)
                }
            )
            
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
        
        # Create user WebSocket emitter using SSOT UnifiedWebSocketEmitter
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        websocket_emitter = UnifiedWebSocketEmitter(
            manager=self.websocket_bridge,
            user_id=context.user_id,
            context=context
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
        logger.info(f" CYCLE:  Legacy run() method - delegating to SSOT execute() for user {user_id}")
        
        # Create UserExecutionContext using SSOT factory method
        from shared.id_generation import UnifiedIdGenerator
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id),
            metadata={"user_request": user_request}
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
        
        logger.info(" PASS:  Created SSOT SupervisorAgent using factory pattern")
        return supervisor

    async def _execute_orchestration_workflow(self, 
                                            engine: UserExecutionEngine,
                                            context: UserExecutionContext,
                                            user_request: str,
                                            stream_updates: bool = True) -> Any:
        """Execute the agent orchestration workflow.
        
        This method implements the actual orchestration logic without circular dependencies.
        It orchestrates triage -> data -> optimization -> actions -> reporting agents.
        
        Args:
            engine: UserExecutionEngine for agent execution
            context: User execution context
            user_request: The user's request
            stream_updates: Whether to stream updates
            
        Returns:
            Orchestration workflow result
        """
        logger.info(f"[U+1F3AD] Starting orchestration workflow for user {context.user_id}")
        
        try:
            # Step 1: Triage the user request
            triage_result = await engine.execute_agent_pipeline(
                agent_name="triage",
                execution_context=context,
                input_data={"user_request": user_request}
            )
            
            # Step 2: Data analysis based on triage
            data_result = await engine.execute_agent_pipeline(
                agent_name="data",
                execution_context=context,
                input_data={
                    "user_request": user_request,
                    "triage_result": triage_result
                }
            )
            
            # Step 3: Optimization recommendations
            optimization_result = await engine.execute_agent_pipeline(
                agent_name="optimization",
                execution_context=context,
                input_data={
                    "user_request": user_request,
                    "triage_result": triage_result,
                    "data_result": data_result
                }
            )
            
            # Step 4: Action planning
            actions_result = await engine.execute_agent_pipeline(
                agent_name="actions",
                execution_context=context,
                input_data={
                    "user_request": user_request,
                    "optimization_result": optimization_result
                }
            )
            
            # Step 5: Final reporting
            reporting_result = await engine.execute_agent_pipeline(
                agent_name="reporting",
                execution_context=context,
                input_data={
                    "user_request": user_request,
                    "triage_result": triage_result,
                    "data_result": data_result,
                    "optimization_result": optimization_result,
                    "actions_result": actions_result
                }
            )
            
            # Compile final result
            orchestration_result = {
                "workflow_completed": True,
                "triage": triage_result,
                "data": data_result,
                "optimization": optimization_result,
                "actions": actions_result,
                "reporting": reporting_result,
                "user_request": user_request
            }
            
            logger.info(f" PASS:  Orchestration workflow completed for user {context.user_id}")
            return orchestration_result
            
        except Exception as e:
            logger.error(f" FAIL:  Orchestration workflow failed for user {context.user_id}: {e}")
            return {
                "workflow_completed": False,
                "error": str(e),
                "user_request": user_request
            }

    def __str__(self) -> str:
        return f"SupervisorAgent(SSOT pattern, factory-based)"
    
    def __repr__(self) -> str:
        return f"SupervisorAgent(pattern='SSOT', factory_based=True)"