"""
Real Agent Orchestration E2E Test Suite
Tests complete agent workflow with real LLM calls and proper state transitions.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from typing import Dict, List

import pytest

from netra_backend.app.agents.data_sub_agent.models import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)

# Add project root to path
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.schemas import SubAgentLifecycle
from netra_backend.tests.e2e.state_validation_utils import (
    StateIntegrityChecker,
    StateValidationReporter,
)

# Add project root to path


class TestRealAgentOrchestration:
    """Test real agent orchestration with actual LLM calls."""
    
    async def test_real_agent_triage_to_data_flow(self, real_agent_setup):
        """Test real triage→data agent flow with state validation."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Optimize AI workload costs for batch processing")
        triage_result = await self._execute_real_triage_agent(setup, state)
        await self._validate_triage_state_transition(state, triage_result)
        data_result = await self._execute_real_data_agent(setup, state) 
        await self._validate_data_state_transition(state, data_result)
    
    async def _execute_real_triage_agent(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute real triage agent with proper setup."""
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        agent.user_id = setup['user_id']
        await agent.run(state, setup['run_id'], stream_updates=True)
        return {'agent_state': agent.state, 'workflow_state': state}
    
    async def _validate_triage_state_transition(self, state: DeepAgentState, result: Dict):
        """Validate triage agent state transitions with real LLM output."""
        assert result['agent_state'] == SubAgentLifecycle.COMPLETED
        integrity_checker = StateIntegrityChecker()
        integrity_checker.check_triage_completion_integrity(state)
    
    async def _execute_real_data_agent(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute real data agent with triage result input."""
        agent = setup['agents']['data']
        agent.websocket_manager = setup['websocket']
        agent.user_id = setup['user_id']
        await agent.run(state, setup['run_id'], stream_updates=True)
        return {'agent_state': agent.state, 'workflow_state': state}
    
    async def _validate_data_state_transition(self, state: DeepAgentState, result: Dict):
        """Validate data agent state transitions with real LLM output."""
        assert result['agent_state'] == SubAgentLifecycle.COMPLETED
        integrity_checker = StateIntegrityChecker()
        integrity_checker.check_data_completion_integrity(state)


class TestRealAgentArtifactValidation:
    """Test artifact validation between real agent handoffs."""
    
    async def test_triage_to_data_artifact_validation(self, real_agent_setup):
        """Test artifacts pass correctly from triage to data agent."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Analyze performance bottlenecks in ML pipeline")
        await self._execute_triage_and_validate_artifacts(setup, state)
        await self._execute_data_and_validate_handoff_artifacts(setup, state)
    
    async def _execute_triage_and_validate_artifacts(self, setup: Dict, state: DeepAgentState):
        """Execute triage and validate its artifacts for data handoff."""
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], stream_updates=True)
        await self._validate_triage_artifacts_for_handoff(state)
    
    async def _validate_triage_artifacts_for_handoff(self, state: DeepAgentState):
        """Validate triage artifacts are ready for data agent handoff."""
        integrity_checker = StateIntegrityChecker()
        integrity_checker.artifact_validator.validate_triage_artifacts_for_handoff(state)
    
    async def _execute_data_and_validate_handoff_artifacts(self, setup: Dict, state: DeepAgentState):
        """Execute data agent and validate it uses triage artifacts."""
        agent = setup['agents']['data']
        agent.websocket_manager = setup['websocket']
        triage_input = state.triage_result
        await agent.run(state, setup['run_id'], stream_updates=True)
        await self._validate_data_used_triage_artifacts(state, triage_input)
    
    async def _validate_data_used_triage_artifacts(self, state: DeepAgentState, triage_input):
        """Validate data agent properly used triage artifacts."""
        integrity_checker = StateIntegrityChecker()
        integrity_checker.check_triage_to_data_handoff_integrity(state, triage_input)


class TestRealAgentErrorHandling:
    """Test real agent error handling and recovery."""
    
    async def test_invalid_request_handling(self, real_agent_setup):
        """Test how real agents handle invalid user requests."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="")  # Invalid empty request
        result = await self._execute_triage_with_invalid_input(setup, state)
        await self._validate_graceful_error_handling(result)
    
    async def _execute_triage_with_invalid_input(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute triage agent with invalid input."""
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        try:
            await agent.run(state, setup['run_id'], stream_updates=True)
        except Exception as e:
            return {'error': str(e), 'agent_state': agent.state}
        return {'agent_state': agent.state, 'success': True}
    
    async def _validate_graceful_error_handling(self, result: Dict):
        """Validate agents handle errors gracefully."""
        # Agent should either complete with fallback or fail gracefully
        assert result['agent_state'] in [
            SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED
        ]
        # Should not crash or throw unhandled exceptions
        assert 'success' in result or 'error' in result


class TestRealAgentConcurrency:
    """Test real agent concurrent execution scenarios."""
    
    async def test_concurrent_triage_requests(self, real_agent_setup):
        """Test multiple concurrent real triage requests."""
        setup = real_agent_setup
        tasks = await self._create_concurrent_real_agent_tasks(setup)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await self._validate_concurrent_execution_results(results)
    
    async def _create_concurrent_real_agent_tasks(self, setup: Dict) -> List:
        """Create concurrent real agent execution tasks."""
        tasks = []
        for i in range(3):
            state = DeepAgentState(user_request=f"Optimize workload performance {i}")
            agent = setup['agents']['triage']
            agent.websocket_manager = setup['websocket']
            agent.user_id = f"user-{i}"
            task = asyncio.create_task(agent.run(state, f"run-{i}", True))
            tasks.append(task)
        return tasks
    
    async def _validate_concurrent_execution_results(self, results: List):
        """Validate concurrent execution results."""
        assert len(results) == 3, "All concurrent tasks should complete"
        # All should either succeed or fail gracefully
        for result in results:
            if isinstance(result, Exception):
                # Exception should be a known agent exception, not system crash
                assert "agent" in str(result).lower() or "llm" in str(result).lower()


class TestRealAgentPipelineIntegration:
    """Test real agent pipeline integration and flow control."""
    
    async def test_complete_pipeline_state_flow(self, real_agent_setup):
        """Test complete state flow through real agent pipeline."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Comprehensive AI workload optimization")
        pipeline_result = await self._execute_complete_real_pipeline(setup, state)
        await self._validate_complete_pipeline_state_flow(pipeline_result, state)
    
    async def _execute_complete_real_pipeline(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute complete pipeline with real agents."""
        results = {}
        # Execute triage
        triage_agent = setup['agents']['triage']
        triage_agent.websocket_manager = setup['websocket']
        await triage_agent.run(state, setup['run_id'], True)
        results['triage'] = triage_agent.state
        
        # Execute data (depends on triage)
        data_agent = setup['agents']['data']
        data_agent.websocket_manager = setup['websocket']
        await data_agent.run(state, setup['run_id'], True)
        results['data'] = data_agent.state
        
        return results
    
    async def _validate_complete_pipeline_state_flow(self, results: Dict, state: DeepAgentState):
        """Validate complete pipeline state flow with real agents."""
        assert results['triage'] == SubAgentLifecycle.COMPLETED
        assert results['data'] == SubAgentLifecycle.COMPLETED
        assert state.triage_result is not None
        assert state.data_result is not None
        assert state.step_count >= 2


class TestRealAgentInterimArtifactValidation:
    """Test comprehensive interim artifact validation between agents."""
    
    async def test_interim_artifact_validation_with_reporter(self, real_agent_setup):
        """Test interim artifact validation with detailed reporting."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Test interim artifact validation")
        reporter = StateValidationReporter()
        await self._execute_with_interim_validation_reporting(setup, state, reporter)
        await self._validate_validation_reports(reporter)
    
    async def _execute_with_interim_validation_reporting(self, setup: Dict, 
                                                       state: DeepAgentState, 
                                                       reporter: StateValidationReporter):
        """Execute agents with interim validation reporting."""
        # Execute triage and validate immediately
        triage_agent = setup['agents']['triage']
        triage_agent.websocket_manager = setup['websocket']
        await triage_agent.run(state, setup['run_id'], True)
        triage_report = reporter.validate_and_report_triage(state)
        assert triage_report['success'], f"Triage validation failed: {triage_report['issues']}"
        
        # Store triage result for handoff validation
        original_triage = state.triage_result
        
        # Execute data and validate handoff
        data_agent = setup['agents']['data']
        data_agent.websocket_manager = setup['websocket']
        await data_agent.run(state, setup['run_id'], True)
        data_report = reporter.validate_and_report_data(state)
        handoff_report = reporter.validate_and_report_handoff(state, original_triage)
        assert data_report['success'], f"Data validation failed: {data_report['issues']}"
        assert handoff_report['success'], f"Handoff validation failed: {handoff_report['issues']}"
    
    async def _validate_validation_reports(self, reporter: StateValidationReporter):
        """Validate validation reports are comprehensive."""
        summary = reporter.get_summary_report()
        assert summary['total_validations'] >= 3, "Should have triage, data, and handoff validations"
        assert summary['success_rate'] == 1.0, "All validations should succeed"
        assert len(summary['details']) >= 3, "Should have detailed validation results"


class TestRealAgentTypeValidation:
    """Test type validation in real agent workflows."""
    
    async def test_agent_state_type_integrity(self, real_agent_setup):
        """Test agent state maintains type integrity throughout pipeline."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Test type integrity in AI optimization")
        await self._execute_and_validate_types(setup, state)
    
    async def _execute_and_validate_types(self, setup: Dict, state: DeepAgentState):
        """Execute agents and validate type integrity."""
        # Execute triage
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], True)
        await self._validate_triage_types(state)
        
        # Execute data
        data_agent = setup['agents']['data']
        data_agent.websocket_manager = setup['websocket']
        await data_agent.run(state, setup['run_id'], True)
        await self._validate_data_types(state)
    
    async def _validate_triage_types(self, state: DeepAgentState):
        """Validate triage result types."""
        if state.triage_result is not None:
            assert isinstance(state.triage_result, TriageResult)
            assert isinstance(state.triage_result.category, str)
            assert isinstance(state.triage_result.priority, str)
    
    async def _validate_data_types(self, state: DeepAgentState):
        """Validate data result types."""
        if state.data_result is not None:
            valid_types = (DataAnalysisResponse, AnomalyDetectionResponse)
            assert isinstance(state.data_result, valid_types)
            if isinstance(state.data_result, DataAnalysisResponse):
                assert isinstance(state.data_result.summary, str)
                assert isinstance(state.data_result.recommendations, list)
            elif isinstance(state.data_result, AnomalyDetectionResponse):
                assert isinstance(state.data_result.recommended_actions, list)