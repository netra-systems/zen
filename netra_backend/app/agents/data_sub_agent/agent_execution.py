"""Execution management for DataSubAgent."""

import time
from typing import Union

from netra_backend.app.agents.data_sub_agent.data_operations import DataOperations
from netra_backend.app.agents.data_sub_agent.execution_engine import ExecutionEngine
from netra_backend.app.agents.data_sub_agent.metrics_analyzer import MetricsAnalyzer
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.json_parsing_utils import (
    comprehensive_json_fix,
    ensure_agent_response_is_json,
)
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)
from netra_backend.app.schemas.strict_types import (
    AgentExecutionMetrics,
    TypedAgentResult,
)


class ExecutionManager:
    """Manages execution flow for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
    
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute advanced data analysis with ClickHouse integration."""
        start_time = time.time()
        try:
            return await self._execute_with_error_handling(state, run_id, stream_updates, start_time)
        except Exception as e:
            return self._handle_execution_failure(e, run_id, start_time)
    
    def _handle_execution_failure(self, error: Exception, run_id: str, start_time: float) -> TypedAgentResult:
        """Handle execution failure and create error result."""
        logger.error(f"Data analysis execution failed for run_id {run_id}: {error}")
        return self._create_failure_result(f"Data analysis failed: {error}", start_time)
    
    async def _execute_with_error_handling(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> TypedAgentResult:
        """Execute data analysis with comprehensive error handling."""
        execution_engine = self._create_execution_engine()
        data_ops, metrics_analyzer = self._create_operation_modules()
        await self._run_analysis_execution(execution_engine, state, run_id, stream_updates, data_ops, metrics_analyzer)
        result = await self._finalize_analysis_result(state, run_id, start_time)
        return result
    
    async def _run_analysis_execution(self, execution_engine, state: DeepAgentState, 
                                    run_id: str, stream_updates: bool, data_ops, metrics_analyzer) -> None:
        """Run the analysis execution process."""
        await execution_engine.execute_analysis(
            state, run_id, stream_updates, self.agent._send_update, data_ops, metrics_analyzer
        )
    
    async def _finalize_analysis_result(self, state: DeepAgentState, run_id: str, start_time: float) -> TypedAgentResult:
        """Finalize and return analysis result with completion message."""
        data_result = self._ensure_data_result(state.data_result)
        state.data_result = data_result
        state.step_count += 1
        
        # Send completion message
        await self._send_completion_message(run_id, data_result)
        
        return self._create_success_result(start_time, data_result)
        
    async def _send_completion_message(self, run_id: str, result: dict) -> None:
        """Send agent completion message via WebSocket."""
        try:
            # Send completion message through WebSocket manager directly
            if hasattr(self.agent, 'websocket_manager') and self.agent.websocket_manager:
                completion_message = {
                    "type": "agent_completed",
                    "payload": {
                        "run_id": run_id,
                        "result": result,
                        "agent_name": "DataSubAgent",
                        "timestamp": time.time()
                    }
                }
                # Note: Without thread_id or user_id, we cannot reliably send WebSocket messages
                # run_id should not be used as a user_id for WebSocket communication
                # This would need to be passed in via context if WebSocket messaging is required
                logger.debug(f"WebSocket message not sent for run_id {run_id} - no thread/user context available")
        except Exception as e:
            logger.debug(f"Failed to send completion message: {e}")
    
    def _create_execution_engine(self) -> ExecutionEngine:
        """Create and configure execution engine."""
        return ExecutionEngine(
            self.agent.clickhouse_ops, self.agent.query_builder, self.agent.analysis_engine,
            self.agent.redis_manager, self.agent.llm_manager
        )
    
    def _create_operation_modules(self) -> tuple:
        """Create data operations and metrics analyzer modules."""
        data_ops = self._create_data_operations()
        metrics_analyzer = self._create_metrics_analyzer()
        return data_ops, metrics_analyzer
    
    def _create_data_operations(self) -> DataOperations:
        """Create data operations module."""
        return DataOperations(
            self.agent.query_builder, self.agent.analysis_engine, 
            self.agent.clickhouse_ops, self.agent.redis_manager
        )
    
    def _create_metrics_analyzer(self) -> MetricsAnalyzer:
        """Create metrics analyzer module."""
        return MetricsAnalyzer(
            self.agent.query_builder, self.agent.analysis_engine, self.agent.clickhouse_ops
        )
    
    def _ensure_data_result(self, result) -> Union[DataAnalysisResponse, AnomalyDetectionResponse]:
        """Ensure result is a proper data analysis result object."""
        if isinstance(result, (DataAnalysisResponse, AnomalyDetectionResponse)):
            return result
        elif isinstance(result, dict):
            return self._convert_dict_to_result(result)
        else:
            # Fix non-JSON responses before processing
            fixed_result = ensure_agent_response_is_json(result)
            return self._convert_dict_to_result(fixed_result)
    
    def _convert_dict_to_result(self, result_dict: dict) -> Union[DataAnalysisResponse, AnomalyDetectionResponse]:
        """Convert dictionary to typed result."""
        try:
            # Apply comprehensive JSON fixes first
            fixed_dict = comprehensive_json_fix(result_dict)
            return DataAnalysisResponse(**fixed_dict)
        except Exception:
            return self._try_anomaly_detection_conversion(result_dict)
    
    def _try_anomaly_detection_conversion(
        self, result_dict: dict
    ) -> Union[AnomalyDetectionResponse, DataAnalysisResponse]:
        """Try converting to AnomalyDetectionResponse, fallback to DataAnalysisResponse."""
        try:
            self._fix_anomaly_format_issues(result_dict)
            return AnomalyDetectionResponse(**result_dict)
        except Exception as e:
            logger.warning(f"Failed to convert dict to typed result: {e}")
            return self._create_fallback_result(str(e))
    
    def _fix_anomaly_format_issues(self, result_dict: dict) -> None:
        """Fix common format issues from LLM responses."""
        if 'anomalies_detected' in result_dict and isinstance(result_dict['anomalies_detected'], list):
            anomaly_list = result_dict['anomalies_detected']
            result_dict['anomalies_detected'] = bool(anomaly_list)
            result_dict['anomaly_details'] = anomaly_list
            result_dict['anomaly_count'] = len(anomaly_list)
    
    def _create_fallback_result(self, error_message: str) -> DataAnalysisResponse:
        """Create fallback DataAnalysisResponse."""
        return DataAnalysisResponse(
            query="unknown",
            error=error_message
        )
    
    def _calculate_execution_time_ms(self, start_time: float) -> float:
        """Calculate execution time in milliseconds."""
        execution_time_seconds = time.time() - start_time
        return execution_time_seconds * 1000.0
    
    def _create_execution_metrics(self, execution_time_ms: float) -> AgentExecutionMetrics:
        """Create execution metrics with timing info."""
        return AgentExecutionMetrics(
            execution_time_ms=execution_time_ms,
            database_queries=1,
            websocket_messages_sent=0,
            errors_encountered=0
        )
    
    def _get_common_result_params(self, execution_time_ms: float, 
                                metrics: AgentExecutionMetrics) -> dict:
        """Get common parameters for TypedAgentResult."""
        return {
            "execution_time_ms": execution_time_ms,
            "metrics": metrics
        }
    
    def _create_success_result(self, start_time: float, data_result) -> TypedAgentResult:
        """Create success result with timing info."""
        execution_time_ms = self._calculate_execution_time_ms(start_time)
        metrics = self._create_execution_metrics(execution_time_ms)
        return self._build_success_result(data_result, execution_time_ms, metrics)
    
    def _build_success_result(self, data_result, execution_time_ms: float, 
                            metrics: AgentExecutionMetrics) -> TypedAgentResult:
        """Build success TypedAgentResult."""
        # Convert complex data to simple format for TypedAgentResult compatibility
        if hasattr(data_result, 'model_dump'):
            data_dict = data_result.model_dump()
            # Convert to JsonCompatibleDict format (only str, int, float, bool, None values)
            result_dict = self._flatten_to_json_compatible(data_dict)
        elif isinstance(data_result, dict):
            result_dict = self._flatten_to_json_compatible(data_result)
        else:
            result_dict = {"message": str(data_result)}
        
        return TypedAgentResult(
            success=True,
            result=result_dict, 
            execution_time_ms=execution_time_ms,
            metadata={"agent_name": "DataSubAgent"}
        )
    
    def _create_failure_result(self, error_message: str, start_time: float) -> TypedAgentResult:
        """Create failure result with timing info."""
        execution_time_ms = self._calculate_execution_time_ms(start_time)
        metrics = self._create_execution_metrics(execution_time_ms)
        return self._build_failure_result(error_message, execution_time_ms, metrics)
    
    def _build_failure_result(self, error_message: str, execution_time_ms: float,
                            metrics: AgentExecutionMetrics) -> TypedAgentResult:
        """Build failure TypedAgentResult."""
        common_params = self._get_common_result_params(execution_time_ms, metrics)
        return TypedAgentResult(
            success=False,
            result=None,
            error=error_message, 
            execution_time_ms=execution_time_ms,
            metadata={"agent_name": "DataSubAgent"}
        )
    
    def _flatten_to_json_compatible(self, data: dict) -> dict:
        """Flatten complex data structures to JSON-compatible format."""
        result = {}
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, list):
                # Convert lists to string summary
                if value:
                    result[f"{key}_count"] = len(value)
                    result[f"{key}_summary"] = f"List of {len(value)} items"
                else:
                    result[f"{key}_count"] = 0
            elif isinstance(value, dict):
                # Convert nested dicts to string representation
                result[f"{key}_keys"] = str(list(value.keys()))
            else:
                # Convert other types to string
                result[key] = str(value)
        return result