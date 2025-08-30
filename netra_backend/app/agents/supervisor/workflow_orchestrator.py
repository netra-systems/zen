"""Supervisor Workflow Orchestrator.

Orchestrates the complete agent workflow according to unified spec.
Business Value: Implements the adaptive workflow for AI optimization value creation.
"""

import time
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import PipelineStep
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ExecutionStatus

logger = central_logger.get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates supervisor workflow according to unified spec with adaptive logic."""
    
    def __init__(self, agent_registry, execution_engine, websocket_manager):
        self.agent_registry = agent_registry
        self.execution_engine = execution_engine
        self.websocket_manager = websocket_manager
        # No longer define static workflow - it will be determined dynamically
    
    def _define_workflow_based_on_triage(self, triage_result: Dict[str, Any]) -> List[PipelineStep]:
        """Define adaptive workflow based on triage results and data sufficiency.
        
        The workflow adapts based on the TriageSubAgent's assessment:
        a. If sufficient data is available: Full workflow
        b. If some data but more needed: Partial workflow with data_helper
        c. If no data available: Only data_helper
        
        Args:
            triage_result: Results from the triage agent including data sufficiency assessment
            
        Returns:
            List of pipeline steps tailored to the situation
        """
        # Extract data sufficiency from triage result
        data_sufficiency = triage_result.get("data_sufficiency", "unknown")
        
        if data_sufficiency == "sufficient":
            # Full workflow when sufficient data is available
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("optimization", "strategies", 2, dependencies=["triage"]),
                self._create_pipeline_step("data", "insights", 3, dependencies=["optimization"]),
                self._create_pipeline_step("actions", "implementation", 4, dependencies=["data"]),
                self._create_pipeline_step("reporting", "summary", 5, dependencies=["actions"])
            ]
        elif data_sufficiency == "partial":
            # Partial workflow with data_helper for additional data needs
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("optimization", "strategies", 2, dependencies=["triage"]),
                self._create_pipeline_step("actions", "implementation", 3, dependencies=["optimization"]),
                self._create_pipeline_step("data_helper", "data_request", 4, dependencies=["actions"]),
                self._create_pipeline_step("reporting", "summary_with_data_request", 5, dependencies=["data_helper"])
            ]
        elif data_sufficiency == "insufficient":
            # Minimal workflow - only request data
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data_helper", "data_request", 2, dependencies=["triage"])
            ]
        else:
            # Default fallback to standard workflow
            logger.warning(f"Unknown data sufficiency level: {data_sufficiency}, using default workflow")
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data", "insights", 2, dependencies=["triage"]),
                self._create_pipeline_step("optimization", "strategies", 3, dependencies=["data"]),
                self._create_pipeline_step("actions", "implementation", 4, dependencies=["optimization"]),
                self._create_pipeline_step("reporting", "summary", 5, dependencies=["actions"])
            ]
    
    def _create_pipeline_step(self, agent_name: str, 
                             step_type: str, order: int,
                             dependencies: List[str] = None) -> PipelineStep:
        """Create standardized pipeline step with proper dependencies."""
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionStrategy
        
        return PipelineStep(
            agent_name=agent_name,
            strategy=AgentExecutionStrategy.SEQUENTIAL,  # Explicitly set sequential
            dependencies=dependencies or [],
            metadata={
                "step_type": step_type,
                "order": order,
                "continue_on_error": False,
                "requires_sequential": True  # Ensure sequential execution
            }
        )
    
    async def execute_standard_workflow(self, context: ExecutionContext) -> List[ExecutionResult]:
        """Execute the adaptive workflow based on triage results."""
        # First, always execute triage to determine workflow
        triage_step = self._create_pipeline_step("triage", "classification", 1, dependencies=[])
        
        # Create initial workflow with just triage to send notification
        self._workflow_steps = [triage_step]
        await self._send_workflow_started(context)
        
        triage_result = await self._execute_workflow_step(context, triage_step)
        
        # Store triage result in context for downstream agents
        if hasattr(context.state, 'triage_result'):
            context.state.triage_result = triage_result.result
        
        # Determine workflow based on triage result
        workflow_steps = self._define_workflow_based_on_triage(
            triage_result.result if triage_result.success else {}
        )
        
        # Update workflow steps with full workflow
        self._workflow_steps = workflow_steps
        
        # Execute the determined workflow (skip first triage since already done)
        results = [triage_result]
        for step in workflow_steps[1:]:  # Skip first triage step
            result = await self._execute_workflow_step(context, step)
            results.append(result)
            if not result.success and not step.metadata.get("continue_on_error"):
                break
        
        await self._send_workflow_completed(context, results)
        return results
    
    async def _execute_workflow_steps(self, context: ExecutionContext) -> List[ExecutionResult]:
        """Execute all workflow steps with monitoring.
        
        This method is kept for backward compatibility but delegates to execute_standard_workflow.
        """
        return await self.execute_standard_workflow(context)
    
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
    
    def get_workflow_definition(self) -> Dict[str, Any]:
        """Get workflow definition for monitoring.
        
        Returns adaptive workflow configurations based on data sufficiency levels.
        """
        return {
            "type": "adaptive",
            "description": "Workflow adapts based on triage assessment of data sufficiency",
            "configurations": {
                "sufficient_data": [
                    {"agent": "triage", "type": "classification"},
                    {"agent": "optimization", "type": "strategies"},
                    {"agent": "data", "type": "insights"},
                    {"agent": "actions", "type": "implementation"},
                    {"agent": "reporting", "type": "summary"}
                ],
                "partial_data": [
                    {"agent": "triage", "type": "classification"},
                    {"agent": "optimization", "type": "strategies"},
                    {"agent": "actions", "type": "implementation"},
                    {"agent": "data_helper", "type": "data_request"},
                    {"agent": "reporting", "type": "summary_with_data_request"}
                ],
                "insufficient_data": [
                    {"agent": "triage", "type": "classification"},
                    {"agent": "data_helper", "type": "data_request"}
                ]
            }
        }
