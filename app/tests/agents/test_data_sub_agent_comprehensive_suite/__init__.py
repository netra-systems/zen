"""
DataSubAgent Comprehensive Test Suite

This test suite is organized into modular components to maintain the 300-line limit
while preserving complete test coverage. Each module focuses on specific aspects:

- conftest.py: Shared fixtures and test configuration
- test_query_builder.py: Tests for QueryBuilder class
- test_analysis_engine.py: Tests for AnalysisEngine class  
- test_data_sub_agent_basic.py: Basic DataSubAgent tests (init, caching, data fetching)
- test_data_sub_agent_analysis.py: Analysis method tests (performance, anomalies, patterns)
- test_data_sub_agent_processing.py: Processing and utility method tests
"""

# Import all test modules to ensure they're discovered by pytest
from .test_query_builder import TestQueryBuilder
from .test_analysis_engine import TestAnalysisEngine
from .test_data_sub_agent_basic import TestDataSubAgentBasic
from .test_data_sub_agent_analysis import TestDataSubAgentAnalysis
from .test_data_sub_agent_processing import TestDataSubAgentProcessing

__all__ = [
    'TestQueryBuilder',
    'TestAnalysisEngine',
    'TestDataSubAgentBasic',
    'TestDataSubAgentAnalysis',
    'TestDataSubAgentProcessing'
]