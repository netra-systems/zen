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
        self._assign_core_dependencies(clickhouse_ops, query_builder, analysis_engine, redis_manager, llm_manager)
        self._init_fallback_handler()
    
    def _assign_core_dependencies(
        self, clickhouse_ops: Any, query_builder: Any, analysis_engine: Any, 
        redis_manager: Any, llm_manager: LLMManager
    ) -> None:
        """Assign core dependencies to instance variables."""
        self.clickhouse_ops = clickhouse_ops
        self.query_builder = query_builder
        self.analysis_engine = analysis_engine
        self.redis_manager = redis_manager
        self.llm_manager = llm_manager
    
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
            await self._execute_analysis_workflow(state, run_id, stream_updates, send_update_fn, data_ops)
        except Exception as e:
            logger.error(f"DataSubAgent execution failed: {e}")
            await self._handle_execution_error(state, run_id, stream_updates, send_update_fn, e)
    
    async def _execute_analysis_workflow(
        self, state: "DeepAgentState", run_id: str, stream_updates: bool, send_update_fn: Callable, data_ops: Any
    ) -> None:
        """Execute the complete analysis workflow."""
        await self._send_initial_update(run_id, stream_updates, send_update_fn)
        params = self._extract_analysis_params(state)
        result = await self._perform_complete_analysis(params, run_id, stream_updates, send_update_fn, data_ops)
        self._store_result_in_state(state, result)
        await self._send_completion_update(run_id, stream_updates, send_update_fn, result)
        logger.info(f"DataSubAgent completed analysis for run_id: {run_id}")
    
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
        triage_result = state.triage_result
        if not triage_result:
            return self._build_analysis_params_dict({}, {})
        
        # Access TriageResult object attributes properly
        key_params = getattr(triage_result, 'key_parameters', {})
        intent = getattr(triage_result, 'intent', {})
        
        return self._build_analysis_params_dict(key_params, intent)
    
    def _build_analysis_params_dict(self, key_params: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build analysis parameters dictionary."""
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
        time_deltas = self._get_time_delta_mapping()
        start_time = end_time - time_deltas.get(time_range_str, timedelta(days=1))
        return (start_time, end_time)
    
    def _get_time_delta_mapping(self) -> Dict[str, timedelta]:
        """Get mapping of time range strings to timedelta objects."""
        return {
            "last_hour": timedelta(hours=1),
            "last_24_hours": timedelta(days=1),
            "last_week": timedelta(weeks=1),
            "last_month": timedelta(days=30)
        }
    
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
        
        return await self._route_analysis_by_intent(
            base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops
        )
    
    async def _route_analysis_by_intent(
        self, base_result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime],
        run_id: str, stream_updates: bool, send_update_fn: Callable, data_ops: Any
    ) -> Dict[str, Any]:
        """Route analysis based on primary intent."""
        intent = params["primary_intent"]
        
        if intent in ["optimize", "performance"]:
            return await self._analyze_performance_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        elif intent == "analyze":
            return await self._analyze_correlation_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        elif intent == "monitor":
            return await self._analyze_monitoring_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
        else:
            return await self._analyze_comprehensive_intent(base_result, params, time_range, run_id, stream_updates, send_update_fn, data_ops)
    
    def _create_base_result(self, params: Dict[str, Any], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            "analysis_type": params["primary_intent"],
            "parameters": self._create_parameters_section(params, time_range),
            "results": {}
        }
    
    def _create_parameters_section(self, params: Dict[str, Any], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create parameters section of result."""
        return {
            "user_id": params["user_id"],
            "workload_id": params["workload_id"],
            "time_range": self._format_time_range(time_range),
            "metrics": params["metric_names"]
        }
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range as ISO strings."""
        return {
            "start": time_range[0].isoformat(),
            "end": time_range[1].isoformat()
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
        
        await self._perform_performance_analysis(result, params, time_range, data_ops)
        await self._check_performance_anomalies(result, params, time_range, data_ops)
        return result
    
    async def _perform_performance_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform core performance metrics analysis."""
        perf_analysis = await data_ops.analyze_performance_metrics(
            params["user_id"], params["workload_id"], time_range
        )
        result["results"]["performance"] = perf_analysis
    
    async def _check_performance_anomalies(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Check for performance-related anomalies."""
        await self._check_metric_anomalies(result, params, time_range, data_ops, ["latency_ms", "error_rate"])
    
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
        
        await self._perform_correlation_analysis(result, params, time_range, data_ops)
        await self._analyze_usage_patterns(result, params, data_ops)
        return result
    
    async def _perform_correlation_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform correlation analysis between metrics."""
        correlations = await data_ops.analyze_correlations(
            params["user_id"], params["metric_names"], time_range
        )
        result["results"]["correlations"] = correlations
    
    async def _analyze_usage_patterns(
        self, result: Dict[str, Any], params: Dict[str, Any], data_ops: Any
    ) -> None:
        """Analyze usage patterns for the user."""
        usage_patterns = await data_ops.analyze_usage_patterns(params["user_id"])
        result["results"]["usage_patterns"] = usage_patterns
    
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
        
        await self._perform_monitoring_analysis(result, params, time_range, data_ops)
        return result
    
    async def _perform_monitoring_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform monitoring analysis for all metrics."""
        for metric in params["metric_names"]:
            await self._analyze_single_metric_anomalies(result, params, time_range, data_ops, metric)
    
    async def _analyze_single_metric_anomalies(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], 
        data_ops: Any, metric: str
    ) -> None:
        """Analyze anomalies for a single metric."""
        anomalies = await data_ops.detect_anomalies(
            params["user_id"], metric, time_range, z_score_threshold=2.5
        )
        result["results"][f"{metric}_monitoring"] = anomalies
    
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
        
        await self._perform_comprehensive_performance_analysis(result, params, time_range, data_ops)
        await self._perform_comprehensive_usage_analysis(result, params, data_ops)
        return result
    
    async def _perform_comprehensive_performance_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform comprehensive performance analysis."""
        perf_analysis = await data_ops.analyze_performance_metrics(
            params["user_id"], params["workload_id"], time_range
        )
        result["results"]["performance"] = perf_analysis
    
    async def _perform_comprehensive_usage_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], data_ops: Any
    ) -> None:
        """Perform comprehensive usage pattern analysis."""
        usage_patterns = await data_ops.analyze_usage_patterns(params["user_id"], 7)
        result["results"]["usage_patterns"] = usage_patterns
    
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
            await self._check_single_metric_anomalies(result, params, time_range, data_ops, metric)
    
    async def _check_single_metric_anomalies(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], 
        data_ops: Any, metric: str
    ) -> None:
        """Check anomalies for a single metric and store if found."""
        anomalies = await data_ops.detect_anomalies(params["user_id"], metric, time_range)
        
        if self._has_anomalies(anomalies):
            result["results"][f"{metric}_anomalies"] = anomalies
    
    def _has_anomalies(self, anomalies: Dict[str, Any]) -> bool:
        """Check if anomalies were detected."""
        return anomalies.get("anomaly_count", 0) > 0
    
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
        self._store_fallback_result(state, fallback_result)
        
        if stream_updates:
            await self._send_fallback_completion(run_id, send_update_fn, fallback_result)
    
    def _store_fallback_result(self, state: 'DeepAgentState', fallback_result: Dict[str, Any]) -> None:
        """Store fallback result in agent state."""
        state.data_result = fallback_result
    
    async def _execute_llm_fallback(
        self,
        state: 'DeepAgentState',
        run_id: str,
        error: Exception
    ) -> Dict[str, Any]:
        """Execute LLM-based fallback analysis."""
        prompt = self._build_fallback_prompt(state, run_id)
        llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='data')
        data_result = extract_json_from_response(llm_response_str)
        
        return data_result or self._create_basic_fallback_result(error)
    
    def _build_fallback_prompt(self, state: 'DeepAgentState', run_id: str) -> str:
        """Build fallback analysis prompt."""
        return data_prompt_template.format(
            triage_result=state.triage_result,
            user_request=state.user_request,
            thread_id=run_id
        )
    
    def _create_basic_fallback_result(self, error: Exception) -> Dict[str, Any]:
        """Create basic fallback result when LLM extraction fails."""
        return {
            "collection_status": "fallback",
            "data": "Limited data available due to connection issues",
            "error": str(error)
        }
    
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
        
        try:
            return await self._try_llm_fallback_with_protection(state, run_id, error)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed for {run_id}: {fallback_error}")
            return self._create_emergency_data_fallback(state, fallback_error)
    
    async def _try_llm_fallback_with_protection(
        self, state: 'DeepAgentState', run_id: str, error: Exception
    ) -> Dict[str, Any]:
        """Try LLM fallback with handler protection."""
        async def _llm_fallback_operation():
            return await self._execute_llm_fallback(state, run_id, error)
        
        result = await self.fallback_handler.execute_with_fallback(
            _llm_fallback_operation, "data_analysis_fallback", "data_analysis", "data_analysis"
        )
        
        return self._process_fallback_result(result, state, error)
    
    def _process_fallback_result(
        self, result: Any, state: 'DeepAgentState', error: Exception
    ) -> Dict[str, Any]:
        """Process fallback result based on type."""
        if isinstance(result, dict):
            return self._enrich_fallback_result(result, error)
        else:
            return self._create_emergency_data_fallback(state, error)
    
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
        triage_result = state.triage_result
        category = getattr(triage_result, 'category', 'Unknown') if triage_result else 'Unknown'
        
        return {
            "analysis_type": "emergency_fallback",
            "category": category,
            "insights": self._create_emergency_insights(category),
            "recommendations": self._create_emergency_recommendations(),
            "data": self._create_emergency_data_section(error),
            "metadata": self._create_emergency_metadata()
        }
    
    def _create_emergency_insights(self, category: str) -> List[str]:
        """Create emergency fallback insights."""
        return [
            f"Analysis for {category} request is temporarily unavailable",
            "System is experiencing technical difficulties",
            "Please try again in a few minutes"
        ]
    
    def _create_emergency_recommendations(self) -> List[str]:
        """Create emergency fallback recommendations."""
        return [
            "Check system status",
            "Retry with simpler parameters",
            "Contact support if issue persists"
        ]
    
    def _create_emergency_data_section(self, error: Exception) -> Dict[str, Any]:
        """Create emergency data section."""
        return {
            "status": "emergency_fallback",
            "error": str(error),
            "available": False
        }
    
    def _create_emergency_metadata(self) -> Dict[str, Any]:
        """Create emergency metadata section."""
        return {
            "fallback_used": True,
            "fallback_type": "emergency",
            "data_quality": "unavailable",
            "confidence": 0.0
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