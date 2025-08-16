"""Analysis routing and execution for DataSubAgent."""

from typing import Dict, Any, Tuple, List, Callable
from datetime import datetime


class AnalysisRouter:
    """Routes and executes different types of analysis."""
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
    
    async def perform_complete_analysis(
        self,
        params: Dict[str, Any],
        run_id: str,
        stream_updates: bool,
        send_update_fn: Callable,
        data_ops: Any
    ) -> Dict[str, Any]:
        """Perform complete analysis based on parameters."""
        time_range = self.engine.parameter_processor.parse_time_range(params["time_range_str"])
        base_result = self.engine.parameter_processor.create_base_result(params, time_range)
        
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
        """Analyze performance optimization intent."""
        await self.engine.core.send_progress_update(run_id, stream_updates, send_update_fn, "Analyzing performance metrics...")
        
        await self._perform_performance_analysis(result, params, time_range, data_ops)
        await self._check_metric_anomalies(result, params, time_range, data_ops, params["metric_names"])
        return result
    
    async def _perform_performance_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform detailed performance analysis."""
        perf_analysis = await data_ops.analyze_performance_metrics(
            params["user_id"], params["workload_id"], time_range
        )
        result["results"]["performance"] = perf_analysis
    
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
        """Analyze correlation analysis intent."""
        await self.engine.core.send_progress_update(run_id, stream_updates, send_update_fn, "Analyzing correlations...")
        
        await self._perform_correlation_analysis(result, params, time_range, data_ops)
        return result
    
    async def _perform_correlation_analysis(
        self, result: Dict[str, Any], params: Dict[str, Any], time_range: Tuple[datetime, datetime], data_ops: Any
    ) -> None:
        """Perform correlation analysis between metrics."""
        correlations = await data_ops.analyze_correlations(
            params["user_id"], params["metric_names"], time_range
        )
        result["results"]["correlations"] = correlations
    
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
        """Analyze monitoring intent."""
        await self.engine.core.send_progress_update(run_id, stream_updates, send_update_fn, "Monitoring for anomalies...")
        
        for metric in params["metric_names"]:
            await self._analyze_metric_monitoring(result, params, time_range, data_ops, metric)
        return result
    
    async def _analyze_metric_monitoring(
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
        await self.engine.core.send_progress_update(run_id, stream_updates, send_update_fn, "Performing comprehensive analysis...")
        
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