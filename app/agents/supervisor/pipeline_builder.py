"""Pipeline building logic for supervisor agent."""

from typing import List
from app.agents.state import DeepAgentState
from app.agents.supervisor.execution_context import PipelineStep


class PipelineBuilder:
    """Builds execution pipelines based on state and requirements."""
    
    def get_execution_pipeline(self, prompt: str, 
                               state: DeepAgentState) -> List[PipelineStep]:
        """Determine execution pipeline based on prompt."""
        pipeline = self._build_base_pipeline()
        self._add_conditional_steps(pipeline, state)
        pipeline.append(PipelineStep(agent_name="reporting"))
        return pipeline
    
    def _build_base_pipeline(self) -> List[PipelineStep]:
        """Build base pipeline with triage."""
        return [PipelineStep(agent_name="triage")]
    
    def _add_conditional_steps(self, pipeline: List[PipelineStep],
                              state: DeepAgentState) -> None:
        """Add conditional pipeline steps."""
        if self._needs_data_analysis(state):
            pipeline.append(PipelineStep(agent_name="data"))
        if self._needs_optimization(state):
            pipeline.append(PipelineStep(agent_name="optimization"))
        if self._needs_actions(state):
            pipeline.append(PipelineStep(agent_name="actions"))
    
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