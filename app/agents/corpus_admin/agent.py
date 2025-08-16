"""
Corpus Admin Sub Agent

Main agent class for corpus administration with modular operation handling.
Maintains 8-line function limit and single responsibility.
"""

import time
from typing import Dict, Any
from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
from app.llm.observability import log_agent_communication
from .models import CorpusOperationResult, CorpusMetadata, CorpusType, CorpusOperation
from .parsers import CorpusRequestParser
from .validators import CorpusApprovalValidator
from .operations import CorpusOperationHandler

logger = central_logger.get_logger(__name__)


class CorpusAdminSubAgent(BaseSubAgent):
    """Sub-agent dedicated to corpus administration and management"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager,
            name="CorpusAdminSubAgent",
            description="Agent specialized in corpus management and administration"
        )
        self._initialize_components(tool_dispatcher, llm_manager)
    
    def _initialize_components(self, tool_dispatcher: ToolDispatcher, llm_manager: LLMManager) -> None:
        """Initialize agent components"""
        self.tool_dispatcher = tool_dispatcher
        self.parser = CorpusRequestParser(llm_manager)
        self.validator = CorpusApprovalValidator()
        self.operations = CorpusOperationHandler(tool_dispatcher)
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for corpus administration"""
        if self._is_admin_mode_request(state) or self._has_corpus_keywords(state):
            return True
        
        logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute corpus administration operation"""
        log_agent_communication("Supervisor", "CorpusAdminSubAgent", run_id, "execute_request")
        start_time = time.time()
        
        try:
            await self._execute_corpus_operation_workflow(state, run_id, stream_updates, start_time)
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
            raise
    
    async def _execute_corpus_operation_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Execute the complete corpus operation workflow."""
        await self._send_initial_update(run_id, stream_updates)
        operation_request = await self.parser.parse_operation_request(state.user_request)
        
        if await self._handle_approval_check(operation_request, state, run_id, stream_updates):
            return
        
        await self._complete_corpus_operation(operation_request, state, run_id, stream_updates, start_time)
        log_agent_communication("CorpusAdminSubAgent", "Supervisor", run_id, "execute_response")
    
    async def _complete_corpus_operation(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Complete the corpus operation execution."""
        await self._send_processing_update(operation_request, run_id, stream_updates)
        result = await self.operations.execute_operation(operation_request, run_id, stream_updates)
        
        await self._finalize_operation_result(result, state, run_id, stream_updates, start_time)
    
    async def _finalize_operation_result(
        self, result, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Finalize operation result and send updates"""
        state.corpus_admin_result = result.model_dump()
        await self._send_completion_update(result, run_id, stream_updates, start_time)
        self._log_completion(result, run_id)
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        self._log_final_metrics(state)
    
    def _is_admin_mode_request(self, state: DeepAgentState) -> bool:
        """Check if request is admin mode or corpus-related"""
        triage_result = state.triage_result or {}
        
        if isinstance(triage_result, dict):
            return self._check_admin_indicators(triage_result)
        return False
    
    def _check_admin_indicators(self, triage_result: dict) -> bool:
        """Check if triage result indicates admin or corpus operation"""
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "corpus" in category.lower() or "admin" in category.lower() or is_admin
    
    def _has_corpus_keywords(self, state: DeepAgentState) -> bool:
        """Check if user request contains corpus keywords"""
        if not state.user_request:
            return False
        corpus_keywords = self._get_corpus_keywords()
        return any(keyword in state.user_request.lower() for keyword in corpus_keywords)
    
    def _get_corpus_keywords(self) -> list:
        """Get list of corpus-related keywords."""
        return ["corpus", "knowledge base", "documentation", "reference data", "embeddings"]
    
    async def _send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial processing update"""
        if stream_updates:
            update_data = self._build_initial_update_data()
            await self._send_update(run_id, update_data)
    
    def _build_initial_update_data(self) -> dict:
        """Build initial update data."""
        return {
            "status": "starting",
            "message": "📚 Initializing corpus administration...",
            "agent": "CorpusAdminSubAgent"
        }
    
    async def _handle_approval_check(
        self, 
        operation_request, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool
    ) -> bool:
        """Handle approval requirements check"""
        requires_approval = await self.validator.check_approval_requirements(operation_request, state)
        if requires_approval:
            await self._process_approval_requirement(operation_request, state, run_id, stream_updates)
        return requires_approval
    
    async def _process_approval_requirement(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Process approval requirement workflow."""
        approval_message = self.validator.generate_approval_message(operation_request)
        await self._store_approval_result(operation_request, approval_message, state)
        await self._send_approval_update(approval_message, operation_request, run_id, stream_updates)
    
    async def _send_processing_update(self, operation_request, run_id: str, stream_updates: bool) -> None:
        """Send processing update"""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": f"🔄 Executing {operation_request.operation.value} operation on corpus '{operation_request.corpus_metadata.corpus_name}'...",
                "operation": operation_request.operation.value
            })
    
    async def _send_completion_update(
        self, 
        result, 
        run_id: str, 
        stream_updates: bool, 
        start_time: float
    ) -> None:
        """Send completion update"""
        if stream_updates:
            update_data = await self._build_completion_update_data(result, start_time)
            await self._send_update(run_id, update_data)
    
    async def _build_completion_update_data(self, result, start_time: float) -> dict:
        """Build completion update data."""
        duration = int((time.time() - start_time) * 1000)
        status_emoji = "✅" if result.success else "❌"
        statistics = await self.operations.get_corpus_statistics()
        return self._create_completion_update_dict(
            result, duration, status_emoji, statistics
        )
    
    def _create_completion_update_dict(
        self, result, duration: int, status_emoji: str, statistics
    ) -> dict:
        """Create completion update dictionary."""
        return {
            "status": "completed" if result.success else "failed",
            "message": f"{status_emoji} Corpus operation completed in {duration}ms",
            "result": result.model_dump(),
            "statistics": statistics
        }
    
    async def _handle_execution_error(
        self, 
        error: Exception, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool
    ) -> None:
        """Handle execution errors"""
        logger.error(f"Corpus operation failed for run_id {run_id}: {error}")
        error_result = self._create_error_result(error)
        state.corpus_admin_result = error_result.model_dump()
        if stream_updates:
            await self._send_error_update(run_id, error)
    
    def _create_error_result(self, error: Exception) -> CorpusOperationResult:
        """Create error result for failed operation."""
        return CorpusOperationResult(
            success=False,
            operation=CorpusOperation.SEARCH,
            corpus_metadata=CorpusMetadata(corpus_name="unknown", corpus_type=CorpusType.REFERENCE_DATA),
            errors=[str(error)]
        )
    
    async def _send_error_update(self, run_id: str, error: Exception) -> None:
        """Send error update via WebSocket."""
        await self._send_update(run_id, {
            "status": "error",
            "message": f"❌ Corpus operation failed: {str(error)}",
            "error": str(error)
        })
    
    async def _store_approval_result(
        self, 
        operation_request, 
        approval_message: str, 
        state: DeepAgentState
    ) -> None:
        """Store approval result in state"""
        approval_result = self._create_approval_result(operation_request, approval_message)
        state.corpus_admin_result = approval_result.model_dump()
    
    def _create_approval_result(self, operation_request, approval_message: str) -> CorpusOperationResult:
        """Create approval result for pending operation."""
        return CorpusOperationResult(
            success=False,
            operation=operation_request.operation,
            corpus_metadata=operation_request.corpus_metadata,
            requires_approval=True,
            approval_message=approval_message
        )
    
    async def _send_approval_update(
        self, 
        approval_message: str, 
        operation_request, 
        run_id: str, 
        stream_updates: bool
    ) -> None:
        """Send approval required update"""
        if stream_updates:
            update_data = self._build_approval_update_data(approval_message, operation_request)
            await self._send_update(run_id, update_data)
    
    def _build_approval_update_data(self, approval_message: str, operation_request) -> dict:
        """Build approval update data."""
        return {
            "status": "approval_required",
            "message": approval_message,
            "requires_user_action": True,
            "action_type": "approve_corpus_operation",
            "operation_details": operation_request.model_dump()
        }
    
    def _log_completion(self, result, run_id: str) -> None:
        """Log operation completion"""
        logger.info(f"Corpus operation completed for run_id {run_id}: "
                   f"operation={result.operation.value}, "
                   f"success={result.success}, "
                   f"affected={result.affected_documents}")
    
    def _log_final_metrics(self, state: DeepAgentState) -> None:
        """Log final metrics"""
        if state.corpus_admin_result and isinstance(state.corpus_admin_result, dict):
            result = state.corpus_admin_result
            metrics_message = self._build_metrics_message(result)
            logger.info(metrics_message)
    
    def _build_metrics_message(self, result: dict) -> str:
        """Build metrics message for logging."""
        operation = result.get('operation')
        corpus_name = result.get('corpus_metadata', {}).get('corpus_name')
        affected = result.get('affected_documents')
        return f"Corpus operation completed: operation={operation}, corpus={corpus_name}, affected={affected}"
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via WebSocket manager"""
        if self.websocket_manager:
            try:
                await self.websocket_manager.send_agent_update(run_id, "corpus_admin", update)
            except Exception as e:
                logger.error(f"Failed to send WebSocket update: {e}")