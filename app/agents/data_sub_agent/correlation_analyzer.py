"""Modern Correlation Analysis Module with BaseExecutionInterface

Business Value: Provides reliable correlation analysis for mid-tier and enterprise customers.
Enables data-driven insights that justify AI spend optimization decisions.

Complies with 300-line module and 8-line function limits.
"""

import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus
)
from app.agents.base.reliability_manager import ReliabilityManager
from app.schemas.shared_types import RetryConfig
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.core.exceptions_base import NetraException, ValidationError
from app.core.system_health_monitor import system_health_monitor


class CorrelationAnalyzer(BaseExecutionInterface):
    """Modern correlation analysis with reliability patterns."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any,
                 websocket_manager=None) -> None:
        super().__init__("CorrelationAnalyzer", websocket_manager)
        self._initialize_core_components(query_builder, clickhouse_ops, redis_manager)
        self._initialize_reliability_manager()
        self._register_health_monitoring()
    
    def _initialize_core_components(self, query_builder: Any, clickhouse_ops: Any, 
                                   redis_manager: Any) -> None:
        """Initialize core analysis components."""
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    def _initialize_reliability_manager(self) -> None:
        """Initialize reliability patterns."""
        circuit_config = CircuitBreakerConfig("correlation_analyzer", 5, 60)
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
    
    def _register_health_monitoring(self) -> None:
        """Register with system health monitor."""
        system_health_monitor.register_component_checker(
            "correlation_analyzer", self._health_check
        )
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute correlation analysis with modern patterns."""
        params = context.state.get_current_parameters()
        user_id = params.get("user_id")
        metrics = params.get("metrics", [])
        time_range = params.get("time_range")
        
        correlations = await self._calculate_pairwise_correlations(user_id, metrics, time_range)
        return self._build_correlation_response(time_range, metrics, correlations)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate correlation analysis preconditions."""
        params = context.state.get_current_parameters()
        return self._validate_correlation_params(params)
    
    async def analyze_correlations_with_reliability(self, user_id: int, metrics: List[str],
                                                   time_range: Tuple[datetime, datetime]
                                                   ) -> ExecutionResult:
        """Public interface for correlation analysis with reliability."""
        context = self._create_analysis_context(user_id, metrics, time_range)
        return await self.reliability_manager.execute_with_reliability(
            context, lambda: self._execute_analysis_logic(context)
        )
    
    def _validate_correlation_params(self, params: Dict[str, Any]) -> bool:
        """Validate correlation analysis parameters."""
        metrics = params.get("metrics", [])
        user_id = params.get("user_id")
        time_range = params.get("time_range")
        return len(metrics) >= 2 and user_id is not None and time_range is not None
    
    def _create_analysis_context(self, user_id: int, metrics: List[str],
                                time_range: Tuple[datetime, datetime]) -> ExecutionContext:
        """Create execution context for analysis."""
        from app.agents.state import DeepAgentState
        state = DeepAgentState()
        state.set_parameters({
            "user_id": user_id, "metrics": metrics, "time_range": time_range
        })
        return ExecutionContext(
            run_id=f"corr_analysis_{int(time.time())}", agent_name=self.agent_name,
            state=state, start_time=datetime.utcnow()
        )
    
    async def _execute_analysis_logic(self, context: ExecutionContext) -> ExecutionResult:
        """Execute analysis logic with proper result handling."""
        start_time = time.time()
        try:
            result = await self.execute_core_logic(context)
            execution_time = (time.time() - start_time) * 1000
            return self._create_success_result(result, execution_time)
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return self._create_error_result(str(e), execution_time)
    
    async def _calculate_pairwise_correlations(self, user_id: int, metrics: List[str], 
                                             time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Calculate pairwise correlations between metrics."""
        start_time, end_time = time_range
        correlations = {}
        await self._process_metric_pairs(user_id, metrics, start_time, end_time, correlations)
        return correlations
    
    async def _process_metric_pairs(self, user_id: int, metrics: List[str], 
                                  start_time: datetime, end_time: datetime, correlations: Dict) -> None:
        """Process all metric pairs for correlation analysis."""
        for i in range(len(metrics)):
            await self._process_metric_pair_combinations(user_id, metrics, i, start_time, end_time, correlations)
    
    async def _process_metric_pair_combinations(self, user_id: int, metrics: List[str], i: int,
                                              start_time: datetime, end_time: datetime, correlations: Dict) -> None:
        """Process metric pair combinations for given index."""
        for j in range(i + 1, len(metrics)):
            correlation = await self._calculate_single_correlation(user_id, metrics[i], metrics[j], start_time, end_time)
            if correlation:
                pair_key = self._create_pair_key(metrics[i], metrics[j])
                correlations[pair_key] = correlation
    
    def _create_pair_key(self, metric1: str, metric2: str) -> str:
        """Create key for metric pair."""
        return f"{metric1}_vs_{metric2}"
    
    async def _calculate_single_correlation(self, user_id: int, metric1: str, metric2: str, 
                                          start_time: datetime, end_time: datetime) -> Optional[Dict]:
        """Calculate correlation between two metrics with error handling."""
        try:
            query = self._build_correlation_query(user_id, metric1, metric2, start_time, end_time)
            data = await self.clickhouse_ops.fetch_data(query, redis_manager=self.redis_manager)
            
            if self._has_sufficient_data(data):
                return self._format_correlation_data(data[0])
            return None
        except Exception as e:
            logger.error(f"Error calculating correlation for {metric1} vs {metric2}: {e}")
            raise NetraException(f"Correlation calculation failed: {e}")
    
    def _build_correlation_query(self, user_id: int, metric1: str, metric2: str, 
                               start_time: datetime, end_time: datetime) -> str:
        """Build correlation analysis query."""
        return self.query_builder.build_correlation_analysis_query(
            user_id, metric1, metric2, start_time, end_time
        )
    
    def _has_sufficient_data(self, data: Optional[List[Dict]]) -> bool:
        """Check if correlation data has sufficient sample size."""
        return data and len(data) > 0 and data[0].get('sample_size', 0) > 10
    
    def _format_correlation_data(self, corr_data: Dict) -> Dict[str, Any]:
        """Format correlation data for response."""
        corr_coef = corr_data.get('correlation_coefficient', 0.0)
        strength = self._interpret_correlation_strength(corr_coef)
        basic_info = self._create_correlation_basic_info(corr_coef, strength, corr_data)
        stats_info = self._create_correlation_stats_info(corr_data)
        return {**basic_info, **stats_info}
    
    def _create_correlation_basic_info(self, corr_coef: float, strength: str, corr_data: Dict) -> Dict[str, Any]:
        """Create basic correlation information."""
        return {
            "coefficient": corr_coef,
            "strength": strength,
            "direction": self._determine_direction(corr_coef),
            "sample_size": corr_data.get('sample_size', 0)
        }
    
    def _determine_direction(self, corr_coef: float) -> str:
        """Determine correlation direction."""
        return "positive" if corr_coef > 0 else "negative"
    
    def _create_correlation_stats_info(self, corr_data: Dict) -> Dict[str, Any]:
        """Create correlation statistics information."""
        return {
            "metric1_stats": self._create_metric_stats(corr_data, 'metric1'),
            "metric2_stats": self._create_metric_stats(corr_data, 'metric2')
        }
    
    def _create_metric_stats(self, corr_data: Dict, metric_prefix: str) -> Dict[str, float]:
        """Create statistics for a single metric."""
        return {
            "mean": corr_data.get(f'{metric_prefix}_avg', 0.0),
            "std": corr_data.get(f'{metric_prefix}_std', 0.0)
        }
    
    def _interpret_correlation_strength(self, corr_coef: float) -> str:
        """Interpret correlation coefficient strength."""
        abs_coef = abs(corr_coef)
        if abs_coef > 0.7:
            return "strong"
        elif abs_coef > 0.4:
            return "moderate"
        return "weak"
    
    def _build_correlation_response(self, time_range: Tuple[datetime, datetime], metrics: List[str], 
                                   correlations: Dict) -> Dict[str, Any]:
        """Build correlation analysis response."""
        start_time, end_time = time_range
        return {
            "time_range": self._create_time_range_info(start_time, end_time),
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": self._find_strongest_correlation(correlations)
        }
    
    def _create_time_range_info(self, start_time: datetime, end_time: datetime) -> Dict[str, str]:
        """Create time range information."""
        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
    
    def _find_strongest_correlation(self, correlations: Dict) -> Optional[Tuple]:
        """Find the strongest correlation in the data."""
        if not correlations:
            return None
        return max(correlations.items(), key=lambda x: abs(x[1].get('coefficient', 0)))
    
    async def _health_check(self) -> Dict[str, Any]:
        """Health check for correlation analyzer."""
        try:
            health_score = self._calculate_health_score()
            return self._create_health_check_response(health_score)
        except Exception as e:
            logger.error(f"Health check failed for correlation analyzer: {e}")
            return {"healthy": False, "health_score": 0.0, "error": str(e)}
    
    def _calculate_health_score(self) -> float:
        """Calculate health score based on reliability stats."""
        health_status = self.reliability_manager.get_health_status()
        return health_status.get("success_rate", 0.0)
    
    def _create_health_check_response(self, health_score: float) -> Dict[str, Any]:
        """Create health check response."""
        return {
            "healthy": health_score > 0.8,
            "health_score": health_score,
            "component": "correlation_analyzer",
            "reliability_stats": self.reliability_manager.get_health_status()
        }
    
    async def analyze_correlations(self, user_id: int, metrics: List[str],
                                 time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Legacy interface for backward compatibility."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        
        result = await self.analyze_correlations_with_reliability(user_id, metrics, time_range)
        if result.success:
            return result.result
        else:
            return {"error": result.error}


