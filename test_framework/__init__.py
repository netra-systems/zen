"""Test framework module for Netra AI Platform."""

# Import from refactored modules
from .runner import UnifiedTestRunner
from .test_config import TEST_LEVELS, RUNNERS, SHARD_MAPPINGS
from .test_parser import parse_test_counts, parse_coverage, extract_failing_tests
from .test_orchestrator import TestOrchestrator

# Import report generators and managers
from .report_generators import generate_json_report, generate_text_report, generate_markdown_report
from .report_manager import print_summary, save_test_report

# Import test runners
from .test_runners import (
    run_backend_tests, run_frontend_tests, run_e2e_tests, run_simple_tests
)
from .failing_test_runner import run_failing_tests

# Import discovery and execution engines
from .test_discovery import TestDiscovery
from .test_execution_engine import TestExecutionEngine

# Import failure analysis
from .failure_patterns import FailurePatternAnalyzer
from .test_insights import TestInsightGenerator, FailureReportGenerator

# Import profile models
from .test_profile_models import (
    TestProfile, TestSuite, TestPriority, TestStatus, TestProfileManager
)

__all__ = [
    # Core runner classes
    'UnifiedTestRunner',
    'TestOrchestrator',
    
    # Configuration
    'TEST_LEVELS',
    'RUNNERS', 
    'SHARD_MAPPINGS',
    
    # Parsing utilities
    'parse_test_counts',
    'parse_coverage',
    'extract_failing_tests',
    
    # Report generation
    'generate_json_report',
    'generate_text_report',
    'generate_markdown_report',
    'print_summary',
    'save_test_report',
    
    # Test execution
    'run_backend_tests',
    'run_frontend_tests', 
    'run_e2e_tests',
    'run_simple_tests',
    'run_failing_tests',
    
    # Discovery and execution engines
    'TestDiscovery',
    'TestExecutionEngine',
    
    # Failure analysis
    'FailurePatternAnalyzer',
    'TestInsightGenerator',
    'FailureReportGenerator',
    
    # Profile models
    'TestProfile',
    'TestSuite',
    'TestPriority',
    'TestStatus',
    'TestProfileManager'
]