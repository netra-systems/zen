"""
Realistic ClickHouse Operations Tests - Main Index Module
Re-exports all test classes from focused modules for backwards compatibility
"""

import pytest

# Import all test classes from focused modules
from netra_backend.tests.array_operations_tests import TestClickHouseArrayOperations
from netra_backend.tests.log_ingestion_tests import TestRealisticLogIngestion  
from netra_backend.tests.metrics_aggregation_tests import TestLLMMetricsAggregation, TestPerformanceMetricsWithClickHouse
from netra_backend.tests.timeseries_analysis_tests import TestTimeSeriesAnalysis
from netra_backend.tests.clustering_analysis_tests import TestLogClusteringAlgorithms
from netra_backend.tests.multisource_volume_tests import TestMultiSourceAggregation, TestRealisticDataVolumes

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