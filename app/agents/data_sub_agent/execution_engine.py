"""Execution engine that breaks down the massive execute() function into ≤8 line functions."""

from typing import Dict, Optional, Any, Tuple, List, Callable, TYPE_CHECKING
from datetime import datetime, timedelta, UTC

from app.llm.llm_manager import LLMManager
from app.agents.prompts import data_prompt_template

from app.schemas.registry import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger as logger
from app.llm.fallback_handler import LLMFallbackHandler, FallbackConfig


class ExecutionEngine:
    """Engine that executes data analysis workflow in ≤8 line functions."""
    
    def __init__(
        self,
        clickhouse_ops: Any,
        query_builder: Any,
        analysis_engine: Any,
        redis_manager: Any,
        llm_manager: LLMManager
    ) -> None:
        self.clickhouse_ops = clickhouse_ops
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.redis_manager = redis_manager
        self.llm_manager = llm_manager
        self._init_fallback_handler()
    
    async def execute_analysis(
        self,
        state: "DeepAgentState",
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any,
        metrics_analyzer: Any
    ) -> None:
        """Main execution method coordinating analysis workflow."""
        try:
            await self._send_initial_update(run_id, stream_updates, send_update_fn)
            params = self._extract_analysis_params(state)
            result = await self._perform_complete_analysis(params, run_id, stream_updates, send_update_fn, data_ops)
            self._store_result_in_state(state, result)
            await self._send_completion_update(run_id, stream_updates, send_update_fn, result)
            logger.info(f"DataSubAgent completed analysis for run_id: {run_id}")
        except Exception as e:
            logger.error(f"DataSubAgent execution failed: {e}")
            await self._handle_execution_error(state, run_id, stream_updates, send_update_fn, e)
    
    async def _send_initial_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable
    ) -> None:
        """Send initial status update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "started",
                "message": "Starting advanced data analysis..."
            })
    
    def _extract_analysis_params(self, state: "DeepAgentState") -> Dict[str, Any]:
        """Extract analysis parameters from triage result."""
        triage_result = state.triage_result or {}
        key_params = triage_result.get("key_parameters", {})
        intent = triage_result.get("intent", {})
        
        return {
            "user_id": key_params.get("user_id", 1),
            "workload_id": key_params.get("workload_id"),
            "metric_names": key_params.get("metrics", ["latency_ms", "throughput", "cost_cents"]),
            "time_range_str": key_params.get("time_range", "last_24_hours"),
            "primary_intent": intent.get("primary", "general")
        }
    
    def _parse_time_range(self, time_range_str: str) -> Tuple[datetime, datetime]:
        """Parse time range string into datetime tuple."""
        end_time = datetime.now(UTC)
        time_deltas = {
            "last_hour": timedelta(hours=1),
            "last_24_hours": timedelta(days=1),
            "last_week": timedelta(weeks=1),
            "last_month": timedelta(days=30)
        }
        start_time = end_time - time_deltas.get(time_range_str, timedelta(days=1))
        return (start_time, end_time)
    
    async def _perform_complete_analysis(
        self,
        params: Dict[str, Any],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Perform complete analysis based on parameters."""
        time_range = self._parse_time_range(params["time_range_str"])
        base_result = self._create_base_result(params, time_range)
        
        if params["primary_intent"] in ["optimize", "performance"]:
            return await self._analyze_performance_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        elif params["primary_intent"] == "analyze":
            return await self._analyze_correlation_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        elif params["primary_intent"] == "monitor":
            return await self._analyze_monitoring_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        else:
            return await self._analyze_comprehensive_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
    
    def _create_base_result(self, params: Dict[str, Any], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            "analysis_type": params["primary_intent"],
            "parameters": {
                "user_id": params["user_id"],
                "workload_id": params["workload_id"],
                "time_range": {
                    "start": time_range[0].isoformat(),
                    "end": time_range[1].isoformat()
                },
                "metrics": params["metric_names"]
            },
            "results": {}
        }
    
    async def _analyze_performance_intent(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Analyze performance-focused intent."""
        await self._send_progress_update(run_id, stream_updates, send_update_fn, "Analyzing performance metrics...")
        
        perf_analysis = await data_ops.analyze_performance_metrics(
            params["user_id"], params["workload_id"], time_range
        )
        result["results"]["performance"] = perf_analysis
        
        await self._check_metric_anomalies(result, params, time_range, data_ops, ["latency_ms", "error_rate"])
        return result
    
    async def _analyze_correlation_intent(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Analyze correlation-focused intent."""
        await self._send_progress_update(run_id, stream_updates, send_update_fn, "Performing correlation analysis...")
        
        correlations = await data_ops.analyze_correlations(
            params["user_id"], params["metric_names"], time_range
        )
        result["results"]["correlations"] = correlations
        
        usage_patterns = await data_ops.analyze_usage_patterns(params["user_id"])
        result["results"]["usage_patterns"] = usage_patterns
        return result
    
    async def _analyze_monitoring_intent(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Analyze monitoring-focused intent."""
        await self._send_progress_update(run_id, stream_updates, send_update_fn, "Checking for anomalies...")
        
        for metric in params["metric_names"]:
            anomalies = await data_ops.detect_anomalies(
                params["user_id"], metric, time_range, z_score_threshold=2.5
            )
            result["results"][f"{metric}_monitoring"] = anomalies
        return result
    
    async def _analyze_comprehensive_intent(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Analyze comprehensive intent (default case)."""
        await self._send_progress_update(run_id, stream_updates, send_update_fn, "Performing comprehensive analysis...")
        
        perf_analysis = await data_ops.analyze_performance_metrics(
            params["user_id"], params["workload_id"], time_range
        )
        result["results"]["performance"] = perf_analysis
        
        usage_patterns = await data_ops.analyze_usage_patterns(params["user_id"], 7)
        result["results"]["usage_patterns"] = usage_patterns
        return result
    
    async def _check_metric_anomalies(
        self,
        result: Dict[str, Any],
        params: Dict[str, Any],
        time_range: Tuple[datetime, datetime],
        data_ops: Any,
        metrics: List[str]
    ) -> None:
        """Check for anomalies in specified metrics."""
        for metric in metrics:
            anomalies = await data_ops.detect_anomalies(
                params["user_id"], metric, time_range
            )
            if anomalies.get("anomaly_count", 0) > 0:
                result["results"][f"{metric}_anomalies"] = anomalies
    
    async def _send_progress_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        message: str
    ) -> None:
        """Send progress update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "analyzing",
                "message": message
            })
    
    def _store_result_in_state(self, state: 'DeepAgentState', result: Dict[str, Any]) -> None:
        """Store analysis result in agent state."""
        state.data_result = result
    
    async def _send_completion_update(
        self,
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        result: Dict[str, Any]
    ) -> None:
        """Send completion update."""
        if stream_updates:
            await send_update_fn(run_id, {
                "status": "completed",
                "message": "Advanced data analysis completed successfully",
                "result": result
            })
    
    async def _handle_execution_error(
        self,
        state: 'DeepAgentState',
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        error: Exception
    ) -> None:
        """Handle execution error with comprehensive fallback."""
        fallback_result = await self._execute_comprehensive_fallback(state, run_id, error)
        state.data_result = fallback_result
        
        if stream_updates:
            await self._send_fallback_completion(run_id, send_update_fn, fallback_result)
    
    async def _execute_llm_fallback(
        self,
        state: 'DeepAgentState',
        run_id: str,
        error: Exception
    ) -> Dict[str, Any]:
        """Execute LLM-based fallback analysis."""
        prompt = data_prompt_template.format(
            triage_result=state.triage_result,
            user_request=state.user_request,
            thread_id=run_id
        )
        
        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
        data_result = extract_json_from_response(llm_response_str)
        
        if not data_result:
            data_result = {
                "collection_status": "fallback",
                "data": "Limited data available due to connection issues",
                "error": str(error)
            }
        
        return data_result
    
    def _init_fallback_handler(self) -> None:
        """Initialize fallback handler for data operations."""
        fallback_config = FallbackConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=15.0,
            timeout=45.0,
            use_circuit_breaker=True
        )
        self.fallback_handler = LLMFallbackHandler(fallback_config)
    
    async def _execute_comprehensive_fallback(
        self,
        state: 'DeepAgentState',
        run_id: str,
        error: Exception
    ) -> Dict[str, Any]:
        """Execute comprehensive fallback strategy."""
        logger.warning(f"Executing fallback for data analysis {run_id}: {error}")
        
        async def _llm_fallback_operation():
            return await self._execute_llm_fallback(state, run_id, error)
        
        try:
            # Try LLM fallback with handler protection
            result = await self.fallback_handler.execute_with_fallback(
                _llm_fallback_operation,
                "data_analysis_fallback",
                "data_analysis",
                "data_analysis"
            )
            
            if isinstance(result, dict):
                return self._enrich_fallback_result(result, error)
            else:
                return self._create_emergency_data_fallback(state, error)
                
        except Exception as fallback_error:
            logger.error(f"Fallback also failed for {run_id}: {fallback_error}")
            return self._create_emergency_data_fallback(state, fallback_error)
    
    def _enrich_fallback_result(self, result: Dict[str, Any], original_error: Exception) -> Dict[str, Any]:
        """Enrich fallback result with metadata and context."""
        if "metadata" not in result:
            result["metadata"] = {}
        
        result["metadata"].update({
            "fallback_used": True,
            "original_error": str(original_error),
            "fallback_type": "llm_analysis",
            "data_quality": "degraded"
        })
        
        return result
    
    def _create_emergency_data_fallback(self, state: 'DeepAgentState', error: Exception) -> Dict[str, Any]:
        """Create emergency fallback when all analysis methods fail."""
        triage_result = state.triage_result or {}
        category = triage_result.get("category", "Unknown")
        
        return {
            "analysis_type": "emergency_fallback",
            "category": category,
            "insights": [
                f"Analysis for {category} request is temporarily unavailable",
                "System is experiencing technical difficulties",
                "Please try again in a few minutes"
            ],
            "recommendations": [
                "Check system status",
                "Retry with simpler parameters",
                "Contact support if issue persists"
            ],
            "data": {
                "status": "emergency_fallback",
                "error": str(error),
                "available": False
            },
            "metadata": {
                "fallback_used": True,
                "fallback_type": "emergency",
                "data_quality": "unavailable",
                "confidence": 0.0
            }
        }
    
    async def _send_fallback_completion(
        self,
        run_id: str,
        send_update_fn: Callable,
        result: Dict[str, Any]
    ) -> None:
        """Send completion update for fallback results."""
        fallback_type = result.get("metadata", {}).get("fallback_type", "unknown")
        
        if fallback_type == "emergency":
            status = "completed_with_emergency_fallback"
            message = "Analysis completed using emergency fallback"
        else:
            status = "completed_with_fallback"
            message = "Data analysis completed with limited capabilities"
        
        await send_update_fn(run_id, {
            "status": status,
            "message": message,
            "result": result
        })
    
    def get_fallback_health_status(self) -> Dict[str, Any]:
        """Get health status of fallback mechanisms."""
        return self.fallback_handler.get_health_status()