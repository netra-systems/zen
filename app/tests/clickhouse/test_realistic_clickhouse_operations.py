"""
Realistic ClickHouse Operations Tests - Main Index Module
Re-exports all test classes from focused modules for backwards compatibility
"""

import pytest

# Import all test classes from focused modules
from .array_operations_tests import TestClickHouseArrayOperations
from .log_ingestion_tests import TestRealisticLogIngestion  
from .metrics_aggregation_tests import TestLLMMetricsAggregation, TestPerformanceMetricsWithClickHouse
from .timeseries_analysis_tests import TestTimeSeriesAnalysis
from .clustering_analysis_tests import TestLogClusteringAlgorithms
from .multisource_volume_tests import TestMultiSourceAggregation, TestRealisticDataVolumes

# Re-export all test classes for backwards compatibility
__all__ = [
    'TestClickHouseArrayOperations',
    'TestRealisticLogIngestion',
    'TestLLMMetricsAggregation', 
    'TestPerformanceMetricsWithClickHouse',
    'TestTimeSeriesAnalysis',
    'TestLogClusteringAlgorithms',
    'TestMultiSourceAggregation',
    'TestRealisticDataVolumes'
]



if __name__ == "__main__":
    pytest.main([__file__, "-v"])