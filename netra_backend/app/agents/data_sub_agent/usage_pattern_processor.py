"""Modernized Usage Pattern Processor with BaseExecutionInterface

Usage pattern analysis with standardized execution patterns.
Now modernized with BaseExecutionInterface for reliability and monitoring.

Business Value: Critical for customer usage optimization insights.
BVJ: Growth & Enterprise | Usage Analytics | +20% optimization value capture
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, WebSocketManagerProtocol
)
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.core.exceptions import ProcessingError


class UsagePatternProcessor(BaseExecutionInterface):
    """Modernized usage pattern processor with standardized execution.
    
    Provides usage pattern analysis with reliability patterns
    and performance monitoring via BaseExecutionInterface.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None) -> None:
        self._init_base_interface(websocket_manager)
        self._init_modern_components(reliability_manager)
        
    def _init_base_interface(self, websocket_manager: Optional[WebSocketManagerProtocol]) -> None:
        """Initialize base execution interface."""
        BaseExecutionInterface.__init__(self, "UsagePatternProcessor", websocket_manager)
        
    def _init_modern_components(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize modern reliability and monitoring components."""
        self.reliability_manager = reliability_manager or ReliabilityManager()
        self.execution_monitor = ExecutionMonitor("UsagePatternProcessor")
        self.processor_core = UsagePatternProcessorCore()
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute usage pattern processing with monitoring."""
        await self.send_status_update(context, "processing", "Starting pattern analysis")
        
        data = self._extract_data_from_context(context)
        days_back = self._extract_days_back_from_context(context)
        
        result = await self._execute_pattern_processing(data, days_back, context)
        return self._format_execution_result(result)
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate preconditions for pattern processing."""
        return self._validate_context_data(context) and self._validate_context_params(context)
        
    async def process_patterns(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns with reliability patterns."""
        start_time = time.time()
        
        try:
            return await self._process_with_monitoring(data, days_back, start_time)
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._log_processing_error(e, execution_time)
            raise ProcessingError(f"Pattern processing failed: {str(e)}")
    
    async def _execute_pattern_processing(self, data: List[Dict[str, Any]], 
                                        days_back: int, context: ExecutionContext) -> Dict[str, Any]:
        """Execute pattern processing with reliability."""
        async def processing_func():
            return self.processor_core.process_patterns_sync(data, days_back)
            
        return await self.reliability_manager.execute_with_reliability(
            context, processing_func
        )
        
    async def _process_with_monitoring(self, data: List[Dict[str, Any]], 
                                     days_back: int, start_time: float) -> Dict[str, Any]:
        """Process patterns with performance monitoring."""
        with self.execution_monitor.track_execution("pattern_processing"):
            result = self.processor_core.process_patterns_sync(data, days_back)
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Pattern processing completed in {execution_time:.2f}ms")
            return result
    
    def _extract_data_from_context(self, context: ExecutionContext) -> List[Dict[str, Any]]:
        """Extract data from execution context."""
        return context.state.data_result.get('raw_data', []) if context.state.data_result else []
        
    def _extract_days_back_from_context(self, context: ExecutionContext) -> int:
        """Extract days_back parameter from context."""
        return context.metadata.get('days_back', 30)
        
    def _validate_context_data(self, context: ExecutionContext) -> bool:
        """Validate context contains required data."""
        return hasattr(context.state, 'data_result') and context.state.data_result is not None
        
    def _validate_context_params(self, context: ExecutionContext) -> bool:
        """Validate context contains required parameters."""
        return 'days_back' in context.metadata or hasattr(context.state, 'data_result')
    
    def _format_execution_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format result for BaseExecutionInterface."""
        return {
            "success": True,
            "pattern_analysis": result,
            "processor": "UsagePatternProcessor",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _log_processing_error(self, error: Exception, execution_time: float) -> None:
        """Log processing error with details."""
        logger.error(
            f"Usage pattern processing failed in {execution_time:.2f}ms: {str(error)}"
        )


class UsagePatternProcessorCore:
    """Core processing logic separated for modularity.
    
    Contains the actual pattern processing algorithms
    without the execution interface overhead.
    """
    
    def process_patterns_sync(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data synchronously."""
        daily_patterns = {}
        hourly_patterns = {}
        
        for row in data:
            self._aggregate_daily_patterns(row, daily_patterns)
            self._aggregate_hourly_patterns(row, hourly_patterns)
        
        return self._create_pattern_summary(daily_patterns, hourly_patterns, days_back)
    
    def _aggregate_daily_patterns(self, row: Dict[str, Any], daily_patterns: Dict[int, Dict[str, Any]]) -> None:
        """Aggregate daily usage patterns."""
        dow = row['day_of_week']
        
        if dow not in daily_patterns:
            daily_patterns[dow] = self._create_empty_daily_pattern()
        
        daily_patterns[dow]["total_events"] += row['event_count']
        daily_patterns[dow]["total_cost"] += row['total_cost']
        
    def _aggregate_hourly_patterns(self, row: Dict[str, Any], hourly_patterns: Dict[int, Dict[str, Any]]) -> None:
        """Aggregate hourly usage patterns."""
        hour = row['hour_of_day']
        
        if hour not in hourly_patterns:
            hourly_patterns[hour] = self._create_empty_hourly_pattern()
        
        hourly_patterns[hour]["total_events"] += row['event_count']
        hourly_patterns[hour]["total_cost"] += row['total_cost']
    
    def _create_empty_daily_pattern(self) -> Dict[str, Any]:
        """Create empty daily pattern structure."""
        return {
            "total_events": 0,
            "total_cost": 0,
            "unique_workloads": set(),
            "unique_models": set()
        }
    
    def _create_empty_hourly_pattern(self) -> Dict[str, Any]:
        """Create empty hourly pattern structure."""
        return {
            "total_events": 0,
            "total_cost": 0
        }
        
    def _create_pattern_summary(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        hourly_patterns: Dict[int, Dict[str, Any]],
        days_back: int
    ) -> Dict[str, Any]:
        """Create pattern summary result."""
        peak_day = self._find_peak_day(daily_patterns)
        peak_hour = self._find_peak_hour(hourly_patterns)
        total_cost = self._calculate_total_cost(daily_patterns)
        avg_daily_cost = total_cost / days_back if days_back > 0 else 0
        
        return self._format_pattern_result(
            daily_patterns, hourly_patterns, peak_day, peak_hour, 
            total_cost, avg_daily_cost, days_back
        )
    
    def _find_peak_day(self, daily_patterns: Dict[int, Dict[str, Any]]) -> tuple:
        """Find peak usage day."""
        return max(daily_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _find_peak_hour(self, hourly_patterns: Dict[int, Dict[str, Any]]) -> tuple:
        """Find peak usage hour."""
        return max(hourly_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _calculate_total_cost(self, daily_patterns: Dict[int, Dict[str, Any]]) -> float:
        """Calculate total cost across all days."""
        return sum(d["total_cost"] for d in daily_patterns.values())
        
    def _format_pattern_result(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        hourly_patterns: Dict[int, Dict[str, Any]],
        peak_day: tuple,
        peak_hour: tuple,
        total_cost: float,
        avg_daily_cost: float,
        days_back: int
    ) -> Dict[str, Any]:
        """Format final pattern result."""
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        return {
            "period": f"Last {days_back} days",
            "summary": self._create_summary_section(
                total_cost, avg_daily_cost, peak_day, peak_hour, 
                daily_patterns, day_names
            ),
            "daily_patterns": self._format_daily_patterns(daily_patterns, day_names),
            "hourly_distribution": hourly_patterns
        }
    
    def _create_summary_section(
        self,
        total_cost: float,
        avg_daily_cost: float,
        peak_day: tuple,
        peak_hour: tuple,
        daily_patterns: Dict[int, Dict[str, Any]],
        day_names: List[str]
    ) -> Dict[str, Any]:
        """Create summary section."""
        return {
            "total_cost": total_cost,
            "average_daily_cost": avg_daily_cost,
            "peak_usage_day": day_names[peak_day[0] - 1],
            "peak_usage_hour": f"{peak_hour[0]:02d}:00",
            "total_events": sum(d["total_events"] for d in daily_patterns.values())
        }
    
    def _format_daily_patterns(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        day_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Format daily patterns with day names."""
        return {
            day_names[k - 1]: v
            for k, v in daily_patterns.items()
        }