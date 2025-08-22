"""Test framework module for Netra AI Platform."""

# Import core unified components
from .runner import UnifiedTestRunner
from .test_config import COMPONENT_MAPPINGS, RUNNERS, SHARD_MAPPINGS, TEST_LEVELS

# Import discovery and parsing utilities
from .test_discovery import TestDiscovery
from .test_parser import (
    extract_failing_tests,
    extract_test_details,
    parse_coverage,
    parse_test_counts,
)

# Import report generators and managers
from .report_generators import (
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)
from .report_manager import print_summary, save_test_report

# Import unified quality analyzer
from .test_quality_analyzer import TestQualityAnalyzer, TestQualityIssue

# Import essential utilities
from .mock_utils import mock_justified
from .feature_flags import FeatureFlagManager, FeatureStatus
from .decorators import feature_flag, requires_feature, tdd_test

__all__ = [
    # Core runner classes
    'UnifiedTestRunner',
    
    # Configuration
    'TEST_LEVELS',
    'RUNNERS', 
    'COMPONENT_MAPPINGS',
    'SHARD_MAPPINGS',
    
    # Parsing utilities
    'parse_test_counts',
    'parse_coverage',
    'extract_failing_tests',
    'extract_test_details',
    
    # Report generation
    'generate_json_report',
    'generate_text_report',
    'generate_markdown_report',
    'print_summary',
    'save_test_report',
    
    # Discovery engine
    'TestDiscovery',
    
    # Quality analysis
    'TestQualityAnalyzer',
    'TestQualityIssue',
    
    # Essential utilities
    'mock_justified',
    'FeatureFlagManager',
    'FeatureStatus',
    'feature_flag',
    'requires_feature',
    'tdd_test',
]