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
        await self._execute_with_error_handling(state, run_id, stream_updates, start_time)
    
    async def _execute_with_error_handling(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Execute with error handling wrapper"""
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
        await self._process_operation_with_approval(operation_request, state, run_id, stream_updates, start_time)
        log_agent_communication("CorpusAdminSubAgent", "Supervisor", run_id, "execute_response")
    
    async def _process_operation_with_approval(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Process operation with approval check"""
        approval_required = await self._handle_approval_check(operation_request, state, run_id, stream_updates)
        if not approval_required:
            await self._complete_corpus_operation(operation_request, state, run_id, stream_updates, start_time)
    
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
    
