from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

env = get_env()

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Complete Real Pipeline E2E Test Suite
# REMOVED_SYNTAX_ERROR: Tests the complete agent pipeline with real LLM calls and proper error handling.
# REMOVED_SYNTAX_ERROR: Maximum 300 lines, functions <=8 lines.
""

# Test framework import - using pytest fixtures instead

import sys
from pathlib import Path

from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
from typing import Dict, List
import asyncio
import os
import pytest
import uuid

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.tests.e2e.state_validation_utils import StateIntegrityChecker, StateValidationReporter

# REMOVED_SYNTAX_ERROR: @pytest.fixture

env.get("ENABLE_REAL_LLM_TESTING") != "true",

reason="Real LLM testing not enabled"



# REMOVED_SYNTAX_ERROR: class TestCompleteRealPipeline:

    # REMOVED_SYNTAX_ERROR: """Test complete real agent pipeline with proper error handling."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_complete_triage_to_data_pipeline(self, real_agent_setup):

        # REMOVED_SYNTAX_ERROR: """Test complete triage->data pipeline with real LLM calls."""

        # REMOVED_SYNTAX_ERROR: setup = real_agent_setup

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="Optimize AI workload costs for enterprise batch processing")

        # REMOVED_SYNTAX_ERROR: pipeline_result = await self._execute_complete_real_pipeline(setup, state)

        # REMOVED_SYNTAX_ERROR: await self._validate_complete_pipeline_integrity(pipeline_result, state)

# REMOVED_SYNTAX_ERROR: async def _execute_complete_real_pipeline(self, setup: Dict, state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute complete pipeline with real agents."""

    # REMOVED_SYNTAX_ERROR: results = self._init_pipeline_results()

    # REMOVED_SYNTAX_ERROR: results = await self._execute_all_pipeline_stages(setup, state, results)

    # REMOVED_SYNTAX_ERROR: return self._finalize_pipeline_timing(results)

# REMOVED_SYNTAX_ERROR: def _init_pipeline_results(self) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Initialize pipeline results structure."""

    # REMOVED_SYNTAX_ERROR: return {"stages": [}, "start_time": asyncio.get_event_loop().time()]

# REMOVED_SYNTAX_ERROR: async def _execute_all_pipeline_stages(self, setup: Dict, state: DeepAgentState, results: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute all pipeline stages and collect results."""

    # REMOVED_SYNTAX_ERROR: triage_result = await self._execute_triage_stage(setup, state)

    # REMOVED_SYNTAX_ERROR: results["stages"].append({"name": "triage", "result": triage_result})

    # REMOVED_SYNTAX_ERROR: data_result = await self._execute_data_stage(setup, state)

    # REMOVED_SYNTAX_ERROR: results["stages"].append({"name": "data", "result": data_result})

    # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: def _finalize_pipeline_timing(self, results: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Finalize pipeline results with timing calculations."""

    # REMOVED_SYNTAX_ERROR: results["end_time"] = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: results["total_duration"] = results["end_time"] - results["start_time"]

    # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: async def _execute_triage_stage(self, setup: Dict, state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute triage stage with real agent."""

    # REMOVED_SYNTAX_ERROR: agent = setup['agents']['triage']

    # REMOVED_SYNTAX_ERROR: agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: agent.user_id = setup['user_id']

    # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: await agent.run(state.user_request, agent.thread_id, agent.user_id, setup['run_id'])

    # REMOVED_SYNTAX_ERROR: return self._create_stage_result("triage", agent.state, start_time)

# REMOVED_SYNTAX_ERROR: async def _execute_data_stage(self, setup: Dict, state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute data stage with real agent."""

    # REMOVED_SYNTAX_ERROR: agent = setup['agents']['data']

    # REMOVED_SYNTAX_ERROR: agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: agent.user_id = setup['user_id']

    # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: await agent.run(state.user_request, agent.thread_id, agent.user_id, setup['run_id'])

    # REMOVED_SYNTAX_ERROR: return self._create_stage_result("data", agent.state, start_time)

# REMOVED_SYNTAX_ERROR: def _create_stage_result(self, stage_name: str, agent_state: SubAgentLifecycle,

# REMOVED_SYNTAX_ERROR: start_time: float) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Create result for pipeline stage."""

    # REMOVED_SYNTAX_ERROR: duration = asyncio.get_event_loop().time() - start_time

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "stage": stage_name, "agent_state": agent_state,

    # REMOVED_SYNTAX_ERROR: "success": agent_state == SubAgentLifecycle.COMPLETED,

    # REMOVED_SYNTAX_ERROR: "duration": duration

    

# REMOVED_SYNTAX_ERROR: async def _validate_complete_pipeline_integrity(self, pipeline_result: Dict,

# REMOVED_SYNTAX_ERROR: state: DeepAgentState):

    # REMOVED_SYNTAX_ERROR: """Validate complete pipeline integrity."""

    # REMOVED_SYNTAX_ERROR: assert len(pipeline_result["stages"]) == 2, "Should have 2 pipeline stages"

    # REMOVED_SYNTAX_ERROR: assert pipeline_result["total_duration"] > 0, "Should have measurable duration"

    # Validate each stage completed successfully

    # REMOVED_SYNTAX_ERROR: for stage in pipeline_result["stages"]:

        # REMOVED_SYNTAX_ERROR: assert stage["success"], "formatted_string"

        # REMOVED_SYNTAX_ERROR: assert stage["duration"] > 0, "formatted_string"

        # Validate state integrity

        # REMOVED_SYNTAX_ERROR: integrity_checker = StateIntegrityChecker()

        # REMOVED_SYNTAX_ERROR: integrity_checker.check_pipeline_state_consistency(state)

# REMOVED_SYNTAX_ERROR: class TestRealPipelineErrorHandling:

    # REMOVED_SYNTAX_ERROR: """Test error handling in real agent pipeline."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_pipeline_with_invalid_request(self, real_agent_setup):

        # REMOVED_SYNTAX_ERROR: """Test pipeline behavior with invalid user request."""

        # REMOVED_SYNTAX_ERROR: setup = real_agent_setup

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="")  # Invalid empty request

        # REMOVED_SYNTAX_ERROR: error_result = await self._execute_pipeline_with_errors(setup, state)

        # REMOVED_SYNTAX_ERROR: await self._validate_error_handling(error_result)

# REMOVED_SYNTAX_ERROR: async def _execute_pipeline_with_errors(self, setup: Dict, state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute pipeline expecting errors."""

    # REMOVED_SYNTAX_ERROR: results = {"errors": [}, "stages": []]

    # REMOVED_SYNTAX_ERROR: return await self._try_execute_triage_with_errors(setup, state, results)

# REMOVED_SYNTAX_ERROR: async def _try_execute_triage_with_errors(self, setup: Dict, state: DeepAgentState, results: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Try executing triage with error handling."""

    # REMOVED_SYNTAX_ERROR: try:

        # REMOVED_SYNTAX_ERROR: triage_agent = self._prepare_triage_agent_for_error_test(setup)

        # REMOVED_SYNTAX_ERROR: await triage_agent.run(state.user_request, triage_agent.thread_id, triage_agent.user_id, setup['run_id'])

        # REMOVED_SYNTAX_ERROR: results["stages"].append({"name": "triage", "state": triage_agent.state})

        # REMOVED_SYNTAX_ERROR: except Exception as e:

            # REMOVED_SYNTAX_ERROR: results["errors"].append({"stage": "triage", "error": str(e)})

            # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: def _prepare_triage_agent_for_error_test(self, setup: Dict):

    # REMOVED_SYNTAX_ERROR: """Prepare triage agent for error testing."""

    # REMOVED_SYNTAX_ERROR: triage_agent = setup['agents']['triage']

    # REMOVED_SYNTAX_ERROR: triage_agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: return triage_agent

# REMOVED_SYNTAX_ERROR: async def _validate_error_handling(self, error_result: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate error handling is graceful."""
    # Should either complete with fallback or record graceful failure

    # REMOVED_SYNTAX_ERROR: if error_result["stages"]:
        # If stages completed, should be COMPLETED or FAILED (not crashed)

        # REMOVED_SYNTAX_ERROR: for stage in error_result["stages"]:

            # REMOVED_SYNTAX_ERROR: assert stage["state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]

            # Should not have unhandled exceptions

            # REMOVED_SYNTAX_ERROR: for error in error_result["errors"]:
                # Error messages should be informative, not stack traces

                # REMOVED_SYNTAX_ERROR: assert "agent" in error["error"].lower() or "validation" in error["error"].lower()

# REMOVED_SYNTAX_ERROR: class TestRealPipelineWithValidationReporting:

    # REMOVED_SYNTAX_ERROR: """Test real pipeline with comprehensive validation reporting."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_pipeline_with_comprehensive_validation(self, real_agent_setup):

        # REMOVED_SYNTAX_ERROR: """Test pipeline with detailed validation reporting."""

        # REMOVED_SYNTAX_ERROR: setup = real_agent_setup

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="Comprehensive performance optimization analysis")

        # REMOVED_SYNTAX_ERROR: reporter = StateValidationReporter()

        # REMOVED_SYNTAX_ERROR: pipeline_result = await self._execute_with_validation_reporting(setup, state, reporter)

        # REMOVED_SYNTAX_ERROR: await self._validate_comprehensive_results(pipeline_result, reporter)

# REMOVED_SYNTAX_ERROR: async def _execute_with_validation_reporting(self, setup: Dict, state: DeepAgentState,

# REMOVED_SYNTAX_ERROR: reporter: StateValidationReporter) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute pipeline with comprehensive validation at each stage."""

    # REMOVED_SYNTAX_ERROR: results = {"validation_reports": [}, "agent_results": []]

    # REMOVED_SYNTAX_ERROR: results = await self._execute_triage_with_validation(setup, state, reporter, results)

    # REMOVED_SYNTAX_ERROR: results = await self._execute_data_with_validation(setup, state, reporter, results)

    # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: async def _execute_triage_with_validation(self, setup: Dict, state: DeepAgentState,

# REMOVED_SYNTAX_ERROR: reporter: StateValidationReporter, results: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute triage stage with validation reporting."""

    # REMOVED_SYNTAX_ERROR: triage_agent = self._setup_triage_for_validation(setup)

    # REMOVED_SYNTAX_ERROR: await triage_agent.run(state.user_request, triage_agent.thread_id, triage_agent.user_id, setup['run_id'])

    # REMOVED_SYNTAX_ERROR: triage_report = reporter.validate_and_report_triage(state)

    # REMOVED_SYNTAX_ERROR: results["validation_reports"].append(triage_report)

    # REMOVED_SYNTAX_ERROR: results["agent_results"].append({"stage": "triage", "state": triage_agent.state})

    # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: def _setup_triage_for_validation(self, setup: Dict):

    # REMOVED_SYNTAX_ERROR: """Setup triage agent for validation."""

    # REMOVED_SYNTAX_ERROR: triage_agent = setup['agents']['triage']

    # REMOVED_SYNTAX_ERROR: triage_agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: return triage_agent

# REMOVED_SYNTAX_ERROR: async def _execute_data_with_validation(self, setup: Dict, state: DeepAgentState,

# REMOVED_SYNTAX_ERROR: reporter: StateValidationReporter, results: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute data stage with validation reporting."""

    # REMOVED_SYNTAX_ERROR: original_triage = state.triage_result

    # REMOVED_SYNTAX_ERROR: data_agent = self._setup_data_for_validation(setup)

    # REMOVED_SYNTAX_ERROR: await data_agent.run(state.user_request, data_agent.thread_id, data_agent.user_id, setup['run_id'])

    # REMOVED_SYNTAX_ERROR: self._collect_data_validation_reports(reporter, state, original_triage, results)

    # REMOVED_SYNTAX_ERROR: results["agent_results"].append({"stage": "data", "state": data_agent.state})

    # REMOVED_SYNTAX_ERROR: return results

# REMOVED_SYNTAX_ERROR: def _setup_data_for_validation(self, setup: Dict):

    # REMOVED_SYNTAX_ERROR: """Setup data agent for validation."""

    # REMOVED_SYNTAX_ERROR: data_agent = setup['agents']['data']

    # REMOVED_SYNTAX_ERROR: data_agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: return data_agent

# REMOVED_SYNTAX_ERROR: def _collect_data_validation_reports(self, reporter: StateValidationReporter, state: DeepAgentState,

# REMOVED_SYNTAX_ERROR: original_triage, results: Dict):

    # REMOVED_SYNTAX_ERROR: """Collect validation reports for data stage."""

    # REMOVED_SYNTAX_ERROR: data_report = reporter.validate_and_report_data(state)

    # REMOVED_SYNTAX_ERROR: handoff_report = reporter.validate_and_report_handoff(state, original_triage)

    # REMOVED_SYNTAX_ERROR: results["validation_reports"].extend([data_report, handoff_report])

# REMOVED_SYNTAX_ERROR: async def _validate_comprehensive_results(self, pipeline_result: Dict,

# REMOVED_SYNTAX_ERROR: reporter: StateValidationReporter):

    # REMOVED_SYNTAX_ERROR: """Validate comprehensive pipeline results."""

    # REMOVED_SYNTAX_ERROR: self._validate_agent_completion_status(pipeline_result)

    # REMOVED_SYNTAX_ERROR: self._validate_validation_report_success(pipeline_result)

    # REMOVED_SYNTAX_ERROR: self._validate_summary_report_metrics(reporter)

# REMOVED_SYNTAX_ERROR: def _validate_agent_completion_status(self, pipeline_result: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate all agents completed successfully."""

    # REMOVED_SYNTAX_ERROR: for agent_result in pipeline_result["agent_results"]:

        # REMOVED_SYNTAX_ERROR: assert agent_result["state"] == SubAgentLifecycle.COMPLETED, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def _validate_validation_report_success(self, pipeline_result: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate all validation reports passed."""

    # REMOVED_SYNTAX_ERROR: for report in pipeline_result["validation_reports"]:

        # REMOVED_SYNTAX_ERROR: assert report["success"], "formatted_string"

# REMOVED_SYNTAX_ERROR: def _validate_summary_report_metrics(self, reporter: StateValidationReporter):

    # REMOVED_SYNTAX_ERROR: """Validate summary report metrics."""

    # REMOVED_SYNTAX_ERROR: summary = reporter.get_summary_report()

    # REMOVED_SYNTAX_ERROR: assert summary["success_rate"] == 1.0, "All validations should pass"

    # REMOVED_SYNTAX_ERROR: assert summary["total_validations"] >= 3, "Should have comprehensive validations"

# REMOVED_SYNTAX_ERROR: class TestRealPipelineConcurrencyAndStability:

    # REMOVED_SYNTAX_ERROR: """Test real pipeline concurrency and stability."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_pipeline_executions(self, real_agent_setup):

        # REMOVED_SYNTAX_ERROR: """Test multiple concurrent pipeline executions."""

        # REMOVED_SYNTAX_ERROR: setup = real_agent_setup

        # REMOVED_SYNTAX_ERROR: concurrent_tasks = await self._create_concurrent_pipeline_tasks(setup)

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        # REMOVED_SYNTAX_ERROR: await self._validate_concurrent_stability(results)

# REMOVED_SYNTAX_ERROR: async def _create_concurrent_pipeline_tasks(self, setup: Dict) -> List:

    # REMOVED_SYNTAX_ERROR: """Create concurrent pipeline execution tasks."""

    # REMOVED_SYNTAX_ERROR: tasks = []

    # REMOVED_SYNTAX_ERROR: for i in range(3):

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="formatted_string")

        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(self._execute_single_pipeline(setup, state, i))

        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # REMOVED_SYNTAX_ERROR: return tasks

# REMOVED_SYNTAX_ERROR: async def _execute_single_pipeline(self, setup: Dict, state: DeepAgentState,

# REMOVED_SYNTAX_ERROR: task_id: int) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute single pipeline for concurrency testing."""

    # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"

    # Execute triage

    # REMOVED_SYNTAX_ERROR: triage_agent = setup['agents']['triage']

    # REMOVED_SYNTAX_ERROR: triage_agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: triage_agent.user_id = "formatted_string"

    # REMOVED_SYNTAX_ERROR: await triage_agent.run(state.user_request, triage_agent.thread_id, triage_agent.user_id, run_id)

    # REMOVED_SYNTAX_ERROR: return {"task_id": task_id, "triage_state": triage_agent.state, "run_id": run_id}

# REMOVED_SYNTAX_ERROR: async def _validate_concurrent_stability(self, results: List):

    # REMOVED_SYNTAX_ERROR: """Validate concurrent execution stability."""

    # REMOVED_SYNTAX_ERROR: assert len(results) == 3, "All concurrent tasks should complete"

    # REMOVED_SYNTAX_ERROR: self._validate_each_concurrent_result(results)

# REMOVED_SYNTAX_ERROR: def _validate_each_concurrent_result(self, results: List):

    # REMOVED_SYNTAX_ERROR: """Validate each concurrent execution result."""

    # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):

        # REMOVED_SYNTAX_ERROR: if isinstance(result, Exception):

            # REMOVED_SYNTAX_ERROR: self._validate_exception_result(result, i)

            # REMOVED_SYNTAX_ERROR: else:

                # REMOVED_SYNTAX_ERROR: self._validate_success_result(result, i)

# REMOVED_SYNTAX_ERROR: def _validate_exception_result(self, result: Exception, task_id: int):

    # REMOVED_SYNTAX_ERROR: """Validate exception result is handled gracefully."""

    # REMOVED_SYNTAX_ERROR: assert "agent" in str(result).lower() or "timeout" in str(result).lower(), \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def _validate_success_result(self, result: Dict, task_id: int):

    # REMOVED_SYNTAX_ERROR: """Validate successful execution result."""

    # REMOVED_SYNTAX_ERROR: assert result["task_id"] == task_id, "formatted_string"

    # REMOVED_SYNTAX_ERROR: assert result["triage_state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED], \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: class TestRealPipelinePerformanceMetrics:

    # REMOVED_SYNTAX_ERROR: """Test real pipeline performance and metrics collection."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_pipeline_performance_metrics(self, real_agent_setup):

        # REMOVED_SYNTAX_ERROR: """Test pipeline performance metrics collection."""

        # REMOVED_SYNTAX_ERROR: setup = real_agent_setup

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState(user_request="Performance optimization with metrics tracking")

        # REMOVED_SYNTAX_ERROR: metrics = await self._execute_and_collect_metrics(setup, state)

        # REMOVED_SYNTAX_ERROR: await self._validate_performance_metrics(metrics)

# REMOVED_SYNTAX_ERROR: async def _execute_and_collect_metrics(self, setup: Dict, state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute pipeline and collect detailed metrics."""

    # REMOVED_SYNTAX_ERROR: metrics = self._init_metrics_collection()

    # REMOVED_SYNTAX_ERROR: metrics = await self._collect_stage_metrics(setup, state, metrics)

    # REMOVED_SYNTAX_ERROR: return self._finalize_metrics_timing(metrics)

# REMOVED_SYNTAX_ERROR: def _init_metrics_collection(self) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Initialize metrics collection structure."""

    # REMOVED_SYNTAX_ERROR: return {"stages": [}, "total_start": asyncio.get_event_loop().time()]

# REMOVED_SYNTAX_ERROR: async def _collect_stage_metrics(self, setup: Dict, state: DeepAgentState, metrics: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Collect metrics for all stages."""

    # REMOVED_SYNTAX_ERROR: triage_metrics = await self._execute_stage_with_metrics(setup, 'triage', state)

    # REMOVED_SYNTAX_ERROR: metrics["stages"].append(triage_metrics)

    # REMOVED_SYNTAX_ERROR: data_metrics = await self._execute_stage_with_metrics(setup, 'data', state)

    # REMOVED_SYNTAX_ERROR: metrics["stages"].append(data_metrics)

    # REMOVED_SYNTAX_ERROR: return metrics

# REMOVED_SYNTAX_ERROR: def _finalize_metrics_timing(self, metrics: Dict) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Finalize metrics with total timing calculations."""

    # REMOVED_SYNTAX_ERROR: metrics["total_end"] = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: metrics["total_duration"] = metrics["total_end"] - metrics["total_start"]

    # REMOVED_SYNTAX_ERROR: return metrics

# REMOVED_SYNTAX_ERROR: async def _execute_stage_with_metrics(self, setup: Dict, stage_name: str,

# REMOVED_SYNTAX_ERROR: state: DeepAgentState) -> Dict:

    # REMOVED_SYNTAX_ERROR: """Execute single stage with detailed metrics."""

    # REMOVED_SYNTAX_ERROR: agent = setup['agents'][stage_name]

    # REMOVED_SYNTAX_ERROR: agent.websocket_manager = setup['websocket']

    # REMOVED_SYNTAX_ERROR: start_time = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: await agent.run(state.user_request, agent.thread_id, agent.user_id, setup['run_id'])

    # REMOVED_SYNTAX_ERROR: end_time = asyncio.get_event_loop().time()

    # REMOVED_SYNTAX_ERROR: return { )

    # REMOVED_SYNTAX_ERROR: "stage": stage_name, "start_time": start_time, "end_time": end_time,

    # REMOVED_SYNTAX_ERROR: "duration": end_time - start_time, "agent_state": agent.state

    

# REMOVED_SYNTAX_ERROR: async def _validate_performance_metrics(self, metrics: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate performance metrics are reasonable."""

    # REMOVED_SYNTAX_ERROR: self._validate_basic_metrics_structure(metrics)

    # REMOVED_SYNTAX_ERROR: self._validate_total_duration_consistency(metrics)

    # REMOVED_SYNTAX_ERROR: self._validate_individual_stage_performance(metrics)

# REMOVED_SYNTAX_ERROR: def _validate_basic_metrics_structure(self, metrics: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate basic metrics structure and values."""

    # REMOVED_SYNTAX_ERROR: assert metrics["total_duration"] > 0, "Should have measurable total duration"

    # REMOVED_SYNTAX_ERROR: assert len(metrics["stages"]) == 2, "Should have metrics for all stages"

# REMOVED_SYNTAX_ERROR: def _validate_total_duration_consistency(self, metrics: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate total duration is consistent with stage durations."""

    # REMOVED_SYNTAX_ERROR: total_stage_duration = sum(stage["duration"] for stage in metrics["stages"])

    # REMOVED_SYNTAX_ERROR: assert total_stage_duration <= metrics["total_duration"] + 1.0, \
    # REMOVED_SYNTAX_ERROR: "Stage durations should not exceed total (allowing 1s margin)"

# REMOVED_SYNTAX_ERROR: def _validate_individual_stage_performance(self, metrics: Dict):

    # REMOVED_SYNTAX_ERROR: """Validate individual stage performance metrics."""

    # REMOVED_SYNTAX_ERROR: for stage in metrics["stages"]:

        # REMOVED_SYNTAX_ERROR: assert stage["duration"] < 60.0, "formatted_string"

        # REMOVED_SYNTAX_ERROR: assert stage["agent_state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED], \
        # REMOVED_SYNTAX_ERROR: "formatted_string"