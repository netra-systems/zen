"""Performance Metrics System for Netra Platform

Comprehensive performance tracking with:
- Time to First Token (TTFT) tracking
- Phase-based execution timing
- Queue wait time monitoring
- Database query performance
- External API call metrics
- WebSocket notification latency

Business Value: 30% performance improvement through granular metrics visibility.
BVJ: Platform | Development Velocity | Real-time performance insights
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import statistics
from uuid import UUID

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    TTFT = "time_to_first_token"  # Time to first LLM response
    TOTAL_EXECUTION = "total_execution"
    QUEUE_WAIT = "queue_wait"
    DATABASE_QUERY = "database_query"
    EXTERNAL_API = "external_api"
    WEBSOCKET_LATENCY = "websocket_latency"
    INITIALIZATION = "initialization"
    TOOL_EXECUTION = "tool_execution"
    LLM_PROCESSING = "llm_processing"
    MEMORY_USAGE = "memory_usage"
    THREAD_POOL_USAGE = "thread_pool_usage"


@dataclass
class PhaseTimer:
    """Timer for tracking individual execution phases."""
    
    phase_name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def stop(self) -> float:
        """Stop the timer and return duration in milliseconds."""
        if self.end_time is None:
            self.end_time = time.perf_counter()
            self.duration_ms = (self.end_time - self.start_time) * 1000
        return self.duration_ms
    
    @property
    def is_running(self) -> bool:
        """Check if timer is still running."""
        return self.end_time is None


@dataclass
class TimingBreakdown:
    """Detailed breakdown of execution timings."""
    
    initialization_ms: float = 0.0
    tool_execution_ms: float = 0.0
    llm_processing_ms: float = 0.0
    websocket_notification_ms: float = 0.0
    database_query_ms: float = 0.0
    external_api_ms: float = 0.0
    queue_wait_ms: float = 0.0
    total_ms: float = 0.0
    
    # Additional timing details
    time_to_first_token_ms: Optional[float] = None
    parallel_execution_ms: float = 0.0  # Time saved through parallelization
    overhead_ms: float = 0.0  # Framework overhead
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary format."""
        return {
            "initialization_ms": self.initialization_ms,
            "tool_execution_ms": self.tool_execution_ms,
            "llm_processing_ms": self.llm_processing_ms,
            "websocket_notification_ms": self.websocket_notification_ms,
            "database_query_ms": self.database_query_ms,
            "external_api_ms": self.external_api_ms,
            "queue_wait_ms": self.queue_wait_ms,
            "total_ms": self.total_ms,
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "parallel_execution_ms": self.parallel_execution_ms,
            "overhead_ms": self.overhead_ms
        }
    
    def calculate_efficiency(self) -> float:
        """Calculate execution efficiency (productive time / total time)."""
        if self.total_ms == 0:
            return 0.0
        
        productive_time = (
            self.tool_execution_ms +
            self.llm_processing_ms +
            self.database_query_ms +
            self.external_api_ms
        )
        return (productive_time / self.total_ms) * 100


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_anomaly(self, baseline: float, threshold: float = 2.0) -> bool:
        """Check if metric is an anomaly compared to baseline."""
        if baseline == 0:
            return False
        deviation = abs((self.value - baseline) / baseline)
        return deviation > threshold


class EnhancedExecutionTimingCollector:
    """Enhanced timing collector with detailed phase tracking."""
    
    def __init__(self, execution_id: UUID, agent_name: str = "unknown"):
        """Initialize enhanced timing collector.
        
        Args:
            execution_id: Unique execution identifier
            agent_name: Name of the executing agent
        """
        self.execution_id = execution_id
        self.agent_name = agent_name
        self.phases: Dict[str, PhaseTimer] = {}
        self.metrics: List[PerformanceMetric] = []
        self.start_time = time.perf_counter()
        
        # TTFT tracking
        self.first_token_time: Optional[float] = None
        self.request_start_time: float = self.start_time
        
        # Parallel execution tracking
        self.parallel_tasks: Dict[str, PhaseTimer] = {}
        
    def start_phase(self, phase_name: str, metadata: Optional[Dict[str, Any]] = None) -> PhaseTimer:
        """Start tracking a new execution phase.
        
        Args:
            phase_name: Name of the phase (e.g., 'initialization', 'tool_execution')
            metadata: Optional metadata for the phase
            
        Returns:
            PhaseTimer instance for the phase
        """
        if phase_name in self.phases and self.phases[phase_name].is_running:
            logger.warning(f"Phase {phase_name} already running, stopping previous timer")
            self.phases[phase_name].stop()
        
        timer = PhaseTimer(phase_name=phase_name, metadata=metadata or {})
        self.phases[phase_name] = timer
        
        logger.debug(f"Started phase: {phase_name} for execution {self.execution_id}")
        return timer
    
    def stop_phase(self, phase_name: str) -> Optional[float]:
        """Stop tracking a phase and return its duration.
        
        Args:
            phase_name: Name of the phase to stop
            
        Returns:
            Duration in milliseconds or None if phase not found
        """
        if phase_name not in self.phases:
            logger.warning(f"Attempted to stop unknown phase: {phase_name}")
            return None
        
        duration = self.phases[phase_name].stop()
        logger.debug(f"Stopped phase: {phase_name} (duration: {duration:.2f}ms)")
        
        # Record as metric
        self.add_metric(
            metric_type=self._get_metric_type_for_phase(phase_name),
            value=duration,
            metadata={"phase": phase_name}
        )
        
        return duration
    
    def record_first_token(self) -> float:
        """Record the time to first token.
        
        Returns:
            TTFT in milliseconds
        """
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()
            ttft_ms = (self.first_token_time - self.request_start_time) * 1000
            
            self.add_metric(
                metric_type=MetricType.TTFT,
                value=ttft_ms,
                metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            logger.info(f"Time to First Token: {ttft_ms:.2f}ms")
            return ttft_ms
        
        return 0.0
    
    def start_parallel_task(self, task_name: str) -> PhaseTimer:
        """Start tracking a parallel task.
        
        Args:
            task_name: Name of the parallel task
            
        Returns:
            PhaseTimer for the task
        """
        timer = PhaseTimer(phase_name=f"parallel_{task_name}")
        self.parallel_tasks[task_name] = timer
        return timer
    
    def stop_parallel_task(self, task_name: str) -> Optional[float]:
        """Stop tracking a parallel task.
        
        Args:
            task_name: Name of the parallel task
            
        Returns:
            Duration in milliseconds
        """
        if task_name not in self.parallel_tasks:
            return None
        
        return self.parallel_tasks[task_name].stop()
    
    def add_metric(self, metric_type: MetricType, value: float, 
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a performance metric.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            metadata: Optional metadata
        """
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            agent_name=self.agent_name,
            correlation_id=str(self.execution_id),
            metadata=metadata or {}
        )
        self.metrics.append(metric)
    
    def get_breakdown(self) -> TimingBreakdown:
        """Get detailed timing breakdown.
        
        Returns:
            TimingBreakdown with all phase timings
        """
        breakdown = TimingBreakdown()
        
        # Map phases to breakdown fields
        phase_mapping = {
            "initialization": "initialization_ms",
            "init": "initialization_ms",
            "tool_execution": "tool_execution_ms",
            "tools": "tool_execution_ms",
            "llm_processing": "llm_processing_ms",
            "llm": "llm_processing_ms",
            "websocket_notification": "websocket_notification_ms",
            "websocket": "websocket_notification_ms",
            "database_query": "database_query_ms",
            "database": "database_query_ms",
            "external_api": "external_api_ms",
            "api": "external_api_ms",
            "queue_wait": "queue_wait_ms",
            "queue": "queue_wait_ms"
        }
        
        # Aggregate phase timings
        for phase_name, timer in self.phases.items():
            if timer.duration_ms is not None:
                # Find matching breakdown field
                for key, field in phase_mapping.items():
                    if key in phase_name.lower():
                        current_value = getattr(breakdown, field)
                        setattr(breakdown, field, current_value + timer.duration_ms)
                        break
        
        # Calculate total
        breakdown.total_ms = sum(
            timer.duration_ms or 0 
            for timer in self.phases.values()
            if timer.duration_ms is not None
        )
        
        # Add TTFT if available
        ttft_metrics = [m for m in self.metrics if m.metric_type == MetricType.TTFT]
        if ttft_metrics:
            breakdown.time_to_first_token_ms = ttft_metrics[0].value
        
        # Calculate parallel execution savings
        if self.parallel_tasks:
            # Parallel savings = sum of parallel tasks - max duration
            parallel_durations = [
                t.duration_ms for t in self.parallel_tasks.values() 
                if t.duration_ms is not None
            ]
            if parallel_durations:
                breakdown.parallel_execution_ms = sum(parallel_durations) - max(parallel_durations)
        
        # Calculate overhead (unaccounted time)
        actual_total = (time.perf_counter() - self.start_time) * 1000
        accounted_time = sum([
            breakdown.initialization_ms,
            breakdown.tool_execution_ms,
            breakdown.llm_processing_ms,
            breakdown.websocket_notification_ms,
            breakdown.database_query_ms,
            breakdown.external_api_ms,
            breakdown.queue_wait_ms
        ])
        breakdown.overhead_ms = max(0, actual_total - accounted_time)
        
        return breakdown
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary with key metrics.
        
        Returns:
            Dictionary containing summary metrics
        """
        breakdown = self.get_breakdown()
        
        return {
            "execution_id": str(self.execution_id),
            "agent_name": self.agent_name,
            "total_duration_ms": breakdown.total_ms,
            "time_to_first_token_ms": breakdown.time_to_first_token_ms,
            "efficiency_percent": breakdown.calculate_efficiency(),
            "breakdown": breakdown.to_dict(),
            "phase_count": len(self.phases),
            "metric_count": len(self.metrics),
            "parallel_savings_ms": breakdown.parallel_execution_ms,
            "overhead_ms": breakdown.overhead_ms
        }
    
    def _get_metric_type_for_phase(self, phase_name: str) -> MetricType:
        """Map phase name to metric type.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Corresponding MetricType
        """
        phase_lower = phase_name.lower()
        
        if "init" in phase_lower:
            return MetricType.INITIALIZATION
        elif "tool" in phase_lower:
            return MetricType.TOOL_EXECUTION
        elif "llm" in phase_lower:
            return MetricType.LLM_PROCESSING
        elif "websocket" in phase_lower:
            return MetricType.WEBSOCKET_LATENCY
        elif "database" in phase_lower or "db" in phase_lower:
            return MetricType.DATABASE_QUERY
        elif "api" in phase_lower or "external" in phase_lower:
            return MetricType.EXTERNAL_API
        elif "queue" in phase_lower:
            return MetricType.QUEUE_WAIT
        else:
            return MetricType.TOTAL_EXECUTION


class PerformanceAnalyzer:
    """Analyzes performance metrics to identify patterns and issues."""
    
    def __init__(self):
        """Initialize performance analyzer."""
        self.baseline_metrics: Dict[str, float] = {}
        self.historical_metrics: List[PerformanceMetric] = []
        
    def analyze_timing_breakdown(self, breakdown: TimingBreakdown) -> Dict[str, Any]:
        """Analyze timing breakdown for performance insights.
        
        Args:
            breakdown: Timing breakdown to analyze
            
        Returns:
            Analysis results with recommendations
        """
        analysis = {
            "bottlenecks": [],
            "recommendations": [],
            "efficiency_score": breakdown.calculate_efficiency(),
            "warnings": []
        }
        
        # Identify bottlenecks (phases taking >30% of total time)
        total = breakdown.total_ms
        if total > 0:
            phase_percentages = {
                "initialization": (breakdown.initialization_ms / total) * 100,
                "tool_execution": (breakdown.tool_execution_ms / total) * 100,
                "llm_processing": (breakdown.llm_processing_ms / total) * 100,
                "websocket_notification": (breakdown.websocket_notification_ms / total) * 100,
                "database_query": (breakdown.database_query_ms / total) * 100,
                "external_api": (breakdown.external_api_ms / total) * 100,
                "queue_wait": (breakdown.queue_wait_ms / total) * 100,
                "overhead": (breakdown.overhead_ms / total) * 100
            }
            
            for phase, percentage in phase_percentages.items():
                if percentage > 30:
                    analysis["bottlenecks"].append({
                        "phase": phase,
                        "percentage": percentage,
                        "duration_ms": getattr(breakdown, f"{phase}_ms", 0)
                    })
            
            # Generate recommendations
            if phase_percentages["queue_wait"] > 20:
                analysis["recommendations"].append(
                    "High queue wait time detected. Consider scaling workers or optimizing queue processing."
                )
            
            if phase_percentages["database_query"] > 25:
                analysis["recommendations"].append(
                    "Database queries are taking significant time. Review query optimization and indexing."
                )
            
            if phase_percentages["overhead"] > 15:
                analysis["recommendations"].append(
                    "High overhead detected. Review framework efficiency and reduce unnecessary operations."
                )
            
            if breakdown.time_to_first_token_ms and breakdown.time_to_first_token_ms > 5000:
                analysis["warnings"].append(
                    f"High TTFT ({breakdown.time_to_first_token_ms:.0f}ms). User experience may be impacted."
                )
        
        return analysis
    
    def detect_anomalies(self, metrics: List[PerformanceMetric]) -> List[Dict[str, Any]]:
        """Detect performance anomalies in metrics.
        
        Args:
            metrics: List of performance metrics to analyze
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Group metrics by type
        metrics_by_type: Dict[MetricType, List[PerformanceMetric]] = {}
        for metric in metrics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            metrics_by_type[metric.metric_type].append(metric)
        
        # Detect anomalies using statistical methods
        for metric_type, type_metrics in metrics_by_type.items():
            if len(type_metrics) < 3:
                continue
            
            values = [m.value for m in type_metrics]
            mean = statistics.mean(values)
            
            # Calculate stdev only if there's variance
            try:
                stdev = statistics.stdev(values)
            except statistics.StatisticsError:
                # All values are the same
                continue
            
            if stdev == 0:
                continue
            
            for metric in type_metrics:
                z_score = abs((metric.value - mean) / stdev)
                if z_score > 3:  # 3 standard deviations
                    anomalies.append({
                        "metric_type": metric_type.value,
                        "value": metric.value,
                        "mean": mean,
                        "z_score": z_score,
                        "timestamp": metric.timestamp.isoformat(),
                        "agent_name": metric.agent_name
                    })
        
        return anomalies
    
    def calculate_slo_compliance(self, metrics: List[PerformanceMetric], 
                                 slo_thresholds: Dict[str, float]) -> Dict[str, float]:
        """Calculate SLO compliance for performance metrics.
        
        Args:
            metrics: List of performance metrics
            slo_thresholds: SLO thresholds by metric type
            
        Returns:
            Compliance percentages by metric type
        """
        compliance = {}
        
        # Group metrics by type
        metrics_by_type: Dict[str, List[PerformanceMetric]] = {}
        for metric in metrics:
            type_key = metric.metric_type.value
            if type_key not in metrics_by_type:
                metrics_by_type[type_key] = []
            metrics_by_type[type_key].append(metric)
        
        # Calculate compliance for each type
        for metric_type, threshold in slo_thresholds.items():
            if metric_type in metrics_by_type:
                type_metrics = metrics_by_type[metric_type]
                compliant_count = sum(1 for m in type_metrics if m.value <= threshold)
                compliance[metric_type] = (compliant_count / len(type_metrics)) * 100
            else:
                compliance[metric_type] = 100.0  # No metrics means no violations
        
        return compliance