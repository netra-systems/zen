"""Test framework module for Netra AI Platform."""

import sys
from pathlib import Path

# Import core unified components
from test_framework.runner import UnifiedTestRunner
from test_framework.test_config import COMPONENT_MAPPINGS, SHARD_MAPPINGS, TEST_LEVELS, RUNNERS

# Import discovery and parsing utilities
from test_framework.test_discovery import TestDiscovery
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
from test_framework.report_manager import print_summary, save_test_report

# Import unified quality analyzer
from test_framework.test_quality_analyzer import TestQualityAnalyzer, TestQualityIssue

# Import essential utilities
from test_framework.mock_utils import mock_justified
from test_framework.feature_flags import FeatureFlagManager, FeatureStatus
from test_framework.decorators import feature_flag, requires_feature, tdd_test


def setup_test_path():
    """Set up the project root in sys.path for test imports.
    
    This function ensures that the project root is in sys.path
    so that all tests can import from the netra_backend module.
    
    Handles Windows and Unix path differences automatically.
    
    Returns:
        Path: The project root path
    """
    # Navigate from test_framework/ -> project_root/
    current_file = Path(__file__).resolve()
    project_root = current_file.parent  # Go up one level from test_framework to project root
    
    # Add project root to sys.path (for main imports)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    return project_root

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
    'setup_test_path',
]