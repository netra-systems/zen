"""Modern Data Analysis Engine with BaseExecutionInterface Integration

Advanced data analysis capabilities with:
- BaseExecutionInterface standardization
- Integrated reliability patterns
- Performance monitoring
- Error handling improvements
- Circuit breaker protection

Business Value: Critical for customer insights and AI optimization
BVJ: Growth & Enterprise | Data Intelligence | +15% performance fee capture
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from abc import ABC, abstractmethod
from netra_backend.app.agents.base.interface import (
    ExecutionContext, ExecutionResult, WebSocketManagerProtocol
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor

# Import modular helpers
from netra_backend.app.agents.data_sub_agent.analysis_engine_helpers import (
    OutlierHelpers,
    SeasonalityHelpers,
    StatisticsHelpers,
    TrendHelpers,
)
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ModernAnalysisEngine(ABC):
    """Modern analysis engine with BaseExecutionInterface integration.
    
    Provides standardized execution patterns for all analysis operations
    with integrated monitoring and reliability features.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManagerProtocol] = None):
        self.agent_name = "ModernAnalysisEngine"
        self.websocket_manager = websocket_manager
        self.execution_monitor = ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler
        self.execution_engine = BaseExecutionEngine(monitor=self.execution_monitor)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute analysis operation with context."""
        operation = context.metadata.get("operation", "process_data")
        data = context.metadata.get("data", {})
        method_map = self._get_operation_method_map()
        method = method_map.get(operation, self._default_process_data)
        return await method(data, context)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate analysis operation preconditions."""
        if not context.metadata:
            return False
        operation = context.metadata.get("operation")
        data = context.metadata.get("data")
        return operation is not None and data is not None
    
    def _get_operation_method_map(self) -> Dict[str, Any]:
        """Get mapping of operations to methods."""
        return {
            "process_data": self._default_process_data,
            "calculate_statistics": self._execute_statistics,
            "detect_trend": self._execute_trend_detection,
            "detect_seasonality": self._execute_seasonality_detection,
            "identify_outliers": self._execute_outlier_detection
        }
    
    async def _default_process_data(self, data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Process data with modern patterns."""
        await self.send_status_update(context, "processing", "Processing data")
        result = await self._process_data_internal(data)
        return {"analysis_result": result, "processed": True}
    
    async def _process_data_internal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal data processing logic."""
        return {
            "status": "success" if data.get("valid", True) else "error",
            "data": data,
            "processed": True
        }
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy process_data method with modern execution."""
        context = self.create_execution_context(
            state=None, run_id=f"analysis_{int(time.time() * 1000)}"
        )
        context.metadata = {"operation": "process_data", "data": data}
        result = await self.execution_engine.execute(self, context)
        return result.result if result.success else {"error": result.error}
    
    async def _execute_statistics(self, data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute statistics calculation with context."""
        values = data.get("values", [])
        stats = self.calculate_statistics(values)
        return {"statistics": stats, "operation": "calculate_statistics"}
    
    async def _execute_trend_detection(self, data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute trend detection with context."""
        values = data.get("values", [])
        timestamps = data.get("timestamps", [])
        trend = self.detect_trend(values, timestamps)
        return {"trend": trend, "operation": "detect_trend"}
    
    async def _execute_seasonality_detection(self, data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute seasonality detection with context."""
        values = data.get("values", [])
        timestamps = data.get("timestamps", [])
        seasonality = self.detect_seasonality(values, timestamps)
        return {"seasonality": seasonality, "operation": "detect_seasonality"}
    
    async def _execute_outlier_detection(self, data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute outlier detection with context."""
        values = data.get("values", [])
        method = data.get("method", "iqr")
        outliers = self.identify_outliers(values, method)
        return {"outliers": outliers, "operation": "identify_outliers"}
    
    # Static methods delegating to helper classes
    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        """Calculate comprehensive statistics for a metric"""
        if not values:
            return StatisticsHelpers._empty_statistics()
        return StatisticsHelpers._compute_comprehensive_stats(values)
    
    @staticmethod
    def detect_trend(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect trend in time series data"""
        if len(values) < 3:
            return {"has_trend": False, "reason": "insufficient_data"}
        return TrendHelpers._perform_trend_analysis(values, timestamps)
    
    @staticmethod
    def detect_seasonality(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect daily/hourly seasonality patterns"""
        if len(values) < 24:
            return {"has_seasonality": False, "reason": "insufficient_data"}
        return SeasonalityHelpers._perform_seasonality_analysis(values, timestamps)
    
    @staticmethod
    def identify_outliers(values: List[float], method: str = "iqr") -> List[int]:
        """Identify outliers using IQR or Z-score method"""
        if not OutlierHelpers._has_sufficient_data_for_outliers(values):
            return []
        arr = np.array(values)
        return OutlierHelpers._apply_outlier_detection_method(arr, method)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get analysis engine health status."""
        return {
            "status": "healthy",
            "monitor": self.execution_monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status()
        }
    
    async def execute_analysis_operation(self, operation: str, data: Dict[str, Any], 
                                       run_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute analysis operation with modern patterns."""
        context = self.create_execution_context(
            state=None, 
            run_id=run_id or f"analysis_{int(time.time() * 1000)}"
        )
        context.metadata = {"operation": operation, "data": data}
        result = await self.execution_engine.execute(self, context)
        return result.result if result.success else {"error": result.error}


# Legacy compatibility class
class AnalysisEngine:
    """Legacy AnalysisEngine for backward compatibility.
    
    Provides the original interface while delegating to ModernAnalysisEngine
    for actual processing with modern patterns.
    """
    
    def __init__(self):
        self._modern_engine = ModernAnalysisEngine()
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with legacy interface."""
        result = await self._modern_engine.process_data(data)
        return result.get("analysis_result", result)
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Dict[str, float]:
        """Calculate comprehensive statistics - delegated to static methods."""
        return ModernAnalysisEngine.calculate_statistics(values)
    
    @staticmethod
    def detect_trend(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect trend - delegated to static methods."""
        return ModernAnalysisEngine.detect_trend(values, timestamps)
    
    @staticmethod
    def detect_seasonality(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect seasonality - delegated to static methods."""
        return ModernAnalysisEngine.detect_seasonality(values, timestamps)
    
    @staticmethod
    def identify_outliers(values: List[float], method: str = "iqr") -> List[int]:
        """Identify outliers - delegated to static methods."""
        return ModernAnalysisEngine.identify_outliers(values, method)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status - delegated to modern engine."""
        return self._modern_engine.get_health_status()