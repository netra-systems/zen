"""Pipeline building logic for supervisor agent."""

from typing import List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import PipelineStepConfig


class PipelineBuilder:
    """Builds execution pipelines based on state and requirements."""
    
    def get_execution_pipeline(self, prompt: str, 
                               state: DeepAgentState) -> List[PipelineStepConfig]:
        """Determine execution pipeline based on prompt."""
        pipeline = self._build_base_pipeline()
        self._add_conditional_steps(pipeline, state)
        pipeline.append(PipelineStepConfig(agent_name="reporting"))
        return pipeline
    
    def _build_base_pipeline(self) -> List[PipelineStepConfig]:
        """Build base pipeline with triage."""
        return [PipelineStepConfig(agent_name="triage")]
    
    def _add_conditional_steps(self, pipeline: List[PipelineStepConfig],
                              state: DeepAgentState) -> None:
        """Add conditional pipeline steps."""
        self._add_data_step_if_needed(pipeline, state)
        self._add_optimization_step_if_needed(pipeline, state)
        self._add_actions_step_if_needed(pipeline, state)
    
    def _add_data_step_if_needed(self, pipeline: List[PipelineStep], state: DeepAgentState) -> None:
        """Add data analysis step if needed."""
        if self._needs_data_analysis(state):
            pipeline.append(PipelineStepConfig(agent_name="data"))
    
    def _add_optimization_step_if_needed(self, pipeline: List[PipelineStepConfig], state: DeepAgentState) -> None:
        """Add optimization step if needed."""
        if self._needs_optimization(state):
            pipeline.append(PipelineStepConfig(agent_name="optimization"))
    
    def _add_actions_step_if_needed(self, pipeline: List[PipelineStepConfig], state: DeepAgentState) -> None:
        """Add actions step if needed."""
        if self._needs_actions(state):
            pipeline.append(PipelineStepConfig(agent_name="actions"))
    
    def _needs_data_analysis(self, state: DeepAgentState) -> bool:
        """Check if data analysis is needed."""
        if not state.triage_result:
            return True
        if hasattr(state.triage_result, 'get'):
            return state.triage_result.get("requires_data", True)
        return True
    
    def _needs_optimization(self, state: DeepAgentState) -> bool:
        """Check if optimization is needed."""
        if not state.triage_result:
            return True
        if hasattr(state.triage_result, 'get'):
            return state.triage_result.get("requires_optimization", True)
        return True
    
    def _needs_actions(self, state: DeepAgentState) -> bool:
        """Check if action planning is needed."""
        if not state.triage_result:
            return True
        if hasattr(state.triage_result, 'get'):
            return state.triage_result.get("requires_actions", True)
        return True