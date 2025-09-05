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
        
        UVS SIMPLIFIED:
        - Only 2 agents are REQUIRED: Triage and Reporting (with UVS)
        - Default flow: Triage → Data Helper → Reporting
        - Reporting with UVS handles ALL scenarios, even failures
        
        Args:
            triage_result: Results from the triage agent including data sufficiency assessment
            
        Returns:
            List of pipeline steps tailored to the situation
        """
        # Extract data sufficiency from triage result
        data_sufficiency = triage_result.get("data_sufficiency", "unknown")
        
        # UVS: Reporting is ALWAYS the last step and can handle any scenario
        if data_sufficiency == "sufficient":
            # Full workflow when sufficient data is available
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data", "insights", 2, dependencies=[]),
                self._create_pipeline_step("optimization", "strategies", 3, dependencies=["data"]),
                self._create_pipeline_step("actions", "implementation", 4, dependencies=["optimization"]),
                self._create_pipeline_step("reporting", "full_report", 5, dependencies=[])  # UVS: No hard deps
            ]
        elif data_sufficiency == "partial":
            # Partial data - use data helper first
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data_helper", "data_guidance", 2, dependencies=[]),
                self._create_pipeline_step("data", "partial_insights", 3, dependencies=[]),
                self._create_pipeline_step("reporting", "partial_report", 4, dependencies=[])  # UVS handles partial
            ]
        elif data_sufficiency == "insufficient":
            # DEFAULT UVS FLOW: Triage → Data Helper → Reporting
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data_helper", "data_collection_guide", 2, dependencies=[]),
                self._create_pipeline_step("reporting", "guidance_report", 3, dependencies=[])  # UVS provides guidance
            ]
        else:
            # Unknown or triage failed - MINIMAL UVS FLOW
            logger.warning(f"Unknown data sufficiency: {data_sufficiency}. Using minimal UVS flow.")
            # Minimal flow: Just Data Helper and Reporting (UVS handles everything)
            return [
                self._create_pipeline_step("data_helper", "initial_guidance", 1, dependencies=[]),
                self._create_pipeline_step("reporting", "fallback_report", 2, dependencies=[])  # UVS fallback
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
        """Send workflow started notification via AgentWebSocketBridge."""
        if context.stream_updates:
            try:
                from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
                
                bridge = await get_agent_websocket_bridge()
                await bridge.notify_agent_started(
                    context.run_id, "WorkflowOrchestrator", 
                    {"workflow_started": True, "total_steps": len(self._workflow_steps)}
                )
            except Exception as e:
                logger.warning(f"Failed to send workflow started via bridge: {e}")
    
    async def _send_step_started(self, context: ExecutionContext, 
                                step: PipelineStep) -> None:
        """Send step started notification via AgentWebSocketBridge."""
        if context.stream_updates:
            try:
                from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
                
                bridge = await get_agent_websocket_bridge()
                await bridge.notify_agent_started(
                    context.run_id, step.agent_name, 
                    {"step_type": step.metadata.get("step_type"), "order": step.metadata.get("order")}
                )
            except Exception as e:
                logger.warning(f"Failed to send step started via bridge: {e}")
    
    async def _send_step_completed(self, context: ExecutionContext, 
                                  step: PipelineStep, result: ExecutionResult) -> None:
        """Send step completed notification via AgentWebSocketBridge."""
        if context.stream_updates:
            try:
                from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
                
                bridge = await get_agent_websocket_bridge()
                
                if result.success:
                    await bridge.notify_agent_completed(
                        context.run_id, step.agent_name,
                        result={"step_type": step.metadata.get("step_type")},
                        execution_time_ms=result.execution_time_ms
                    )
                else:
                    await bridge.notify_agent_error(
                        context.run_id, step.agent_name, 
                        result.error or "Step execution failed",
                        {"step_type": step.metadata.get("step_type")}
                    )
            except Exception as e:
                logger.warning(f"Failed to send step completed via bridge: {e}")
    
    async def _send_workflow_completed(self, context: ExecutionContext, 
                                      results: List[ExecutionResult]) -> None:
        """Send workflow completed notification via AgentWebSocketBridge."""
        if context.stream_updates:
            try:
                from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
                
                bridge = await get_agent_websocket_bridge()
                total_time = sum(r.execution_time_ms for r in results)
                success_count = sum(1 for r in results if r.success)
                
                await bridge.notify_agent_completed(
                    context.run_id, "WorkflowOrchestrator",
                    result={
                        "workflow_completed": True,
                        "successful_steps": success_count,
                        "total_steps": len(results)
                    },
                    execution_time_ms=total_time
                )
            except Exception as e:
                logger.warning(f"Failed to send workflow completed via bridge: {e}")
    
    def get_workflow_definition(self) -> List[Dict[str, Any]]:
        """Get workflow definition for monitoring.
        
        Returns default workflow configuration as list of steps for test compatibility.
        """
        return [
            {"agent_name": "triage", "step_type": "classification", "order": 1, "metadata": {"description": "Classify and assess request"}},
            {"agent_name": "data", "step_type": "insights", "order": 2, "metadata": {"description": "Gather and analyze data"}},
            {"agent_name": "optimization", "step_type": "strategies", "order": 3, "metadata": {"description": "Generate optimization strategies"}},
            {"agent_name": "actions", "step_type": "implementation", "order": 4, "metadata": {"description": "Define implementation actions"}},
            {"agent_name": "reporting", "step_type": "summary", "order": 5, "metadata": {"description": "Generate final report"}}
        ]
    
    def assess_data_completeness(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the completeness of data in the request.
        
        Args:
            request_data: The request data containing available and missing information
            
        Returns:
            Assessment dict with completeness score and workflow recommendation
        """
        # Extract completeness from request if provided
        completeness = request_data.get("completeness", 0.0)
        
        # If not provided, calculate based on available vs missing data
        if completeness == 0.0:
            available_data = request_data.get("available_data", {})
            missing_data = request_data.get("missing_data", [])
            
            if available_data and missing_data:
                total_fields = len(available_data) + len(missing_data)
                completeness = len(available_data) / total_fields if total_fields > 0 else 0.0
            elif available_data:
                # If only available data is provided, estimate based on typical requirements
                completeness = min(0.7, len(available_data) / 10)  # Assume 10 typical fields
        
        # Determine workflow based on completeness
        if completeness >= 0.8:
            workflow_type = "full_optimization"
            confidence = 0.90
        elif completeness >= 0.4:
            workflow_type = "modified_optimization"
            confidence = 0.65
        else:
            workflow_type = "data_collection_focus"
            confidence = 0.10
        
        return {
            "completeness": completeness,
            "workflow": workflow_type,
            "confidence": confidence,
            "data_sufficiency": self._classify_data_sufficiency(completeness)
        }
    
    def _classify_data_sufficiency(self, completeness: float) -> str:
        """Classify data sufficiency level based on completeness score.
        
        Args:
            completeness: Data completeness score between 0 and 1
            
        Returns:
            String classification of data sufficiency
        """
        if completeness >= 0.8:
            return "sufficient"
        elif completeness >= 0.4:
            return "partial"
        else:
            return "insufficient"
    
    async def select_workflow(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate workflow based on data assessment.
        
        Args:
            request_data: The request data to assess
            
        Returns:
            Workflow configuration with type, confidence, and phases
        """
        assessment = self.assess_data_completeness(request_data)
        
        workflow_config = {
            "type": assessment["workflow"],
            "confidence": assessment["confidence"],
            "completeness": assessment["completeness"],
            "phases": []
        }
        
        # Define phases based on workflow type
        if assessment["workflow"] == "full_optimization":
            workflow_config["phases"] = [
                "triage",
                "data_analysis",
                "optimization",
                "actions",
                "reporting"
            ]
        elif assessment["workflow"] == "modified_optimization":
            workflow_config["phases"] = [
                "triage",
                "quick_wins",  # Immediate value delivery
                "data_request",  # Request missing data
                "partial_optimization",  # Work with what we have
                "phased_actions",  # Progressive implementation
                "reporting_with_caveats"
            ]
        else:  # data_collection_focus
            workflow_config["phases"] = [
                "triage",
                "educate",  # Educate user on capabilities
                "collect",  # Collect necessary data
                "demonstrate_value"  # Show potential value
            ]
        
        return workflow_config
