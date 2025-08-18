"""Execution management for DataSubAgent."""

from typing import Union
import time

from app.schemas.strict_types import TypedAgentResult, AgentExecutionMetrics
from app.agents.state import DeepAgentState
from app.logging_config import central_logger as logger
from app.schemas.shared_types import DataAnalysisResponse, AnomalyDetectionResponse
from app.core.json_parsing_utils import ensure_agent_response_is_json, comprehensive_json_fix

from .execution_engine import ExecutionEngine
from .data_operations import DataOperations
from .metrics_analyzer import MetricsAnalyzer


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
                # Try both send_message and send_to_thread methods as per test expectations
                if hasattr(self.agent.websocket_manager, 'send_message'):
                    await self.agent.websocket_manager.send_message(run_id, completion_message)
                elif hasattr(self.agent.websocket_manager, 'send_to_thread'):
                    await self.agent.websocket_manager.send_to_thread(run_id, completion_message)
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
        common_params = self._get_common_result_params(execution_time_ms, metrics)
        return TypedAgentResult(
            agent_name="DataSubAgent", success=True,
            result_data=data_result, **common_params
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
            agent_name="DataSubAgent", success=False,
            error_message=error_message, **common_params
        )