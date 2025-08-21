"""
Complete Real Pipeline E2E Test Suite
Tests the complete agent pipeline with real LLM calls and proper error handling.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import asyncio
import uuid
import os
from typing import Dict, List

from netra_backend.app.agents.state import DeepAgentState
from schemas import SubAgentLifecycle
from netra_backend.tests.e2e.state_validation_utils import StateIntegrityChecker, StateValidationReporter

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



@pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real LLM testing not enabled"
)
class TestCompleteRealPipeline:
    """Test complete real agent pipeline with proper error handling."""
    
    async def test_complete_triage_to_data_pipeline(self, real_agent_setup):
        """Test complete triage→data pipeline with real LLM calls."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Optimize AI workload costs for enterprise batch processing")
        pipeline_result = await self._execute_complete_real_pipeline(setup, state)
        await self._validate_complete_pipeline_integrity(pipeline_result, state)
    
    async def _execute_complete_real_pipeline(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute complete pipeline with real agents."""
        results = self._init_pipeline_results()
        results = await self._execute_all_pipeline_stages(setup, state, results)
        return self._finalize_pipeline_timing(results)
    
    def _init_pipeline_results(self) -> Dict:
        """Initialize pipeline results structure."""
        return {"stages": [], "start_time": asyncio.get_event_loop().time()}
    
    async def _execute_all_pipeline_stages(self, setup: Dict, state: DeepAgentState, results: Dict) -> Dict:
        """Execute all pipeline stages and collect results."""
        triage_result = await self._execute_triage_stage(setup, state)
        results["stages"].append({"name": "triage", "result": triage_result})
        data_result = await self._execute_data_stage(setup, state)
        results["stages"].append({"name": "data", "result": data_result})
        return results
    
    def _finalize_pipeline_timing(self, results: Dict) -> Dict:
        """Finalize pipeline results with timing calculations."""
        results["end_time"] = asyncio.get_event_loop().time()
        results["total_duration"] = results["end_time"] - results["start_time"]
        return results
    
    async def _execute_triage_stage(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute triage stage with real agent."""
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        agent.user_id = setup['user_id']
        start_time = asyncio.get_event_loop().time()
        await agent.run(state, setup['run_id'], stream_updates=True)
        return self._create_stage_result("triage", agent.state, start_time)
    
    async def _execute_data_stage(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute data stage with real agent."""
        agent = setup['agents']['data']
        agent.websocket_manager = setup['websocket']
        agent.user_id = setup['user_id']
        start_time = asyncio.get_event_loop().time()
        await agent.run(state, setup['run_id'], stream_updates=True)
        return self._create_stage_result("data", agent.state, start_time)
    
    def _create_stage_result(self, stage_name: str, agent_state: SubAgentLifecycle, 
                           start_time: float) -> Dict:
        """Create result for pipeline stage."""
        duration = asyncio.get_event_loop().time() - start_time
        return {
            "stage": stage_name, "agent_state": agent_state,
            "success": agent_state == SubAgentLifecycle.COMPLETED,
            "duration": duration
        }
    
    async def _validate_complete_pipeline_integrity(self, pipeline_result: Dict, 
                                                  state: DeepAgentState):
        """Validate complete pipeline integrity."""
        assert len(pipeline_result["stages"]) == 2, "Should have 2 pipeline stages"
        assert pipeline_result["total_duration"] > 0, "Should have measurable duration"
        
        # Validate each stage completed successfully
        for stage in pipeline_result["stages"]:
            assert stage["success"], f"Stage {stage['stage']} should succeed"
            assert stage["duration"] > 0, f"Stage {stage['stage']} should have duration"
        
        # Validate state integrity
        integrity_checker = StateIntegrityChecker()
        integrity_checker.check_pipeline_state_consistency(state)


class TestRealPipelineErrorHandling:
    """Test error handling in real agent pipeline."""
    
    async def test_pipeline_with_invalid_request(self, real_agent_setup):
        """Test pipeline behavior with invalid user request."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="")  # Invalid empty request
        error_result = await self._execute_pipeline_with_errors(setup, state)
        await self._validate_error_handling(error_result)
    
    async def _execute_pipeline_with_errors(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute pipeline expecting errors."""
        results = {"errors": [], "stages": []}
        return await self._try_execute_triage_with_errors(setup, state, results)
    
    async def _try_execute_triage_with_errors(self, setup: Dict, state: DeepAgentState, results: Dict) -> Dict:
        """Try executing triage with error handling."""
        try:
            triage_agent = self._prepare_triage_agent_for_error_test(setup)
            await triage_agent.run(state, setup['run_id'], stream_updates=True)
            results["stages"].append({"name": "triage", "state": triage_agent.state})
        except Exception as e:
            results["errors"].append({"stage": "triage", "error": str(e)})
        return results
    
    def _prepare_triage_agent_for_error_test(self, setup: Dict):
        """Prepare triage agent for error testing."""
        triage_agent = setup['agents']['triage']
        triage_agent.websocket_manager = setup['websocket']
        return triage_agent
    
    async def _validate_error_handling(self, error_result: Dict):
        """Validate error handling is graceful."""
        # Should either complete with fallback or record graceful failure
        if error_result["stages"]:
            # If stages completed, should be COMPLETED or FAILED (not crashed)
            for stage in error_result["stages"]:
                assert stage["state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]
        
        # Should not have unhandled exceptions
        for error in error_result["errors"]:
            # Error messages should be informative, not stack traces
            assert "agent" in error["error"].lower() or "validation" in error["error"].lower()


class TestRealPipelineWithValidationReporting:
    """Test real pipeline with comprehensive validation reporting."""
    
    async def test_pipeline_with_comprehensive_validation(self, real_agent_setup):
        """Test pipeline with detailed validation reporting."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Comprehensive performance optimization analysis")
        reporter = StateValidationReporter()
        pipeline_result = await self._execute_with_validation_reporting(setup, state, reporter)
        await self._validate_comprehensive_results(pipeline_result, reporter)
    
    async def _execute_with_validation_reporting(self, setup: Dict, state: DeepAgentState,
                                               reporter: StateValidationReporter) -> Dict:
        """Execute pipeline with comprehensive validation at each stage."""
        results = {"validation_reports": [], "agent_results": []}
        results = await self._execute_triage_with_validation(setup, state, reporter, results)
        results = await self._execute_data_with_validation(setup, state, reporter, results)
        return results
    
    async def _execute_triage_with_validation(self, setup: Dict, state: DeepAgentState, 
                                            reporter: StateValidationReporter, results: Dict) -> Dict:
        """Execute triage stage with validation reporting."""
        triage_agent = self._setup_triage_for_validation(setup)
        await triage_agent.run(state, setup['run_id'], True)
        triage_report = reporter.validate_and_report_triage(state)
        results["validation_reports"].append(triage_report)
        results["agent_results"].append({"stage": "triage", "state": triage_agent.state})
        return results
    
    def _setup_triage_for_validation(self, setup: Dict):
        """Setup triage agent for validation."""
        triage_agent = setup['agents']['triage']
        triage_agent.websocket_manager = setup['websocket']
        return triage_agent
    
    async def _execute_data_with_validation(self, setup: Dict, state: DeepAgentState,
                                          reporter: StateValidationReporter, results: Dict) -> Dict:
        """Execute data stage with validation reporting."""
        original_triage = state.triage_result
        data_agent = self._setup_data_for_validation(setup)
        await data_agent.run(state, setup['run_id'], True)
        self._collect_data_validation_reports(reporter, state, original_triage, results)
        results["agent_results"].append({"stage": "data", "state": data_agent.state})
        return results
    
    def _setup_data_for_validation(self, setup: Dict):
        """Setup data agent for validation."""
        data_agent = setup['agents']['data']
        data_agent.websocket_manager = setup['websocket']
        return data_agent
    
    def _collect_data_validation_reports(self, reporter: StateValidationReporter, state: DeepAgentState,
                                       original_triage, results: Dict):
        """Collect validation reports for data stage."""
        data_report = reporter.validate_and_report_data(state)
        handoff_report = reporter.validate_and_report_handoff(state, original_triage)
        results["validation_reports"].extend([data_report, handoff_report])
    
    async def _validate_comprehensive_results(self, pipeline_result: Dict, 
                                            reporter: StateValidationReporter):
        """Validate comprehensive pipeline results."""
        self._validate_agent_completion_status(pipeline_result)
        self._validate_validation_report_success(pipeline_result)
        self._validate_summary_report_metrics(reporter)
    
    def _validate_agent_completion_status(self, pipeline_result: Dict):
        """Validate all agents completed successfully."""
        for agent_result in pipeline_result["agent_results"]:
            assert agent_result["state"] == SubAgentLifecycle.COMPLETED, \
                   f"Stage {agent_result['stage']} should complete successfully"
    
    def _validate_validation_report_success(self, pipeline_result: Dict):
        """Validate all validation reports passed."""
        for report in pipeline_result["validation_reports"]:
            assert report["success"], f"Validation failed for {report['stage']}: {report.get('issues', [])}"
    
    def _validate_summary_report_metrics(self, reporter: StateValidationReporter):
        """Validate summary report metrics."""
        summary = reporter.get_summary_report()
        assert summary["success_rate"] == 1.0, "All validations should pass"
        assert summary["total_validations"] >= 3, "Should have comprehensive validations"


class TestRealPipelineConcurrencyAndStability:
    """Test real pipeline concurrency and stability."""
    
    async def test_concurrent_pipeline_executions(self, real_agent_setup):
        """Test multiple concurrent pipeline executions."""
        setup = real_agent_setup
        concurrent_tasks = await self._create_concurrent_pipeline_tasks(setup)
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        await self._validate_concurrent_stability(results)
    
    async def _create_concurrent_pipeline_tasks(self, setup: Dict) -> List:
        """Create concurrent pipeline execution tasks."""
        tasks = []
        for i in range(3):
            state = DeepAgentState(user_request=f"Optimize workload {i} for performance")
            task = asyncio.create_task(self._execute_single_pipeline(setup, state, i))
            tasks.append(task)
        return tasks
    
    async def _execute_single_pipeline(self, setup: Dict, state: DeepAgentState, 
                                     task_id: int) -> Dict:
        """Execute single pipeline for concurrency testing."""
        run_id = f"concurrent-{task_id}-{uuid.uuid4()}"
        
        # Execute triage
        triage_agent = setup['agents']['triage']
        triage_agent.websocket_manager = setup['websocket']
        triage_agent.user_id = f"user-{task_id}"
        await triage_agent.run(state, run_id, True)
        
        return {"task_id": task_id, "triage_state": triage_agent.state, "run_id": run_id}
    
    async def _validate_concurrent_stability(self, results: List):
        """Validate concurrent execution stability."""
        assert len(results) == 3, "All concurrent tasks should complete"
        self._validate_each_concurrent_result(results)
    
    def _validate_each_concurrent_result(self, results: List):
        """Validate each concurrent execution result."""
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._validate_exception_result(result, i)
            else:
                self._validate_success_result(result, i)
    
    def _validate_exception_result(self, result: Exception, task_id: int):
        """Validate exception result is handled gracefully."""
        assert "agent" in str(result).lower() or "timeout" in str(result).lower(), \
               f"Task {task_id} had unexpected exception: {result}"
    
    def _validate_success_result(self, result: Dict, task_id: int):
        """Validate successful execution result."""
        assert result["task_id"] == task_id, f"Task ID mismatch for task {task_id}"
        assert result["triage_state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED], \
               f"Task {task_id} should complete or fail gracefully"


class TestRealPipelinePerformanceMetrics:
    """Test real pipeline performance and metrics collection."""
    
    async def test_pipeline_performance_metrics(self, real_agent_setup):
        """Test pipeline performance metrics collection."""
        setup = real_agent_setup
        state = DeepAgentState(user_request="Performance optimization with metrics tracking")
        metrics = await self._execute_and_collect_metrics(setup, state)
        await self._validate_performance_metrics(metrics)
    
    async def _execute_and_collect_metrics(self, setup: Dict, state: DeepAgentState) -> Dict:
        """Execute pipeline and collect detailed metrics."""
        metrics = self._init_metrics_collection()
        metrics = await self._collect_stage_metrics(setup, state, metrics)
        return self._finalize_metrics_timing(metrics)
    
    def _init_metrics_collection(self) -> Dict:
        """Initialize metrics collection structure."""
        return {"stages": [], "total_start": asyncio.get_event_loop().time()}
    
    async def _collect_stage_metrics(self, setup: Dict, state: DeepAgentState, metrics: Dict) -> Dict:
        """Collect metrics for all stages."""
        triage_metrics = await self._execute_stage_with_metrics(setup, 'triage', state)
        metrics["stages"].append(triage_metrics)
        data_metrics = await self._execute_stage_with_metrics(setup, 'data', state)
        metrics["stages"].append(data_metrics)
        return metrics
    
    def _finalize_metrics_timing(self, metrics: Dict) -> Dict:
        """Finalize metrics with total timing calculations."""
        metrics["total_end"] = asyncio.get_event_loop().time()
        metrics["total_duration"] = metrics["total_end"] - metrics["total_start"]
        return metrics
    
    async def _execute_stage_with_metrics(self, setup: Dict, stage_name: str, 
                                        state: DeepAgentState) -> Dict:
        """Execute single stage with detailed metrics."""
        agent = setup['agents'][stage_name]
        agent.websocket_manager = setup['websocket']
        start_time = asyncio.get_event_loop().time()
        await agent.run(state, setup['run_id'], True)
        end_time = asyncio.get_event_loop().time()
        
        return {
            "stage": stage_name, "start_time": start_time, "end_time": end_time,
            "duration": end_time - start_time, "agent_state": agent.state
        }
    
    async def _validate_performance_metrics(self, metrics: Dict):
        """Validate performance metrics are reasonable."""
        self._validate_basic_metrics_structure(metrics)
        self._validate_total_duration_consistency(metrics)
        self._validate_individual_stage_performance(metrics)
    
    def _validate_basic_metrics_structure(self, metrics: Dict):
        """Validate basic metrics structure and values."""
        assert metrics["total_duration"] > 0, "Should have measurable total duration"
        assert len(metrics["stages"]) == 2, "Should have metrics for all stages"
    
    def _validate_total_duration_consistency(self, metrics: Dict):
        """Validate total duration is consistent with stage durations."""
        total_stage_duration = sum(stage["duration"] for stage in metrics["stages"])
        assert total_stage_duration <= metrics["total_duration"] + 1.0, \
               "Stage durations should not exceed total (allowing 1s margin)"
    
    def _validate_individual_stage_performance(self, metrics: Dict):
        """Validate individual stage performance metrics."""
        for stage in metrics["stages"]:
            assert stage["duration"] < 60.0, f"Stage {stage['stage']} took too long: {stage['duration']}s"
            assert stage["agent_state"] in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED], \
                   f"Stage {stage['stage']} should complete"