"""Data Sub Agent module for advanced data gathering and analysis."""

from typing import TYPE_CHECKING

# Import only models first to avoid circular dependencies
from .models import DataAnalysisResponse, AnomalyDetectionResponse
# Delay import of agent to avoid circular dependency with base.py
# from .agent import DataSubAgent  # Import directly when needed
from .query_builder import QueryBuilder
from .analysis_engine import AnalysisEngine
from .clickhouse_operations import ClickHouseOperations
from .data_operations import DataOperations
from .metrics_analyzer import MetricsAnalyzer
from .performance_data_processor import PerformanceDataProcessor
from .usage_pattern_processor import UsagePatternProcessor

# Import ExecutionEngine only for type checking to avoid circular imports
if TYPE_CHECKING:
    from .execution_engine import ExecutionEngine

__all__ = [
    # 'DataSubAgent',  # Removed to avoid circular import - import directly from .agent when needed
    'DataAnalysisResponse',
    'AnomalyDetectionResponse',
    'QueryBuilder',
    'AnalysisEngine',
    'ClickHouseOperations',
    'DataOperations',
    # 'ExecutionEngine',  # Removed to avoid circular import - import directly from .execution_engine when needed
    'MetricsAnalyzer',
    'PerformanceDataProcessor',
    'UsagePatternProcessor'
]