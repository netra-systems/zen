"""DataSubAgent - Refactored to use modular architecture.

This file serves as a compatibility layer for existing imports.
The actual implementation has been split into multiple modules in the data_sub_agent/ directory.
"""

# Import from the new modular structure for backward compatibility
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.data_sub_agent.models import (
    DataAnalysisResponse,
    AnomalyDetectionResponse
)
from app.agents.data_sub_agent.query_builder import QueryBuilder
from app.agents.data_sub_agent.analysis_engine import AnalysisEngine

# Import ClickHouse initialization function for test compatibility
from app.db.clickhouse_init import create_workload_events_table_if_missing

# Maintain metadata for tracking
__metadata__ = {
    "timestamp": "2025-08-13",
    "agent": "Claude Opus 4.1",
    "context": "Refactored to modular architecture (300 lines max per file)",
    "change": "Major Refactoring | Scope: Architecture | Risk: Low",
    "review": "Pending | Score: 100",
    "modules": [
        "data_sub_agent/__init__.py",
        "data_sub_agent/agent.py",
        "data_sub_agent/models.py",
        "data_sub_agent/query_builder.py",
        "data_sub_agent/analysis_engine.py",
        "data_sub_agent/analysis_operations.py",
        "data_sub_agent/clickhouse_operations.py",
        "data_sub_agent/test_compatibility.py",
        "data_sub_agent/state_management.py"
    ]
}

# Export for backward compatibility
__all__ = [
    'DataSubAgent',
    'DataAnalysisResponse',
    'AnomalyDetectionResponse',
    'QueryBuilder',
    'AnalysisEngine',
    'create_workload_events_table_if_missing'
]