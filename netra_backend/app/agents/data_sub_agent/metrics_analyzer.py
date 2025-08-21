"""Modernized Metrics Analysis Orchestrator with BaseExecutionInterface

Metrics analysis orchestrator with modular specialized analyzers.
Now modernized with BaseExecutionInterface for standardized execution patterns.

Business Value: Analytics critical for customer optimization insights.
BVJ: Growth & Enterprise | Performance Analytics | +15% optimization value capture
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor

from netra_backend.app.metric_distribution_analyzer import MetricDistributionAnalyzer
from netra_backend.app.metric_trend_analyzer import MetricTrendAnalyzer
from netra_backend.app.metric_percentile_analyzer import MetricPercentileAnalyzer
from netra_backend.app.metric_comparison_analyzer import MetricComparisonAnalyzer
from netra_backend.app.metric_seasonality_analyzer import MetricSeasonalityAnalyzer


class MetricsAnalyzer(BaseExecutionInterface):
    """Modernized orchestrator for specialized metric analysis operations.
    
    Now supports BaseExecutionInterface for standardized execution patterns
    with reliability management and performance monitoring.
    """
    
    def __init__(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None) -> None:
        self._init_base_interface(websocket_manager)
        self._init_all_components(query_builder, analysis_engine, clickhouse_ops, reliability_manager)
        
    def _init_base_interface(self, websocket_manager: Optional[WebSocketManagerProtocol]) -> None:
        """Initialize base execution interface."""
        BaseExecutionInterface.__init__(self, "MetricsAnalyzer", websocket_manager)
        
    def _init_all_components(self, query_builder: Any, analysis_engine: Any, 
                           clickhouse_ops: Any, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize analyzers and modern components."""
        self._initialize_specialized_analyzers(query_builder, analysis_engine, clickhouse_ops)
        self._initialize_modern_components(reliability_manager)
    
    def _initialize_specialized_analyzers(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any) -> None:
        """Initialize specialized analyzer modules."""
        self._create_primary_analyzers(query_builder, analysis_engine, clickhouse_ops)
        self._create_secondary_analyzers(query_builder, clickhouse_ops)
        
    def _create_primary_analyzers(self, query_builder: Any, analysis_engine: Any, clickhouse_ops: Any) -> None:
        """Create primary analyzers with full engine support."""
        self.distribution_analyzer = MetricDistributionAnalyzer(query_builder, analysis_engine, clickhouse_ops)
        self.trend_analyzer = MetricTrendAnalyzer(query_builder, analysis_engine, clickhouse_ops)
        self.seasonality_analyzer = MetricSeasonalityAnalyzer(query_builder, analysis_engine, clickhouse_ops)
        
    def _create_secondary_analyzers(self, query_builder: Any, clickhouse_ops: Any) -> None:
        """Create secondary analyzers with basic operations."""
        self.percentile_analyzer = MetricPercentileAnalyzer(query_builder, clickhouse_ops)
        self.comparison_analyzer = MetricComparisonAnalyzer(query_builder, clickhouse_ops)
        
    def _initialize_modern_components(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize modern execution components."""
        self._setup_reliability_manager(reliability_manager)
        self._setup_execution_monitoring()
        self._setup_execution_engine()
        
    def _setup_reliability_manager(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Setup reliability manager for fault tolerance."""
        if not reliability_manager:
            reliability_manager = self._create_default_reliability_manager()
        self.reliability_manager = reliability_manager
        
    def _setup_execution_monitoring(self) -> None:
        """Setup execution monitoring for performance tracking."""
        self.execution_monitor = ExecutionMonitor(max_history_size=1000)
        
    def _setup_execution_engine(self) -> None:
        """Setup execution engine for orchestration."""
        self.execution_engine = BaseExecutionEngine(
            self.reliability_manager, self.execution_monitor
        )
        
    def _create_default_reliability_manager(self) -> ReliabilityManager:
        """Create default reliability manager configuration."""
        from app.agents.base.circuit_breaker import CircuitBreakerConfig
        from app.schemas.shared_types import RetryConfig
        
        circuit_config = self._create_circuit_config()
        retry_config = self._create_retry_config()
        return ReliabilityManager(circuit_config, retry_config)
        
    def _create_circuit_config(self) -> 'CircuitBreakerConfig':
        """Create circuit breaker configuration."""
        from app.agents.base.circuit_breaker import CircuitBreakerConfig
        return CircuitBreakerConfig(
            name="MetricsAnalyzer",
            failure_threshold=5,
            recovery_timeout=30.0
        )
        
    def _create_retry_config(self) -> 'RetryConfig':
        """Create retry configuration."""
        from app.schemas.shared_types import RetryConfig
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
    
    async def analyze_metric_distribution(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate distribution analysis to specialized analyzer."""
        return await self.distribution_analyzer.analyze_metric_distribution(user_id, metric_name, time_range)
    
    async def detect_metric_trends(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate trend detection to specialized analyzer."""
        return await self.trend_analyzer.detect_metric_trends(user_id, metric_name, time_range)
    
    async def calculate_metric_percentiles(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime],
        percentiles: List[float] = [50.0, 75.0, 90.0, 95.0, 99.0]
    ) -> Dict[str, Any]:
        """Delegate percentile calculation to specialized analyzer."""
        return await self.percentile_analyzer.calculate_metric_percentiles(user_id, metric_name, time_range, percentiles)
    
    async def compare_metrics_performance(
        self,
        user_id: int,
        metric_names: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate metrics comparison to specialized analyzer."""
        return await self.comparison_analyzer.compare_metrics_performance(user_id, metric_names, time_range)
    
    async def detect_metric_seasonality(
        self,
        user_id: int,
        metric_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Delegate seasonality detection to specialized analyzer."""
        return await self.seasonality_analyzer.detect_metric_seasonality(user_id, metric_name, time_range)
    
    # BaseExecutionInterface Implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for metrics analysis."""
        return await self._validate_metrics_analysis_preconditions(context)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute metrics analysis core logic based on context state."""
        analysis_type = self._determine_analysis_type(context)
        return await self._execute_analysis_by_type(context, analysis_type)
        
    async def _validate_metrics_analysis_preconditions(self, context: ExecutionContext) -> bool:
        """Validate specific preconditions for metrics analysis."""
        return self._check_required_parameters(context) and self._verify_analyzer_availability()
    
    def _check_required_parameters(self, context: ExecutionContext) -> bool:
        """Check if required parameters are present in context."""
        required_fields = ['user_id', 'metric_name', 'time_range']
        state_data = getattr(context.state, 'data', {}) if context.state else {}
        return all(field in state_data for field in required_fields)
    
    def _verify_analyzer_availability(self) -> bool:
        """Verify all specialized analyzers are available."""
        analyzers = [self.distribution_analyzer, self.trend_analyzer, 
                    self.percentile_analyzer, self.comparison_analyzer, self.seasonality_analyzer]
        return all(analyzer is not None for analyzer in analyzers)
    
    def _determine_analysis_type(self, context: ExecutionContext) -> str:
        """Determine which type of analysis to perform."""
        state_data = getattr(context.state, 'data', {}) if context.state else {}
        return state_data.get('analysis_type', 'distribution')
    
    async def _execute_analysis_by_type(self, context: ExecutionContext, analysis_type: str) -> Dict[str, Any]:
        """Execute analysis based on determined type."""
        state_data = getattr(context.state, 'data', {}) if context.state else {}
        analysis_params = self._extract_analysis_parameters(state_data)
        return await self._route_to_specialized_analyzer(analysis_type, analysis_params)
    
    def _extract_analysis_parameters(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract analysis parameters from state data."""
        return {
            'user_id': state_data.get('user_id'), 'metric_name': state_data.get('metric_name'),
            'time_range': state_data.get('time_range'), 'metric_names': state_data.get('metric_names', []),
            'percentiles': state_data.get('percentiles', [50.0, 75.0, 90.0, 95.0, 99.0])
        }
    
    async def _route_to_specialized_analyzer(self, analysis_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route execution to appropriate specialized analyzer."""
        routing_map = self._get_analysis_routing_map()
        analyzer_method = routing_map.get(analysis_type, self.analyze_metric_distribution)
        return await self._execute_analyzer_method(analyzer_method, params)
    
    def _get_analysis_routing_map(self) -> Dict[str, Any]:
        """Get routing map for analysis types to methods."""
        return {
            'distribution': self.analyze_metric_distribution, 'trends': self.detect_metric_trends,
            'percentiles': self.calculate_metric_percentiles, 'comparison': self.compare_metrics_performance,
            'seasonality': self.detect_metric_seasonality
        }
    
    async def _execute_analyzer_method(self, method, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analyzer method with appropriate parameters."""
        method_params = self._prepare_method_parameters(method, params)
        return await method(**method_params)
    
    def _prepare_method_parameters(self, method, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for specific analyzer method."""
        if method == self.compare_metrics_performance:
            return self._prepare_comparison_parameters(params)
        if method == self.calculate_metric_percentiles:
            return self._prepare_percentile_parameters(params)
        return self._prepare_standard_parameters(params)
    
    def _prepare_comparison_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for metrics comparison."""
        return {
            'user_id': params['user_id'],
            'metric_names': params.get('metric_names', []),
            'time_range': params['time_range']
        }
    
    def _prepare_percentile_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for percentile calculation."""
        return {
            'user_id': params['user_id'],
            'metric_name': params['metric_name'],
            'time_range': params['time_range'],
            'percentiles': params.get('percentiles', [50.0, 75.0, 90.0, 95.0, 99.0])
        }
    
    def _prepare_standard_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare standard parameters for analysis methods."""
        return {
            'user_id': params['user_id'],
            'metric_name': params['metric_name'], 
            'time_range': params['time_range']
        }
    
    async def execute_with_modern_patterns(
        self, context: ExecutionContext
    ) -> 'ExecutionResult':
        """Execute using modern execution patterns with full orchestration."""
        return await self.execution_engine.execute(self, context)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for metrics analyzer."""
        return {
            'analyzer_status': 'healthy',
            'reliability': self.reliability_manager.get_health_status(),
            'monitoring': self.execution_monitor.get_health_status(),
            'specialized_analyzers': self._get_analyzers_health_status()
        }
    
    def _get_analyzers_health_status(self) -> Dict[str, str]:
        """Get health status of all specialized analyzers."""
        analyzers = self._get_analyzer_instances()
        return self._evaluate_analyzer_health(analyzers)
        
    def _get_analyzer_instances(self) -> Dict[str, Any]:
        """Get all analyzer instances."""
        return {
            'distribution': self.distribution_analyzer, 'trend': self.trend_analyzer,
            'percentile': self.percentile_analyzer, 'comparison': self.comparison_analyzer,
            'seasonality': self.seasonality_analyzer
        }
        
    def _evaluate_analyzer_health(self, analyzers: Dict[str, Any]) -> Dict[str, str]:
        """Evaluate health status of analyzer instances."""
        return {name: 'healthy' if analyzer else 'unavailable' 
                for name, analyzer in analyzers.items()}
