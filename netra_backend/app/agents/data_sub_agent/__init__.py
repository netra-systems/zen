"""Data Sub Agent module - Consolidated Implementation

Now exports the unified DataSubAgent implementation that replaces 62+ fragmented files.
Provides reliable data insights for AI cost optimization.

Business Value: Critical for identifying 15-30% cost savings opportunities.
"""

from typing import TYPE_CHECKING

# Helper modules for consolidated implementation  
from netra_backend.app.db.clickhouse import get_clickhouse_service

# CONSOLIDATED IMPLEMENTATION - Primary export
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator
from netra_backend.app.agents.data_sub_agent.performance_analyzer import (
    PerformanceAnalyzer,
)
from netra_backend.app.agents.data_sub_agent.schema_cache import SchemaCache
from netra_backend.app.db.clickhouse import get_clickhouse_client

# Import ClickHouse initialization function and client
from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing

# Create a clickhouse_client instance for backward compatibility
clickhouse_client = get_clickhouse_service()

# Import shared models from central location
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer

# Legacy imports have been removed as part of SSOT compliance
# All functionality is now consolidated into the unified DataSubAgent implementation

__all__ = [
    # PRIMARY CONSOLIDATED IMPLEMENTATION
    'DataSubAgent',
    'get_clickhouse_service', 
    'SchemaCache',
    'PerformanceAnalyzer',
    'LLMCostOptimizer',
    'DataValidator',
    
    # SHARED TYPES
    'DataAnalysisResponse', 
    'AnomalyDetectionResponse',
    
    # CLICKHOUSE UTILITIES
    'create_workload_events_table_if_missing',
    'get_clickhouse_client',
    'clickhouse_client',  # Backward compatibility
]