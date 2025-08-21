# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Refactor to ≤300 lines, functions ≤8 lines
# Git: 8-18-25-AM | modified
# Change: Modularize | Scope: Component | Risk: Low
# Session: synthetic-data-split | Seq: 1
# Review: Pending | Score: 90
# ================================

import time
from typing import Optional, List

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.synthetic_data_presets import WorkloadProfile
from app.agents.synthetic_data_profile_parser import create_profile_parser
from app.agents.synthetic_data_generator import SyntheticDataGenerator
from app.agents.synthetic_data_metrics_handler import SyntheticDataMetricsHandler
from app.logging_config import central_logger
from app.llm.observability import log_agent_communication

# Import modular components
from app.agents.synthetic_data.approval_flow import ApprovalWorkflow, ApprovalRequirements
from app.agents.synthetic_data.llm_handler import SyntheticDataLLMExecutor
from app.agents.synthetic_data.generation_workflow import GenerationExecutor, GenerationErrorHandler
from app.agents.synthetic_data.validation import RequestValidator, MetricsValidator
from app.agents.synthetic_data.messaging import CommunicationCoordinator

logger = central_logger.get_logger(__name__)


class SyntheticDataSubAgent(BaseSubAgent):
    """Sub-agent dedicated to synthetic data generation"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(
            llm_manager, 
            name="SyntheticDataSubAgent", 
            description="Agent specialized in generating synthetic data for workload simulation"
        )
        self.tool_dispatcher = tool_dispatcher
        self.generator = SyntheticDataGenerator(tool_dispatcher)
        self.profile_parser = create_profile_parser()
        self.metrics_handler = SyntheticDataMetricsHandler("SyntheticDataSubAgent")
        
        # Initialize modular components
        self.approval_workflow = ApprovalWorkflow(self._send_update)
        self.llm_executor = SyntheticDataLLMExecutor(llm_manager)
        self.generation_executor = GenerationExecutor(self.generator, self._send_update)
        self.error_handler = GenerationErrorHandler(self._send_update)
        self.communicator = CommunicationCoordinator(self._send_update)
        self.validator = RequestValidator()
        self.approval_requirements = ApprovalRequirements()

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for synthetic data generation"""
        return self.validator.check_entry_conditions(state, run_id)

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute synthetic data generation"""
        log_agent_communication("Supervisor", "SyntheticDataSubAgent", run_id, "execute_request")
        start_time = time.time()
        
        try:
            await self._execute_main_flow(state, run_id, stream_updates, start_time)
            self.metrics_handler.log_successful_execution(run_id)
        except Exception as e:
            await self._handle_generation_error(e, state, run_id, stream_updates)
            raise
    
    async def _execute_main_flow(self, state: DeepAgentState, run_id: str, 
                               stream_updates: bool, start_time: float) -> None:
        """Execute the main generation flow using modular components."""
        workload_profile = await self._determine_workload_profile(state)
        
        requires_approval = self.approval_requirements.check_approval_requirements(
            workload_profile, state
        )
        
        if requires_approval:
            await self.approval_workflow.process_approval_workflow(
                workload_profile, state, run_id, stream_updates
            )
        else:
            await self.generation_executor.execute_generation(
                workload_profile, state, run_id, stream_updates, start_time
            )

    async def _handle_generation_error(
        self, error: Exception, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle generation errors"""
        self.logger.error(f"Synthetic data generation failed for run_id {run_id}: {error}")
        error_result = self.error_handler.create_error_result(error)
        state.synthetic_data_result = error_result.model_dump()
        await self.error_handler.send_error_update_if_needed(stream_updates, run_id, error)

    async def _determine_workload_profile(self, state: DeepAgentState) -> WorkloadProfile:
        """Determine workload profile from user request"""
        return await self.profile_parser.determine_workload_profile(
            state.user_request, self.llm_manager
        )

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        MetricsValidator.log_final_metrics(state)