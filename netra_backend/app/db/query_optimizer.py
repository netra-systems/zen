"""
Query Optimizer - SSOT Import Compatibility Module

This module provides SSOT import compatibility by re-exporting the QueryOptimizer
from its actual location in the performance optimization module.

Business Value Justification (BVJ):
- Segment: Platform/Internal - All user segments benefit from query performance
- Business Goal: Performance optimization reduces infrastructure costs
- Value Impact: Faster query execution improves user experience
- Strategic Impact: Enables platform scalability for customer growth
"""

# SSOT Import: Re-export QueryOptimizer from its actual location
from netra_backend.app.core.performance_query_optimizer import (
    QueryOptimizer,
    QueryMetrics
)

# Export for import compatibility
__all__ = [
    'QueryOptimizer',
    'QueryMetrics'
]