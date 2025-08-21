"""Data Sub Agent module - Consolidated Implementation

Now exports the unified DataSubAgent implementation that replaces 62+ fragmented files.
Provides reliable data insights for AI cost optimization.

Business Value: Critical for identifying 15-30% cost savings opportunities.
"""

from typing import TYPE_CHECKING

# Import shared models from central location
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, AnomalyDetectionResponse

# CONSOLIDATED IMPLEMENTATION - Primary export
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent

# Helper modules for consolidated implementation
from netra_backend.app.agents.data_sub_agent.clickhouse_client import ClickHouseClient
from netra_backend.app.agents.data_sub_agent.schema_cache import SchemaCache
from netra_backend.app.agents.data_sub_agent.performance_analyzer import PerformanceAnalyzer
from netra_backend.app.services.llm.cost_optimizer import CostOptimizer
from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator

# Import ClickHouse initialization function and client
from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing
from netra_backend.app.db.clickhouse import get_clickhouse_client

# LEGACY IMPORTS - Deprecated, will be removed in next phase
# Kept temporarily for backward compatibility during migration
try:
    from .agent import DataSubAgent as LegacyDataSubAgent
    from .query_builder import QueryBuilder
    from .analysis_engine import AnalysisEngine
    from .data_operations import DataOperations
    from .execution_engine import ExecutionEngine
except ImportError:
    # Legacy imports may fail as we clean up fragmented files
    LegacyDataSubAgent = None
    QueryBuilder = None
    AnalysisEngine = None
    DataOperations = None
    ExecutionEngine = None

__all__ = [
    # PRIMARY CONSOLIDATED IMPLEMENTATION
    'DataSubAgent',
    'ClickHouseClient', 
    'SchemaCache',
    'PerformanceAnalyzer',
    'CostOptimizer',
    'DataValidator',
    
    # SHARED TYPES
    'DataAnalysisResponse', 
    'AnomalyDetectionResponse',
    
    # CLICKHOUSE UTILITIES
    'create_workload_events_table_if_missing',
    'get_clickhouse_client',
    
    # LEGACY - Deprecated, remove after migration
    'LegacyDataSubAgent',
    'QueryBuilder',
    'AnalysisEngine', 
    'DataOperations',
    'ExecutionEngine'
]