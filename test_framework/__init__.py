"""Test framework module for Netra AI Platform."""

import sys
from pathlib import Path

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
    project_root = current_file.parent.parent
    
    # Add project root to sys.path (for main imports)
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
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