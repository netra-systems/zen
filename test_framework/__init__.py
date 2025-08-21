"""Test framework module for Netra AI Platform."""

# Import from refactored modules
from .failing_test_runner import run_failing_tests

# from .test_execution_engine import TestExecutionEngine  # Uses functions not classes
# Import failure analysis
from .failure_patterns import FailurePatternAnalyzer

# from .test_orchestrator import TestOrchestrator  # Currently not compatible
# Import report generators and managers
from .report_generators import (
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)
from .report_manager import print_summary, save_test_report
from .runner import UnifiedTestRunner
from .test_config import COMPONENT_MAPPINGS, RUNNERS, SHARD_MAPPINGS, TEST_LEVELS

# Import discovery and execution engines
from .test_discovery import TestDiscovery
from .test_insights import FailureReportGenerator, TestInsightGenerator
from .test_parser import (
    extract_failing_tests,
    extract_test_details,
    parse_coverage,
    parse_test_counts,
)

# Import profile models
from .test_profile_models import (
    TestPriority,
    TestProfile,
    TestProfileManager,
    TestStatus,
    TestSuite,
)

# Import test runners
from .test_runners import (
    run_backend_tests,
    run_e2e_tests,
    run_frontend_tests,
    run_simple_tests,
)

__all__ = [
    # Core runner classes
    'UnifiedTestRunner',
    # 'TestOrchestrator',
    
    # Configuration
    'TEST_LEVELS',
    'RUNNERS', 
    'COMPONENT_MAPPINGS',
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
    # 'TestExecutionEngine',
    
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