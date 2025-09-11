"""Pipeline building logic for supervisor agent."""

from typing import List

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig


class PipelineBuilder:
    """Builds execution pipelines based on state and requirements."""
    
    def get_execution_pipeline(self, prompt: str, 
                               user_context: UserExecutionContext) -> List[PipelineStepConfig]:
        """Determine execution pipeline based on prompt."""
        pipeline = self._build_base_pipeline()
        self._add_conditional_steps(pipeline, user_context)
        pipeline.append(PipelineStepConfig(agent_name="reporting"))
        return pipeline
    
    def _build_base_pipeline(self) -> List[PipelineStepConfig]:
        """Build base pipeline with triage."""
        return [PipelineStepConfig(agent_name="triage")]
    
    def _add_conditional_steps(self, pipeline: List[PipelineStepConfig],
                              user_context: UserExecutionContext) -> None:
        """Add conditional pipeline steps."""
        self._add_data_step_if_needed(pipeline, user_context)
        self._add_optimization_step_if_needed(pipeline, user_context)
        self._add_actions_step_if_needed(pipeline, user_context)
    
    def _add_data_step_if_needed(self, pipeline: List[PipelineStepConfig], user_context: UserExecutionContext) -> None:
        """Add data analysis step if needed."""
        if self._needs_data_analysis(user_context):
            pipeline.append(PipelineStepConfig(agent_name="data"))
    
    def _add_optimization_step_if_needed(self, pipeline: List[PipelineStepConfig], user_context: UserExecutionContext) -> None:
        """Add optimization step if needed."""
        if self._needs_optimization(user_context):
            pipeline.append(PipelineStepConfig(agent_name="optimization"))
    
    def _add_actions_step_if_needed(self, pipeline: List[PipelineStepConfig], user_context: UserExecutionContext) -> None:
        """Add actions step if needed."""
        if self._needs_actions(user_context):
            pipeline.append(PipelineStepConfig(agent_name="actions"))
    
    def _needs_data_analysis(self, user_context: UserExecutionContext) -> bool:
        """Check if data analysis is needed."""
        triage_result = user_context.get_state('triage_result')
        if not triage_result:
            return True
        if hasattr(triage_result, 'get'):
            return triage_result.get("requires_data", True)
        return True
    
    def _needs_optimization(self, user_context: UserExecutionContext) -> bool:
        """Check if optimization is needed."""
        triage_result = user_context.get_state('triage_result')
        if not triage_result:
            return True
        if hasattr(triage_result, 'get'):
            return triage_result.get("requires_optimization", True)
        return True
    
    def _needs_actions(self, user_context: UserExecutionContext) -> bool:
        """Check if action planning is needed."""
        triage_result = user_context.get_state('triage_result')
        if not triage_result:
            return True
        if hasattr(triage_result, 'get'):
            return triage_result.get("requires_actions", True)
        return True