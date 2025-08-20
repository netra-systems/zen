"""Supervisor Workflow Orchestrator.

Orchestrates the complete agent workflow according to unified spec.
Business Value: Implements the 12-step workflow for AI optimization value creation.
"""

import time
from typing import List, Dict, Any, Optional

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.base.interface import ExecutionContext, ExecutionResult
from app.schemas.core_enums import ExecutionStatus
from app.agents.supervisor.execution_context import PipelineStep

logger = central_logger.get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates supervisor workflow according to unified spec."""
    
    def __init__(self, agent_registry, execution_engine, websocket_manager):
        self.agent_registry = agent_registry
        self.execution_engine = execution_engine
        self.websocket_manager = websocket_manager
        self._workflow_steps = self._define_standard_workflow()
    
    def _define_standard_workflow(self) -> List[PipelineStep]:
        """Define standard 12-step workflow from unified spec."""
        return [
            self._create_pipeline_step("triage", "classification", 1),
            self._create_pipeline_step("data", "insights", 2),
            self._create_pipeline_step("optimization", "strategies", 3),
            self._create_pipeline_step("actions", "implementation", 4),
            self._create_pipeline_step("reporting", "summary", 5)
        ]
    
    def _create_pipeline_step(self, agent_name: str, 
                             step_type: str, order: int) -> PipelineStep:
        """Create standardized pipeline step."""
        return PipelineStep(
            agent_name=agent_name,
            metadata={
                "step_type": step_type,
                "order": order,
                "continue_on_error": False
            }
        )
    
    async def execute_standard_workflow(self, context: ExecutionContext) -> List[ExecutionResult]:
        """Execute the standard 12-step workflow."""
        await self._send_workflow_started(context)
        results = await self._execute_workflow_steps(context)
        await self._send_workflow_completed(context, results)
        return results
    
    async def _execute_workflow_steps(self, context: ExecutionContext) -> List[ExecutionResult]:
        """Execute all workflow steps with monitoring."""
        results = []
        for step in self._workflow_steps:
            result = await self._execute_workflow_step(context, step)
            results.append(result)
            if not result.success and not step.metadata.get("continue_on_error"):
                break
        return results
    
    async def _execute_workflow_step(self, context: ExecutionContext, 
                                    step: PipelineStep) -> ExecutionResult:
        """Execute single workflow step with monitoring."""
        step_context = self._create_step_context(context, step)
        await self._send_step_started(step_context, step)
        
        start_time = time.time()
        result = await self.execution_engine.execute_agent(step_context, context.state)
        result.execution_time_ms = (time.time() - start_time) * 1000
        
        await self._send_step_completed(step_context, step, result)
        return result
    
    def _create_step_context(self, base_context: ExecutionContext, 
                           step: PipelineStep) -> ExecutionContext:
        """Create execution context for workflow step."""
        return ExecutionContext(
            run_id=base_context.run_id,
            agent_name=step.agent_name,
            state=base_context.state,
            stream_updates=base_context.stream_updates,
            thread_id=base_context.thread_id,
            user_id=base_context.user_id,
            metadata=step.metadata
        )
    
    async def _send_workflow_started(self, context: ExecutionContext) -> None:
        """Send workflow started notification."""
        if context.stream_updates and self.websocket_manager:
            await self.websocket_manager.send_agent_update(
                context.run_id, "supervisor", 
                {"status": "workflow_started", "total_steps": len(self._workflow_steps)}
            )
    
    async def _send_step_started(self, context: ExecutionContext, 
                                step: PipelineStep) -> None:
        """Send step started notification."""
        if context.stream_updates and self.websocket_manager:
            await self.websocket_manager.send_agent_update(
                context.run_id, step.agent_name, 
                {"status": "started", "step_type": step.metadata.get("step_type"), "order": step.metadata.get("order")}
            )
    
    async def _send_step_completed(self, context: ExecutionContext, 
                                  step: PipelineStep, result: ExecutionResult) -> None:
        """Send step completed notification."""
        if context.stream_updates and self.websocket_manager:
            await self.websocket_manager.send_agent_update(
                context.run_id, step.agent_name,
                {
                    "status": "completed" if result.success else "failed",
                    "execution_time_ms": result.execution_time_ms,
                    "step_type": step.metadata.get("step_type")
                }
            )
    
    async def _send_workflow_completed(self, context: ExecutionContext, 
                                      results: List[ExecutionResult]) -> None:
        """Send workflow completed notification."""
        if context.stream_updates and self.websocket_manager:
            total_time = sum(r.execution_time_ms for r in results)
            success_count = sum(1 for r in results if r.success)
            
            await self.websocket_manager.send_agent_update(
                context.run_id, "supervisor",
                {
                    "status": "workflow_completed",
                    "total_execution_time_ms": total_time,
                    "successful_steps": success_count,
                    "total_steps": len(results)
                }
            )
    
    def get_workflow_definition(self) -> List[Dict[str, Any]]:
        """Get workflow definition for monitoring."""
        return [
            {
                "agent_name": step.agent_name,
                "step_type": step.metadata.get("step_type"),
                "order": step.metadata.get("order"),
                "metadata": step.metadata
            } for step in self._workflow_steps
        ]
