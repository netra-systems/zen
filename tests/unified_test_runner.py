#!/usr/bin/env python

# CRITICAL WINDOWS I/O FIX: Apply Windows encoding setup IMMEDIATELY before ANY imports
import sys
import os
from pathlib import Path

# Setup path FIRST
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# CRITICAL: Delay Windows encoding setup to prevent I/O errors during Docker initialization
# We'll call setup_windows_encoding() after Docker manager is initialized
_windows_encoding_setup_pending = False
try:
    from shared.windows_encoding import setup_windows_encoding
    _windows_encoding_setup_pending = True
except ImportError:
    pass  # Continue if Windows encoding not available

"""
NETRA APEX UNIFIED TEST RUNNER
==============================
Modern test runner with advanced categorization, progress tracking, and intelligent execution planning.

[U+1F4D6] COMPLETE TEST EXECUTION GUIDE: See TEST_EXECUTION_GUIDE.md for comprehensive methodology
   on running all tests without fast-fail, separating collection errors from test failures,
   and understanding test infrastructure.

NEW: ORCHESTRATION SYSTEM
=========================
Advanced layer-based test orchestration with 5 specialized agents:
- Fast Feedback (2-minute cycles)
- Full Layered Execution (dependency-aware)
- Background E2E (long-running tests)
- Real-time Progress Streaming
- Resource Management & Service Dependencies

USAGE:
    # Legacy mode (categories)
    python unified_test_runner.py --category unit       # Run specific category
    python unified_test_runner.py --categories unit api # Run multiple categories
    
    # NEW: Orchestration mode (layers)
    python unified_test_runner.py --use-layers --layers fast_feedback
    python unified_test_runner.py --execution-mode fast_feedback
    python unified_test_runner.py --execution-mode nightly
    python unified_test_runner.py --background-e2e
    python unified_test_runner.py --orchestration-status

CATEGORIES (Legacy Mode):
    CRITICAL: smoke, startup
    HIGH:     unit, security, database
    MEDIUM:   integration, api, websocket, agent
    LOW:      frontend, performance, e2e

LAYERS (New Orchestration Mode):
    fast_feedback:        Quick validation (2 min) - smoke, unit
    core_integration:     Database, API tests (10 min) - database, api, websocket
    service_integration:  Agent workflows (20 min) - agent, e2e_critical, frontend
    e2e_background:       Full E2E + performance (60 min) - cypress, e2e, performance

EXECUTION MODES:
    fast_feedback:  Quick 2-minute feedback cycle
    nightly:        Full layered execution (default)
    background:     Background E2E only
    hybrid:         Foreground layers + background E2E

LEGACY EXAMPLES:
    python unified_test_runner.py --category unit
    python unified_test_runner.py --categories unit api
    python unified_test_runner.py --category performance --window-size 30
    python unified_test_runner.py --list-categories

NEW ORCHESTRATION EXAMPLES:
    python unified_test_runner.py --use-layers --layers fast_feedback
    python unified_test_runner.py --execution-mode fast_feedback
    python unified_test_runner.py --execution-mode nightly --real-services
    python unified_test_runner.py --execution-mode hybrid --progress-mode json
    python unified_test_runner.py --background-e2e --real-llm
    python unified_test_runner.py --orchestration-status
"""

# Now safe to import everything else
import argparse
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from datetime import timedelta

# CRITICAL: Create logger AFTER Windows encoding setup to prevent I/O closed file errors
logger = logging.getLogger(__name__)

# Load environment variables from .env file to ensure CONTAINER_RUNTIME is set
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        load_dotenv(env_file, override=False)
except ImportError:
    pass  # dotenv not available, will rely on system environment

# Use centralized environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Hard failure - IsolatedEnvironment is required for test runner
    raise RuntimeError("IsolatedEnvironment required for test runner. Cannot import from dev_launcher.isolated_environment")

# Import enhanced process cleanup utilities
try:
    from shared.enhanced_process_cleanup import (
        EnhancedProcessCleanup, 
        cleanup_subprocess,
        track_subprocess,
        managed_subprocess,
        get_cleanup_instance
    )
    # Initialize cleanup instance early to register atexit handlers
    cleanup_manager = get_cleanup_instance()
except ImportError:
    try:
        # Fall back to basic Windows cleanup if enhanced not available
        from shared.windows_process_cleanup import WindowsProcessCleanup, cleanup_subprocess
        cleanup_manager = None
        track_subprocess = lambda p: None
        managed_subprocess = None
    except ImportError:
        # Create dummy functions if import fails
        WindowsProcessCleanup = None
        cleanup_subprocess = lambda p, t=10: True
        cleanup_manager = None
        track_subprocess = lambda p: None
        managed_subprocess = None

# Import test framework - using absolute imports from project root
# SSOT CONSOLIDATION: Removed circular dependency to test_framework.runner
# This module IS the canonical SSOT for UnifiedTestRunner - no need to import duplicates
from test_framework.test_config import configure_dev_environment, configure_mock_environment
from test_framework.llm_config_manager import configure_llm_testing, LLMTestMode
from test_framework.test_discovery import TestDiscovery
from test_framework.test_validation import TestValidation

# Enhanced category system imports
from test_framework.category_system import CategorySystem, ExecutionPlan, CategoryPriority
from test_framework.progress_tracker import ProgressTracker, ProgressEvent
from test_framework.auto_splitter import TestSplitter, SplittingStrategy
from test_framework.fail_fast_strategies import FailFastStrategy, FailFastMode
from test_framework.config.category_config import CategoryConfigLoader

# Environment-aware testing imports
from test_framework.environment_markers import TestEnvironment, filter_tests_by_environment

# Cypress integration
from test_framework.cypress_runner import CypressTestRunner, CypressExecutionOptions

# SSOT Orchestration integration
from test_framework.ssot.orchestration import orchestration_config
from test_framework.ssot.orchestration_enums import E2ETestCategory, ProgressOutputMode, OrchestrationMode

# Service Orchestration integration (GitHub Issue #136)
from test_framework.ssot.test_service_orchestrator import (
    TestServiceOrchestrator, 
    TestServiceConfig,
    setup_mission_critical_services,
    get_test_endpoints,
    is_docker_environment,
    should_skip_docker_tests
)

# Test Orchestrator integration - using SSOT config
if orchestration_config.orchestrator_available:
    from test_framework.orchestration.test_orchestrator_agent import (
        TestOrchestratorAgent, OrchestrationConfig, ExecutionMode,
        add_orchestrator_arguments, execute_with_orchestrator
    )
else:
    TestOrchestratorAgent = None
    OrchestrationConfig = None
    ExecutionMode = None
    add_orchestrator_arguments = None
    execute_with_orchestrator = None

# Master Orchestration Controller integration - using SSOT config
if orchestration_config.master_orchestration_available:
    from test_framework.orchestration.master_orchestration_controller import (
        MasterOrchestrationController, MasterOrchestrationConfig,
        create_fast_feedback_controller, create_full_layered_controller,
        create_background_only_controller, create_hybrid_controller, create_legacy_controller
    )
else:
    MasterOrchestrationController = None

# Background E2E Agent integration - using SSOT config
if orchestration_config.background_e2e_available:
    from test_framework.orchestration.background_e2e_agent import (
        BackgroundE2EAgent, BackgroundTaskConfig,
        add_background_e2e_arguments, handle_background_e2e_commands
    )
else:
    BackgroundE2EAgent = None
    BackgroundTaskConfig = None
    add_background_e2e_arguments = None
    handle_background_e2e_commands = None

# Test execution tracking - update import path since we're now in scripts/
try:
    from test_execution_tracker import TestExecutionTracker, TestRunRecord
except ImportError:
    TestExecutionTracker = None
    TestRunRecord = None

# Service availability checking
from test_framework.service_availability import require_real_services, ServiceUnavailableError

# Docker port discovery and centralized management
try:
    from test_framework.docker_port_discovery import DockerPortDiscovery
    DOCKER_DISCOVERY_AVAILABLE = True
except ImportError:
    DockerPortDiscovery = None
    DOCKER_DISCOVERY_AVAILABLE = False

# Import port conflict resolver for safe allocation
try:
    from test_framework.port_conflict_fix import (
        PortConflictResolver, 
        allocate_docker_ports_safely,
        SafePortAllocator
    )
    PORT_CONFLICT_RESOLVER_AVAILABLE = True
except ImportError:
    PORT_CONFLICT_RESOLVER_AVAILABLE = False
    PortConflictResolver = None
    allocate_docker_ports_safely = None
    SafePortAllocator = None
    
try:
    from test_framework.unified_docker_manager import (
        UnifiedDockerManager,
        EnvironmentType, 
        ServiceStatus,
        ServiceMode
    )
    CENTRALIZED_DOCKER_AVAILABLE = True
except ImportError:
    CENTRALIZED_DOCKER_AVAILABLE = False
    UnifiedDockerManager = None
    EnvironmentType = None
    ServiceStatus = None
    ServiceMode = None

# Pytest-cov availability detection for coverage support
try:
    # Try importing the main pytest-cov plugin
    import pytest_cov
    PYTEST_COV_AVAILABLE = True
except ImportError:
    try:
        # Fallback: check if pytest can load the cov plugin
        import subprocess
        import sys
        import shutil
        import platform

        # Use platform-aware Python command detection (same logic as _detect_python_command)
        if platform.system() == 'Windows':
            python_commands = ['python', 'py', 'python3']
        else:
            python_commands = ['python3', 'python', 'py']

        # Find a working Python command
        python_cmd = None
        for cmd in python_commands:
            if shutil.which(cmd):
                try:
                    version_result = subprocess.run(
                        [cmd, '--version'], capture_output=True, text=True, timeout=5
                    )
                    if version_result.returncode == 0 and 'Python 3' in version_result.stdout:
                        python_cmd = cmd
                        break
                except:
                    continue

        if python_cmd:
            result = subprocess.run([python_cmd, "-m", "pytest", "--help"],
                                  capture_output=True, text=True, timeout=10)
            PYTEST_COV_AVAILABLE = "--cov" in result.stdout
        else:
            # Final fallback to sys.executable
            result = subprocess.run([sys.executable, "-m", "pytest", "--help"],
                                  capture_output=True, text=True, timeout=10)
            PYTEST_COV_AVAILABLE = "--cov" in result.stdout
    except Exception:
        PYTEST_COV_AVAILABLE = False


# =============================================================================
# JSON OUTPUT SIZE OPTIMIZATION SYSTEM
# =============================================================================
# Business Value Protection: $500K+ ARR (Development velocity and CI/CD efficiency)
# Addresses issue: Large JSON outputs (127KB+) causing memory and performance issues
# Implementation follows TDD approach with comprehensive test validation

class JsonSizeExceedsLimitError(Exception):
    """Raised when JSON output exceeds configured size limits."""
    pass


class JsonSizeAnalyzer:
    """Analyzes JSON data size and provides metrics."""

    def __init__(self):
        self.size_cache = {}

    def get_size_metrics(self, data_or_file) -> Dict[str, any]:
        """
        Get comprehensive size metrics for JSON data or file.

        Args:
            data_or_file: Either dict/list JSON data or Path to JSON file

        Returns:
            Dict with size metrics including bytes, KB, and analysis
        """
        if isinstance(data_or_file, (str, Path)):
            # File path provided
            file_path = Path(data_or_file)
            if not file_path.exists():
                return {"error": "File does not exist", "size_bytes": 0, "size_kb": 0}

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                size_bytes = len(content.encode('utf-8'))
            except Exception as e:
                return {"error": f"Failed to read file: {e}", "size_bytes": 0, "size_kb": 0}
        else:
            # JSON data provided
            try:
                json_str = json.dumps(data_or_file, indent=2, default=str)
                size_bytes = len(json_str.encode('utf-8'))
            except Exception as e:
                return {"error": f"Failed to serialize JSON: {e}", "size_bytes": 0, "size_kb": 0}

        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024

        return {
            "size_bytes": size_bytes,
            "size_kb": size_kb,
            "size_mb": size_mb,
            "exceeds_limit": False,  # Will be set by caller with specific limit
            "human_readable": self._format_size_human(size_bytes)
        }

    def _format_size_human(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 / 1024:.1f} MB"


class JsonOutputOptimizer:
    """Core JSON output optimization controller."""

    def __init__(self, default_size_limit_kb: int = 100):
        self.default_size_limit_kb = default_size_limit_kb
        self.size_analyzer = JsonSizeAnalyzer()
        self.verbosity_controller = None  # Will be initialized when needed

    def detect_large_output(self, data_or_file, size_limit_kb: Optional[int] = None) -> bool:
        """
        Detect if JSON output exceeds size limits.

        Args:
            data_or_file: JSON data (dict/list) or file path
            size_limit_kb: Size limit in KB (uses default if None)

        Returns:
            True if output exceeds limit, False otherwise
        """
        limit_kb = size_limit_kb or self.default_size_limit_kb
        metrics = self.get_size_metrics(data_or_file)

        if "error" in metrics:
            return False  # Can't determine size, assume not large

        return metrics["size_kb"] > limit_kb

    def get_size_metrics(self, data_or_file) -> Dict[str, any]:
        """Get size metrics with limit checking."""
        metrics = self.size_analyzer.get_size_metrics(data_or_file)
        if "error" not in metrics:
            metrics["exceeds_limit"] = metrics["size_kb"] > self.default_size_limit_kb
        return metrics


class JsonVerbosityController:
    """Controls JSON output verbosity with 5 levels of detail."""

    VERBOSITY_LEVELS = {
        1: "minimal",      # Summary only
        2: "standard",     # Summary + basic results
        3: "verbose",      # All details
        4: "debug",        # Debug information included
        5: "full"          # Complete details with internal data
    }

    def __init__(self):
        self.current_level = 2  # Standard by default

    def apply_verbosity_level(self, data: Dict[str, any], level: int) -> Dict[str, any]:
        """
        Apply verbosity level to JSON data.

        Args:
            data: Original JSON data
            level: Verbosity level (1-5)

        Returns:
            Filtered JSON data according to verbosity level
        """
        if level not in self.VERBOSITY_LEVELS:
            level = 2  # Default to standard

        result = {}

        # Level 1: Minimal (summary only)
        if level >= 1:
            if "summary" in data:
                result["summary"] = data["summary"]

        # Level 2: Standard (summary + basic results)
        if level >= 2:
            if "categories" in data:
                result["categories"] = self._filter_categories_basic(data["categories"])
            if "overall_success" in data:
                result["overall_success"] = data["overall_success"]
            if "total_duration" in data:
                result["total_duration"] = data["total_duration"]
            # Include basic results info but not detailed output
            if "detailed_results" in data and level == 2:
                basic_results = []
                for item in data["detailed_results"]:
                    if isinstance(item, dict):
                        basic_item = {
                            key: value for key, value in item.items()
                            if key not in ["detailed_output", "stack_trace", "metadata"]
                        }
                        basic_results.append(basic_item)
                    else:
                        basic_results.append(item)
                result["detailed_results"] = basic_results

        # Level 3: Verbose (all main details)
        if level >= 3:
            if "detailed_results" in data:
                result["detailed_results"] = self._filter_detailed_results(data["detailed_results"])
            if "execution_plan" in data:
                result["execution_plan"] = data["execution_plan"]
            if "category_statistics" in data:
                result["category_statistics"] = data["category_statistics"]

        # Level 4: Debug (include debug information)
        if level >= 4:
            if "progress_tracking" in data:
                result["progress_tracking"] = data["progress_tracking"]
            if "debug_info" in data:
                result["debug_info"] = data["debug_info"]

        # Level 5: Full (everything including internal data)
        if level >= 5:
            # Include all original data
            result = data.copy()

        return result

    def _filter_categories_basic(self, categories: Dict) -> Dict:
        """Filter categories to basic information only."""
        filtered = {}
        for name, details in categories.items():
            filtered[name] = {
                "success": details.get("success", False),
                "duration": details.get("duration", 0)
            }
            # Include failure information if present
            if not details.get("success", True):
                filtered[name]["error"] = details.get("error", "Unknown error")
        return filtered

    def _filter_detailed_results(self, detailed_results: List) -> List:
        """Filter detailed results to essential information."""
        if not detailed_results:
            return []

        # For large result sets, limit to first 50 + failed tests
        if len(detailed_results) > 100:
            # Take first 50 and any failed tests
            filtered = detailed_results[:50]
            failed_tests = [r for r in detailed_results[50:] if r.get("status") == "FAILED"]
            filtered.extend(failed_tests[:25])  # Limit failed tests to 25
            return filtered

        return detailed_results


class JsonTruncator:
    """Truncates JSON data while preserving essential information."""

    def __init__(self):
        self.essential_fields = ["summary", "overall_success", "total_duration", "failed_tests"]

    def truncate_preserving_essentials(self, data: Dict[str, any],
                                     target_size_kb: int,
                                     preserve_fields: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Truncate JSON data to target size while preserving essential fields.

        Args:
            data: Original JSON data
            target_size_kb: Target size in KB
            preserve_fields: List of fields to always preserve

        Returns:
            Truncated JSON data
        """
        preserve_fields = preserve_fields or self.essential_fields
        target_size_bytes = target_size_kb * 1024

        # Start with essential fields
        result = {}
        for field in preserve_fields:
            if field in data:
                result[field] = data[field]

        # Check if we're already under target size
        current_size = len(json.dumps(result, default=str).encode('utf-8'))
        if current_size >= target_size_bytes:
            # Essential fields alone exceed target, return minimal summary
            return {"summary": data.get("summary", {}), "truncated": True}

        # Add other fields in order of importance
        remaining_size = target_size_bytes - current_size

        # Priority order for additional fields
        priority_fields = [
            "categories", "execution_plan", "category_statistics",
            "detailed_results", "progress_tracking", "debug_info"
        ]

        for field in priority_fields:
            if field in data and field not in result:
                field_data = data[field]

                # Estimate field size
                field_json = json.dumps({field: field_data}, default=str)
                field_size = len(field_json.encode('utf-8'))

                if field_size <= remaining_size:
                    result[field] = field_data
                    remaining_size -= field_size
                elif field == "detailed_results" and isinstance(field_data, list):
                    # Try to include partial detailed results
                    partial_results = self._truncate_detailed_results(
                        field_data, remaining_size
                    )
                    if partial_results:
                        result[field] = partial_results
                        result["truncated_detailed_results"] = True
                    break
                else:
                    break

        result["truncated"] = True
        result["original_size_estimate"] = len(json.dumps(data, default=str).encode('utf-8'))
        result["target_size_kb"] = target_size_kb

        return result

    def _truncate_detailed_results(self, results: List, max_size_bytes: int) -> List:
        """Truncate detailed results to fit within size limit."""
        if not results:
            return []

        truncated = []
        current_size = 0

        # Always include failed tests first
        failed_results = [r for r in results if r.get("status") == "FAILED"]
        for result in failed_results:
            result_json = json.dumps(result, default=str)
            result_size = len(result_json.encode('utf-8'))

            if current_size + result_size > max_size_bytes:
                break

            truncated.append(result)
            current_size += result_size

        # Add passed tests until size limit
        passed_results = [r for r in results if r.get("status") != "FAILED"]
        for result in passed_results:
            result_json = json.dumps(result, default=str)
            result_size = len(result_json.encode('utf-8'))

            if current_size + result_size > max_size_bytes:
                break

            truncated.append(result)
            current_size += result_size

        return truncated


class JsonSizeLimiter:
    """Enforces JSON size limits with validation and auto-truncation."""

    def __init__(self, max_size_mb: float = 1.0):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.truncator = JsonTruncator()

    def validate_and_process(self, data: Dict[str, any]) -> Dict[str, any]:
        """
        Validate JSON size and raise exception if exceeds limit.

        Args:
            data: JSON data to validate

        Returns:
            Original data if within limits

        Raises:
            JsonSizeExceedsLimitError: If data exceeds size limits
        """
        json_str = json.dumps(data, default=str)
        size_bytes = len(json_str.encode('utf-8'))

        if size_bytes > self.max_size_bytes:
            size_mb = size_bytes / 1024 / 1024
            raise JsonSizeExceedsLimitError(
                f"JSON size ({size_mb:.2f} MB) exceeds limit ({self.max_size_mb} MB)"
            )

        return data

    def process_with_auto_truncation(self, data: Dict[str, any]) -> Dict[str, any]:
        """
        Process JSON data with automatic truncation if exceeds limits.

        Args:
            data: JSON data to process

        Returns:
            Original data if within limits, truncated data otherwise
        """
        json_str = json.dumps(data, default=str)
        size_bytes = len(json_str.encode('utf-8'))

        if size_bytes > self.max_size_bytes:
            # Auto-truncate to 80% of limit to provide buffer
            target_size_kb = int(self.max_size_mb * 1024 * 0.8)
            return self.truncator.truncate_preserving_essentials(data, target_size_kb)

        return data


class ProgressiveDetailController:
    """Controls detail level based on data size and test count."""

    def __init__(self):
        self.size_thresholds = {
            "small": 100,    # < 100 tests
            "medium": 1000,  # 100-1000 tests
            "large": 5000    # > 1000 tests
        }

    def apply_progressive_detail(self, data: Dict[str, any]) -> Dict[str, any]:
        """
        Apply progressive detail reduction based on data size.

        Args:
            data: Original test data

        Returns:
            Data with appropriate detail level
        """
        test_count = self._estimate_test_count(data)

        if test_count < self.size_thresholds["small"]:
            # Small suites: Full detail
            return data
        elif test_count < self.size_thresholds["medium"]:
            # Medium suites: Reduced detail
            return self._apply_medium_detail(data)
        else:
            # Large suites: Minimal detail
            return self._apply_minimal_detail(data)

    def _estimate_test_count(self, data: Dict[str, any]) -> int:
        """Estimate number of tests from data structure."""
        # Try multiple ways to estimate test count
        if "summary" in data and "total_tests" in data["summary"]:
            return data["summary"]["total_tests"]

        if "detailed_results" in data and isinstance(data["detailed_results"], list):
            return len(data["detailed_results"])

        if "categories" in data:
            total = 0
            for category_data in data["categories"].values():
                if isinstance(category_data, dict) and "test_count" in category_data:
                    total += category_data["test_count"]
            if total > 0:
                return total

        # Default estimate based on data structure
        return 100

    def _apply_medium_detail(self, data: Dict[str, any]) -> Dict[str, any]:
        """Apply medium detail level (reduced but comprehensive)."""
        result = {
            "summary": data.get("summary", {}),
            "overall_success": data.get("overall_success", True),
            "total_duration": data.get("total_duration", 0),
            "categories": data.get("categories", {})
        }

        # Include limited detailed results
        if "detailed_results" in data:
            detailed = data["detailed_results"]
            if isinstance(detailed, list) and len(detailed) > 50:
                # Include failed tests + sample of passed tests
                failed = [r for r in detailed if r.get("status") == "FAILED"]
                passed = [r for r in detailed if r.get("status") != "FAILED"]

                result["detailed_results"] = failed + passed[:30]  # Up to 30 passed tests
                result["detailed_results_truncated"] = len(detailed)
            else:
                result["detailed_results"] = detailed

        return result

    def _apply_minimal_detail(self, data: Dict[str, any]) -> Dict[str, any]:
        """Apply minimal detail level (summary focus)."""
        result = {
            "summary": data.get("summary", {}),
            "overall_success": data.get("overall_success", True),
            "total_duration": data.get("total_duration", 0)
        }

        # Include only failed test information
        if "detailed_results" in data:
            detailed = data["detailed_results"]
            if isinstance(detailed, list):
                failed = [r for r in detailed if r.get("status") == "FAILED"]
                if failed:
                    result["failed_tests"] = failed[:20]  # Up to 20 failed tests

        # Basic category summary
        if "categories" in data:
            category_summary = {}
            for name, details in data["categories"].items():
                category_summary[name] = {
                    "success": details.get("success", True),
                    "duration": details.get("duration", 0)
                }
            result["category_summary"] = category_summary

        result["detail_level"] = "minimal"
        result["large_suite_optimization"] = True

        return result


class JsonFormatter:
    """Handles JSON formatting options for size optimization."""

    def __init__(self):
        self.compact_separators = (',', ':')  # No spaces
        self.pretty_separators = (', ', ': ')  # With spaces

    def format_compact(self, data: Dict[str, any]) -> str:
        """Format JSON in compact mode (no extra whitespace)."""
        return json.dumps(data, separators=self.compact_separators, default=str)

    def format_pretty(self, data: Dict[str, any], indent: int = 2) -> str:
        """Format JSON in pretty-print mode with indentation."""
        return json.dumps(data, indent=indent, separators=self.pretty_separators, default=str)

    def format_auto(self, data: Dict[str, any], size_threshold_kb: int = 50) -> str:
        """
        Automatically choose format based on data size.

        Args:
            data: JSON data to format
            size_threshold_kb: Size threshold for switching to compact mode

        Returns:
            Formatted JSON string
        """
        # Try compact first to check size
        compact_json = self.format_compact(data)
        compact_size_kb = len(compact_json.encode('utf-8')) / 1024

        if compact_size_kb > size_threshold_kb:
            return compact_json
        else:
            # Use pretty format for smaller data
            return self.format_pretty(data)


class JsonFieldFilter:
    """Filters JSON fields to reduce output size."""

    def __init__(self):
        self.default_essential_fields = [
            "summary", "overall_success", "total_duration",
            "categories", "failed_tests"
        ]

    def filter_fields(self, data: Dict[str, any],
                     include_fields: Optional[List[str]] = None,
                     exclude_fields: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Filter JSON data to include/exclude specific fields.

        Args:
            data: Original JSON data
            include_fields: Fields to include (whitelist approach)
            exclude_fields: Fields to exclude (blacklist approach)

        Returns:
            Filtered JSON data
        """
        if include_fields is not None:
            # Whitelist approach: only include specified fields
            result = {}
            for field in include_fields:
                if field in data:
                    if field == "detailed_results" and isinstance(data[field], list):
                        # Apply field filtering to detailed results as well
                        result[field] = self._filter_detailed_results_fields(
                            data[field], include_fields
                        )
                    else:
                        result[field] = data[field]
            return result

        elif exclude_fields is not None:
            # Blacklist approach: exclude specified fields
            result = data.copy()
            for field in exclude_fields:
                result.pop(field, None)
            return result

        else:
            # No filtering specified, return original
            return data

    def _filter_detailed_results_fields(self, results: List, include_fields: List[str]) -> List:
        """Filter fields within detailed results."""
        filtered_results = []

        for result in results:
            if isinstance(result, dict):
                filtered_result = {}
                for field in include_fields:
                    if field in result:
                        filtered_result[field] = result[field]
                filtered_results.append(filtered_result)
            else:
                filtered_results.append(result)

        return filtered_results


class UnifiedTestRunner:
    """Modern test runner with category-based execution and progress tracking."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_framework_path = self.project_root / "test_framework"
        self.backend_path = self.project_root / "netra_backend"
        self.auth_path = self.project_root / "auth_service"
        self.frontend_path = self.project_root / "frontend"
        
        # Detect the correct Python command for cross-platform compatibility
        self.python_command = self._detect_python_command()
        
        # Initialize category system components
        self.config_loader = CategoryConfigLoader(self.project_root)
        config = self.config_loader.load_config()
        
        self.category_system = self.config_loader.create_category_system(config)
        self.progress_tracker = None
        self.test_splitter = None
        self.fail_fast_strategy = None
        self.execution_plan = None
        
        # Initialize test execution tracker
        self.test_tracker = TestExecutionTracker(self.project_root) if TestExecutionTracker else None

        # Initialize JSON output optimization system
        self.json_optimizer = None  # Will be initialized with args when needed
        self.json_verbosity_controller = JsonVerbosityController()
        self.json_formatter = JsonFormatter()
        self.json_field_filter = JsonFieldFilter()

        # Initialize Cypress runner lazily to avoid Docker issues during init
        self.cypress_runner = None
        
        # Initialize centralized Docker manager
        self.docker_manager = None
        self.docker_environment = None
        self.docker_ports = None

    def _detect_staging_environment(self, args) -> bool:
        """Enhanced staging environment detection for GCP staging context.
        
        Properly identifies GCP staging environment using multiple environment variables
        to ensure accurate staging detection and prevent false negatives.
        
        Args:
            args: Command line arguments containing env parameter
            
        Returns:
            bool: True if running in staging environment, False otherwise
        """
        from shared.isolated_environment import get_env
        
        env = get_env()
        
        # Primary check: explicit env argument
        if hasattr(args, 'env') and args.env == 'staging':
            return True
            
        # Enhanced GCP staging detection
        environment_vars = [
            env.get('ENVIRONMENT'),
            env.get('NETRA_ENVIRONMENT'),
            env.get('TEST_ENV')
        ]
        
        # Check if any environment variable indicates staging
        for env_var in environment_vars:
            if env_var and env_var.lower() == 'staging':
                return True
                
        # GCP project detection
        gcp_project_vars = [
            env.get('GCP_PROJECT_ID'),
            env.get('GOOGLE_CLOUD_PROJECT'),
            env.get('GCLOUD_PROJECT')
        ]
        
        # Check if any GCP project variable indicates staging
        for project_var in gcp_project_vars:
            if project_var and 'staging' in project_var.lower():
                return True
                
        # Additional GCP staging indicators
        staging_indicators = [
            env.get('STAGING_ENVIRONMENT'),
            env.get('CLOUD_RUN_SERVICE') and 'staging' in env.get('CLOUD_RUN_SERVICE', '').lower(),
            env.get('K_SERVICE') and 'staging' in env.get('K_SERVICE', '').lower()
        ]
        
        for indicator in staging_indicators:
            if indicator:
                return True
                
        return False
        
        # Test execution timeout fix for iterations 41-60
        env = get_env()
        self.max_collection_size = int(env.get("MAX_TEST_COLLECTION_SIZE", "1000"))
        
        # Test configurations - Use project root as working directory to fix import issues
        # ISSUE #558 FIX: Use centralized pyproject.toml instead of missing service-specific pytest.ini files
        self.test_configs = {
            "backend": {
                "path": self.project_root,  # Changed from backend_path to project_root
                "test_dir": "netra_backend/tests",  # Updated to full path from root
                "config": "pyproject.toml",  # FIXED: Use centralized config instead of missing pytest.ini
                "command": f"{self.python_command} -m pytest"
            },
            "auth": {
                "path": self.project_root,  # Changed from auth_path to project_root
                "test_dir": "auth_service/tests",  # Updated to full path from root
                "config": "pyproject.toml",  # FIXED: Use centralized config instead of missing pytest.ini
                "command": f"{self.python_command} -m pytest"
            },
            "frontend": {
                "path": self.frontend_path,  # Frontend can stay as-is since it uses npm
                "test_dir": "__tests__",
                "config": "jest.config.cjs",
                "command": "npm test"
            }
        }
    
    def _detect_python_command(self) -> str:
        """Detect the correct Python command for the current platform."""
        import shutil
        import platform

        # Platform-aware command ordering
        if platform.system() == 'Windows':
            # On Windows, 'python' and 'py' are more reliable than 'python3'
            commands_to_try = ['python', 'py', 'python3']
            default_fallback = 'python'
        else:
            # On Unix-like systems, prefer python3
            commands_to_try = ['python3', 'python', 'py']
            default_fallback = 'python3'

        print(f"[DEBUG] Detecting Python command on {platform.system()}...")
        print(f"[DEBUG] Trying commands in order: {commands_to_try}")

        for cmd in commands_to_try:
            print(f"[DEBUG] Checking if '{cmd}' is available...")
            if shutil.which(cmd):
                # Verify it's actually Python 3
                try:
                    print(f"[DEBUG] Testing '{cmd}' for Python 3 compatibility...")
                    result = subprocess.run(
                        [cmd, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and 'Python 3' in result.stdout:
                        print(f"[INFO] Successfully detected Python command: '{cmd}' -> {result.stdout.strip()}")
                        return cmd
                    else:
                        print(f"[DEBUG] '{cmd}' version check failed: {result.stdout.strip()}")
                except (subprocess.TimeoutExpired, Exception) as e:
                    print(f"[DEBUG] '{cmd}' execution failed: {e}")
                    continue
            else:
                print(f"[DEBUG] '{cmd}' not found in PATH")

        # Enhanced fallback with platform awareness
        print(f"[WARNING] Could not detect working Python 3 command from {commands_to_try}")
        print(f"[WARNING] Falling back to '{default_fallback}' - this may fail if not available")

        # Final verification of fallback
        if shutil.which(default_fallback):
            print(f"[INFO] Fallback command '{default_fallback}' is available")
            return default_fallback
        else:
            # If even fallback doesn't exist, raise an error with helpful message
            raise RuntimeError(
                f"No working Python 3 command found on {platform.system()}. "
                f"Tried: {commands_to_try}. Please ensure Python 3 is installed and available in PATH."
            )
    
    def initialize_components(self, args: argparse.Namespace):
        """Initialize test execution components based on arguments."""
        # Initialize progress tracker
        if args.progress_mode:
            config = self.config_loader.load_config()
            self.progress_tracker = self.config_loader.create_progress_tracker(config)
        
        # Initialize test splitter
        if not args.disable_auto_split:
            self.test_splitter = TestSplitter(project_root=self.project_root)
            self.test_splitter.strategy = SplittingStrategy(args.splitting_strategy)
            self.target_window_duration = timedelta(minutes=args.window_size)
        
        # Initialize fail-fast strategy
        if args.fail_fast_mode:
            self.fail_fast_strategy = FailFastStrategy(
                project_root=self.project_root,
                mode=FailFastMode(args.fail_fast_mode)
            )
    
    def run(self, args: argparse.Namespace) -> int:
        """Main entry point for test execution."""
        # CRITICAL: Clean up any existing test environment before starting
        # This prevents Docker resource accumulation and daemon crashes
        try:
            self.cleanup_test_environment()
        except Exception as e:
            print(f"[WARNING] Pre-test cleanup failed, continuing anyway: {e}")
        
        try:
            # Initialize components
            self.initialize_components(args)
            
            # Configure environment
            self._configure_environment(args)
            
            # PERFORMANCE: Skip service orchestration for fast collection
            print(f"[DEBUG] fast_collection = {getattr(args, 'fast_collection', None)}")
            if hasattr(args, 'fast_collection') and args.fast_collection:
                print("[INFO] Fast collection mode - skipping service orchestration")
                # Skip Docker and service setup
                categories_to_run = self._determine_categories_to_run(args)
                
                # Use fast-path collection
                if args.pattern:
                    results = {}
                    for category in categories_to_run:
                        tests = self._fast_path_collect_tests(args.pattern, category)
                        results[category] = {
                            "success": True,
                            "duration": 0.0,
                            "output": f"Fast collection: {len(tests)} test files found",
                            "errors": "",
                            "test_count": len(tests)
                        }
                    
                    print(f"✅ Fast collection completed: {sum(len(r.get('output', '').split()) for r in results.values())} files")
                    return 0


            # Check service availability if real services or E2E tests are requested
            categories_to_run = self._determine_categories_to_run(args)
            e2e_categories = {'e2e', 'e2e_critical', 'cypress'}
            running_e2e = bool(set(categories_to_run) & e2e_categories)
            
            # Service Orchestration (GitHub Issue #136) - Auto-start services if requested
            service_info = None
            if hasattr(args, 'auto_services') and args.auto_services:
                try:
                    print("[INFO] Auto-services enabled - setting up test services...")
                    
                    # Determine test category for service requirements
                    test_category = getattr(args, 'service_category', None)
                    if not test_category and categories_to_run:
                        # Infer category from what's being run
                        if 'mission_critical' in categories_to_run:
                            test_category = 'mission_critical'
                        elif 'integration' in categories_to_run:
                            test_category = 'integration'
                        elif 'websocket' in categories_to_run:
                            test_category = 'websocket'
                        else:
                            test_category = categories_to_run[0] if categories_to_run else 'default'
                    
                    # Create service orchestrator
                    service_config = TestServiceConfig(
                        auto_start_services=True,
                        wait_for_health=True,
                        health_check_timeout=getattr(args, 'service_timeout', 60),
                        fallback_to_staging=not getattr(args, 'prefer_staging', False)
                    )
                    
                    orchestrator = TestServiceOrchestrator(service_config)
                    
                    # Setup services (this may start Docker containers)
                    import asyncio
                    if asyncio.get_event_loop().is_running():
                        # We're in an async context - need to use thread
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                lambda: asyncio.run(orchestrator.setup_for_tests(test_category))
                            )
                            service_info = future.result(timeout=getattr(args, 'service_timeout', 60))
                    else:
                        # Safe to run async directly
                        service_info = asyncio.run(orchestrator.setup_for_tests(test_category))
                    
                    # Store orchestrator for cleanup
                    self.service_orchestrator = orchestrator
                    
                    # Display service status
                    endpoints = service_info.get('endpoints', {})
                    if endpoints:
                        print("[SUCCESS] Test services ready!")
                        for key, url in endpoints.items():
                            print(f"   {key}: {url}")
                        
                        # Set environment variables for tests to use
                        env = get_env()
                        if 'backend_url' in endpoints:
                            env.set('TEST_BACKEND_URL', endpoints['backend_url'], 'service_orchestrator')
                        if 'websocket_url' in endpoints:
                            env.set('TEST_WEBSOCKET_URL', endpoints['websocket_url'], 'service_orchestrator')
                        if 'auth_url' in endpoints:
                            env.set('TEST_AUTH_URL', endpoints['auth_url'], 'service_orchestrator')
                    else:
                        print("[WARNING] No service endpoints configured - tests may use fallback URLs")
                        
                except Exception as e:
                    print(f"[ERROR] Service orchestration failed: {e}")
                    print("[WARNING] Continuing with tests - they may fail if services not available")
                    service_info = None
            
            # CRITICAL: Setup E2E Docker environment if running E2E tests
            if running_e2e and args.env != 'staging':
                try:
                    print(f"[INFO] Detected E2E tests in categories: {set(categories_to_run) & e2e_categories}")
                    print("[INFO] Setting up E2E Docker environment...")
                    
                    # Import E2E Docker helper
                    from test_framework.e2e_docker_helper import E2EDockerHelper
                    import asyncio
                    
                    # Setup E2E environment
                    test_id = f"unified-runner-{int(time.time())}"
                    self.e2e_docker_helper = E2EDockerHelper(test_id=test_id)
                    
                    # Run async setup
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        service_urls = loop.run_until_complete(
                            self.e2e_docker_helper.setup_e2e_environment(timeout=180)
                        )
                        print(f"[SUCCESS] E2E Docker environment ready!")
                        print(f"   Backend: {service_urls['backend']}")
                        print(f"   Auth: {service_urls['auth']}")
                        print(f"   WebSocket: {service_urls['websocket']}")
                        
                        # Set environment variables for tests
                        env = get_env()
                        env.set('E2E_BACKEND_URL', service_urls['backend'], 'e2e_setup')
                        env.set('E2E_AUTH_URL', service_urls['auth'], 'e2e_setup') 
                        env.set('E2E_WEBSOCKET_URL', service_urls['websocket'], 'e2e_setup')
                        env.set('E2E_POSTGRES_URL', service_urls['postgres'], 'e2e_setup')
                        env.set('E2E_REDIS_URL', service_urls['redis'], 'e2e_setup')
                        
                    finally:
                        loop.close()
                        
                except Exception as e:
                    print(f"[ERROR] Failed to setup E2E Docker environment: {e}")
                    print("[ERROR] E2E tests require Docker. Please ensure Docker is running and try again.")
                    return 1
            
            # Skip local service checks for staging - use remote staging services  
            if args.env != 'staging' and (args.real_services or args.real_llm or args.env in ['dev'] or running_e2e):
                # Only check services if we haven't already set up E2E Docker
                if not (running_e2e and hasattr(self, 'e2e_docker_helper')):
                    self._check_service_availability(args)
            
            # Start test tracking session
            if self.test_tracker:
                self.test_tracker.start_session(
                    environment=args.env,
                    categories=args.categories if hasattr(args, 'categories') else None
                )
            
            # Determine categories to run
            categories_to_run = self._determine_categories_to_run(args)
            if not categories_to_run:
                print("No categories to run based on selection criteria - SUCCESS (empty selection is valid)")
                return 0
            
            # Handle resume functionality
            if args.resume_from:
                categories_to_run = self._handle_resume(categories_to_run, args.resume_from)
            
            # Create execution plan
            self.execution_plan = self.category_system.create_execution_plan(
                categories_to_run,
                max_parallel=args.workers,
                skip_dependencies=getattr(args, 'no_dependencies', False)
            )
            
            # Start progress tracking
            if self.progress_tracker:
                run_id = f"run_{int(time.time())}"
                self.progress_tracker.start_run(
                    run_id=run_id,
                    categories=categories_to_run,
                    test_level="category",
                    parallel_workers=args.workers,
                    fail_fast=args.fast_fail,
                    real_llm=args.real_llm,
                    environment=args.env
                )
            
            # Show execution plan
            self._show_execution_plan(self.execution_plan, args)
            
            # Execute categories by phase
            results = self._execute_categories_by_phases(self.execution_plan, args)
            
            # Complete progress tracking
            if self.progress_tracker:
                success = all(r["success"] for r in results.values())
                self.progress_tracker.complete_run(success)
            
            # Generate report
            self._generate_report(results, args)
            
            # End test tracking session
            if self.test_tracker:
                session_summary = self.test_tracker.end_session(metadata={
                    "args": vars(args),
                    "execution_plan": self.execution_plan.to_dict() if self.execution_plan and hasattr(self.execution_plan, 'to_dict') else None
                })
                print(f"Session Summary: {session_summary['total_tests']} tests, "
                      f"{session_summary['passed']} passed, {session_summary['failed']} failed, "
                      f"Pass rate: {session_summary['pass_rate']:.1f}%")
                
                # Show test tracking report if verbose
                if args.verbose:
                    print("\n" + self.test_tracker.generate_report())
            
            # P0 FIX: Only consider requested categories for exit code, not dependencies
            # This prevents false failures when dependencies fail but requested categories pass
            if self.execution_plan and hasattr(self.execution_plan, 'requested_categories'):
                requested_results = {
                    cat: results[cat] for cat in self.execution_plan.requested_categories 
                    if cat in results
                }
                return 0 if all(r["success"] for r in requested_results.values()) else 1
            else:
                # Fallback to original behavior if execution plan doesn't have requested_categories
                # Handle empty results case - no categories found is considered success
                if not results:
                    return 0
                return 0 if all(r["success"] for r in results.values()) else 1
        
        finally:
            # CRITICAL: Always cleanup test environment after tests complete
            # This ensures cleanup runs even on failures or exceptions
            try:
                self.cleanup_test_environment()
            except Exception as e:
                print(f"[WARNING] Post-test cleanup failed: {e}")
    
    def _initialize_docker_environment(self, args, running_e2e: bool):
        """Initialize Docker environment - automatically starts services if needed."""
        # Skip Docker for staging (uses remote services)
        if self._detect_staging_environment(args):
            return
        
        # Skip Docker if explicitly disabled
        env = get_env()
        if env.get('TEST_NO_DOCKER', 'false').lower() == 'true':
            print("[INFO] Docker disabled via TEST_NO_DOCKER environment variable")
            return
        
        # Determine if Docker is actually needed based on test categories
        if not self._docker_required_for_tests(args, running_e2e):
            print("[INFO] Docker not required for selected test categories")
            print("[INFO] Skipping all Docker operations (initialization, health checks, service management)")
            return
            
        # First, try to use the simple Docker manager for automatic startup
        print("\n" + "="*60)
        print("DOCKER SERVICE INITIALIZATION")
        print("="*60)
        
        if not CENTRALIZED_DOCKER_AVAILABLE:
            return
        
        # Memory pre-flight check to prevent OOM kills
        try:
            from test_framework.memory_guardian import MemoryGuardian, TestProfile
            
            # Determine test profile based on categories
            if running_e2e or (args.categories and 'e2e' in args.categories):
                profile = TestProfile.FULL
            elif args.categories and 'performance' in args.categories:
                profile = TestProfile.PERFORMANCE
            elif args.categories and ('integration' in args.categories or 'api' in args.categories):
                profile = TestProfile.STANDARD
            else:
                profile = TestProfile.MINIMAL
            
            guardian = MemoryGuardian(profile)
            can_proceed, details = guardian.pre_flight_check()
            
            if not can_proceed:
                print("\n" + "="*60)
                print("\n" + "="*60)
                print("="*60)
                print(f"\n{details['message']}")
                print(f"\\nProfile: {profile.value}")
                print(f"\nProfile: {profile.value}")
                print(f"Available: {details['system_available_mb']:,} MB")
                
                if details.get('alternatives'):
                    print("\nAlternative profiles that could work:")
                    for alt in details['alternatives']:
                        print(f"  - {alt['profile']}: {alt['description']} ({alt['required_mb']}MB)")
                
                print("\nAlternative profiles that could work:")
                print("="*60 + "\n")
                
                # Check if we should skip the check
                if env.get('TEST_SKIP_MEMORY_CHECK', 'false').lower() != 'true':
                    raise MemoryError(f"Insufficient memory for {profile.value} tests")
                else:
                    print("[WARNING] Memory check failed but continuing due to TEST_SKIP_MEMORY_CHECK=true")
            else:
                print(f"[INFO] Memory check passed: {details['message']}")
                
        except ImportError:
            print("[WARNING] MemoryGuardian not available, skipping memory check")
        except Exception as e:
            print(f"[WARNING] Memory check failed with error: {e}")
        
        # Determine environment type - always default to DEDICATED for isolation
        # DEDICATED is now the default for all test types
        env_type = EnvironmentType.DEDICATED
        
        # Check if we should use production images
        use_production = env.get('TEST_USE_PRODUCTION_IMAGES', 'true').lower() == 'true'
        
        # Initialize centralized Docker manager with Alpine and rebuild defaults
        # Get options from command line or use defaults
        use_alpine = not (hasattr(args, 'no_alpine') and args.no_alpine)
        rebuild_images = not (hasattr(args, 'no_rebuild') and args.no_rebuild)
        rebuild_backend_only = not (hasattr(args, 'rebuild_all') and args.rebuild_all)
        
        # Check if we should use Podman or Docker
        container_runtime = os.environ.get('CONTAINER_RUNTIME', '').lower()
        
        if container_runtime == 'podman':
            # Use Podman with Docker compatibility wrapper
            from test_framework.podman_docker_compat import PodmanDockerCompatWrapper
            self.docker_manager = PodmanDockerCompatWrapper(
                environment_type=env_type,
                test_id=f"test_run_{int(time.time())}_{os.getpid()}",
                use_alpine=use_alpine
            )
            print("[INFO] Using Podman runtime for container management")
        else:
            # Use Docker (existing UnifiedDockerManager)
            self.docker_manager = UnifiedDockerManager(
                environment_type=env_type,
                test_id=f"test_run_{int(time.time())}_{os.getpid()}",
                use_production_images=use_production,
                use_alpine=use_alpine,
                rebuild_images=rebuild_images,
                rebuild_backend_only=rebuild_backend_only
            )
        
        print(f"[INFO] Using Docker environment: type={env_type.value}, alpine={use_alpine}, "
              f"rebuild={rebuild_images}, backend_only={rebuild_backend_only}, production={use_production}")
        
        # CRITICAL: Now that Docker manager is initialized, apply Windows encoding setup
        global _windows_encoding_setup_pending
        if _windows_encoding_setup_pending:
            try:
                setup_windows_encoding()
                _windows_encoding_setup_pending = False
                print("[INFO] Windows encoding setup completed after Docker initialization")
            except Exception as e:
                print(f"[WARNING] Windows encoding setup failed: {e}")
        
        # Acquire environment with locking
        try:
            if not self.docker_manager:
                print("[ERROR] Docker manager not initialized - this should not happen")
                return
                
            self.docker_environment, self.docker_ports = self.docker_manager.acquire_environment()
            print(f"[INFO] Acquired Docker environment: {self.docker_environment}")
            
            # Wait for services to be healthy
            if not self.docker_manager.wait_for_services(timeout=60):
                print("[WARNING] Some Docker services are unhealthy")
                
                if running_e2e or args.real_services:
                    # For E2E and real services, we need healthy services
                    print("[INFO] Attempting to fix unhealthy services...")
                    for service in ['backend', 'auth', 'postgres', 'redis']:
                        status = self.docker_manager.get_service_status(service)
                        if status != ServiceStatus.HEALTHY:
                            self.docker_manager.restart_service(service, force=False)
                    
                    # Wait again
                    if not self.docker_manager.wait_for_services(timeout=30):
                        print("\n" + "="*60)
                        print(" FAIL:  DOCKER SERVICES UNHEALTHY")
                        print("="*60)
                        print("\nSome services failed health checks. To fix:")
                        print("  1. python scripts/docker.py health       # Check service health")
                        print("  2. python scripts/docker.py restart      # Restart all services")
                        print("  3. python scripts/docker.py logs backend # Check logs for errors")
                        print("\n" + "="*60)
                        raise RuntimeError("Docker services not healthy for testing")
                        
        except Exception as e:
            # SSOT: Use UnifiedDockerManager's recovery mechanisms instead of manual scripts
            print(f"\n WARNING: [U+FE0F] Docker initialization encountered an issue: {str(e)}")
            print("\n CYCLE:  Attempting graceful recovery with exponential backoff...")
            
            # Try recovery with exponential backoff
            recovery_attempts = 3
            backoff_seconds = [2, 5, 10]  # Exponential backoff
            
            for attempt in range(recovery_attempts):
                print(f"\n  Attempt {attempt + 1}/{recovery_attempts}...")
                time.sleep(backoff_seconds[attempt])
                
                try:
                    # Check if containers exist but are unhealthy
                    if not self.docker_manager:
                        print("  Docker manager not available for container detection")
                        continue
                    existing_containers = self.docker_manager._detect_existing_dev_containers()
                    if existing_containers:
                        print(f"  Found {len(existing_containers)} existing containers")
                        
                        # Try to restart unhealthy services
                        print("  Attempting to restart unhealthy services...")
                        for service in existing_containers.keys():
                            try:
                                if self.docker_manager:
                                    self.docker_manager.restart_service(service)
                                else:
                                    print(f"    Warning: Docker manager not available to restart {service}")
                            except Exception as restart_err:
                                print(f"    Warning: Could not restart {service}: {restart_err}")
                        
                        # Wait for services with longer timeout
                        print(f"  Waiting up to {30 + attempt * 10}s for services to become healthy...")
                        if self.docker_manager and self.docker_manager.wait_for_services(timeout=30 + attempt * 10):
                            print("\n PASS:  Docker services recovered successfully!")
                            return  # Recovery successful
                    
                    # If no containers exist, try to start fresh
                    else:
                        print("  No existing containers found, attempting fresh start...")
                        
                        # Clean up any stale resources first
                        try:
                            if self.docker_manager:
                                self.docker_manager.cleanup_stale_resources()
                        except Exception:
                            pass  # Ignore cleanup errors
                        
                        # Try to start services again
                        if not self.docker_manager:
                            print("  Docker manager not available for service startup")
                            continue
                            
                        if env_type == "test":
                            # First try normal environment
                            success = self.docker_manager.start_test_environment(
                                use_alpine=use_alpine,
                                rebuild=rebuild_images
                            )
                            
                            # If that fails, try minimal environment as fallback
                            if not success:
                                print("\n CYCLE:  Attempting minimal test environment (infrastructure only)...")
                                success = self.docker_manager.start_test_environment(
                                    minimal_only=True
                                )
                        else:
                            success = self.docker_manager.start_dev_environment(
                                rebuild=rebuild_images
                            )
                        
                        if success:
                            print("\n PASS:  Docker services started successfully on retry!")
                            return  # Recovery successful
                            
                except Exception as recovery_err:
                    print(f"    Recovery attempt failed: {recovery_err}")
                    if attempt < recovery_attempts - 1:
                        print(f"    Will retry in {backoff_seconds[attempt + 1]} seconds...")
            
            # All recovery attempts failed
            print("\n" + "="*60)
            print(" FAIL:  DOCKER RECOVERY FAILED")
            print("="*60)
            
            # Provide diagnostic information
            print("\n CHART:  Diagnostic Information:")
            try:
                # Check Docker daemon status
                daemon_check = subprocess.run(
                    ["docker", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if daemon_check.returncode != 0:
                    print("   FAIL:  Docker daemon is not running or not accessible")
                    print("     Please ensure Docker Desktop is running")
                else:
                    print("   PASS:  Docker daemon is running")
                    
                    # Check for port conflicts
                    port_conflicts = self._check_port_conflicts()
                    if port_conflicts:
                        print(f"   WARNING: [U+FE0F] Port conflicts detected: {port_conflicts}")
                        print("     Another application may be using required ports")
                    
                    # Check Docker resources
                    resource_check = subprocess.run(
                        ["docker", "system", "df"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if "100%" in resource_check.stdout:
                        print("   WARNING: [U+FE0F] Docker disk space may be full")
                        print("     Run: docker system prune -a")
                        
            except Exception:
                pass  # Ignore diagnostic errors
            
            print("\n[U+1F527] Manual Recovery Options:")
            print("  1. Restart Docker Desktop")
            print("  2. Clean Docker resources: docker system prune -a")
            print("  3. Check for port conflicts on 5432, 6379, 8000, 8081")
            print("  4. Review logs: docker-compose logs")
            
            if running_e2e or args.real_services:
                raise RuntimeError(f"Docker services required but could not be started after {recovery_attempts} attempts")  # Re-raise for E2E/real service testing
                
            # Fall back to port discovery for non-critical tests
            self.docker_manager = None
            self.docker_environment = None
            self.docker_ports = None
            print("\n[WARNING] Continuing without Docker management for non-critical tests")
            print("[INFO] Tests will attempt to use any existing services if available")
    

    def _check_port_conflicts(self) -> List[int]:
        """Check for port conflicts on required ports."""
        import socket
        conflicted_ports = []
        required_ports = {
            "postgres": [5432, 5434],
            "redis": [6379, 6381],
            "backend": [8000],
            "auth": [8081]
        }
        
        for service, ports in required_ports.items():
            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        # Port is in use, check if it's our container
                        check_cmd = subprocess.run(
                            ["docker", "ps", "--filter", f"publish={port}", "--format", "{{.Names}}"],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if check_cmd.returncode == 0 and check_cmd.stdout.strip():
                            # It's a Docker container, likely ours
                            continue
                        else:
                            # Port is used by something else
                            conflicted_ports.append(port)
                except Exception:
                    pass
                finally:
                    sock.close()
        
        return conflicted_ports
    
    def cleanup_test_environment(self):
        """Comprehensive cleanup of test environment to prevent Docker resource accumulation.
        
        This function:
        - Stops test containers with docker-compose down --volumes --remove-orphans
        - Removes orphaned containers with name pattern "test-"
        - Removes orphaned networks with name pattern "netra-test-"
        - Logs all cleanup actions
        """
        # Skip cleanup if Docker was not initialized
        if not hasattr(self, 'docker_manager') or self.docker_manager is None:
            print("[INFO] Skipping Docker cleanup - Docker was not initialized")
            return
        
        print("[INFO] Starting comprehensive test environment cleanup...")
        
        try:
            # 1. Docker Compose cleanup with volumes and orphans
            compose_files = [
                self.project_root / "docker-compose.alpine-test.yml",
                self.project_root / "docker-compose.yml"
            ]
            
            for compose_file in compose_files:
                if compose_file.exists():
                    print(f"[INFO] Cleaning up docker-compose from {compose_file}")
                    try:
                        result = subprocess.run([
                            "docker-compose", "-f", str(compose_file),
                            "down", "--volumes", "--remove-orphans"
                        ], capture_output=True, text=True, timeout=60)
                        
                        if result.returncode == 0:
                            print(f"[INFO] Successfully cleaned up compose from {compose_file.name}")
                        else:
                            print(f"[WARNING] Compose cleanup from {compose_file.name} returned code {result.returncode}: {result.stderr}")
                    except subprocess.TimeoutExpired:
                        print(f"[WARNING] Timeout cleaning up compose from {compose_file.name}")
                    except Exception as e:
                        print(f"[WARNING] Error cleaning up compose from {compose_file.name}: {e}")
            
            # 2. Remove orphaned test containers
            try:
                print("[INFO] Removing orphaned test containers...")
                result = subprocess.run([
                    "docker", "ps", "-aq", "--filter", "name=test-"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    container_ids = result.stdout.strip().split('\n')
                    print(f"[INFO] Found {len(container_ids)} test containers to remove")
                    
                    # Remove containers
                    remove_result = subprocess.run([
                        "docker", "rm", "-f"
                    ] + container_ids, capture_output=True, text=True, timeout=60)
                    
                    if remove_result.returncode == 0:
                        print(f"[INFO] Successfully removed {len(container_ids)} test containers")
                    else:
                        print(f"[WARNING] Failed to remove some test containers: {remove_result.stderr}")
                else:
                    print("[INFO] No orphaned test containers found")
                    
            except subprocess.TimeoutExpired:
                print("[WARNING] Timeout removing orphaned test containers")
            except Exception as e:
                print(f"[WARNING] Error removing orphaned test containers: {e}")
            
            # 3. Remove orphaned test networks
            try:
                print("[INFO] Removing orphaned test networks...")
                result = subprocess.run([
                    "docker", "network", "ls", "--filter", "name=netra-test-", "-q"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    network_ids = result.stdout.strip().split('\n')
                    print(f"[INFO] Found {len(network_ids)} test networks to remove")
                    
                    # Remove networks
                    for network_id in network_ids:
                        try:
                            remove_result = subprocess.run([
                                "docker", "network", "rm", network_id
                            ], capture_output=True, text=True, timeout=30)
                            
                            if remove_result.returncode == 0:
                                print(f"[INFO] Removed test network {network_id[:12]}")
                            else:
                                print(f"[WARNING] Failed to remove network {network_id[:12]}: {remove_result.stderr}")
                        except Exception as e:
                            print(f"[WARNING] Error removing network {network_id[:12]}: {e}")
                else:
                    print("[INFO] No orphaned test networks found")
                    
            except subprocess.TimeoutExpired:
                print("[WARNING] Timeout removing orphaned test networks")
            except Exception as e:
                print(f"[WARNING] Error removing orphaned test networks: {e}")
            
            # 4. Clean up dangling volumes (test-specific)
            try:
                print("[INFO] Removing dangling test volumes...")
                result = subprocess.run([
                    "docker", "volume", "ls", "-f", "dangling=true", "--filter", "name=test", "-q"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    volume_names = result.stdout.strip().split('\n')
                    print(f"[INFO] Found {len(volume_names)} dangling test volumes to remove")
                    
                    # Remove volumes
                    remove_result = subprocess.run([
                        "docker", "volume", "rm"
                    ] + volume_names, capture_output=True, text=True, timeout=60)
                    
                    if remove_result.returncode == 0:
                        print(f"[INFO] Successfully removed {len(volume_names)} dangling test volumes")
                    else:
                        print(f"[WARNING] Failed to remove some dangling volumes: {remove_result.stderr}")
                else:
                    print("[INFO] No dangling test volumes found")
                    
            except subprocess.TimeoutExpired:
                print("[WARNING] Timeout removing dangling test volumes")
            except Exception as e:
                print(f"[WARNING] Error removing dangling test volumes: {e}")
            
            print("[INFO] Comprehensive test environment cleanup completed")
            
        except Exception as e:
            print(f"[ERROR] Critical error during test environment cleanup: {e}")
    
    def _cleanup_docker_environment(self):
        """Clean up Docker environment (legacy method - calls comprehensive cleanup)."""
        # First do the comprehensive cleanup
        self.cleanup_test_environment()
        
        # Clean up E2E Docker environment if it was set up
        if hasattr(self, 'e2e_docker_helper') and self.e2e_docker_helper:
            try:
                print("[INFO] Cleaning up E2E Docker environment...")
                import asyncio
                
                # Run async cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.e2e_docker_helper.teardown_e2e_environment())
                    print("[SUCCESS] E2E Docker environment cleaned up")
                finally:
                    loop.close()
                    
            except Exception as e:
                print(f"[WARNING] Error cleaning up E2E Docker environment: {e}")
            finally:
                # Clean up reference
                self.e2e_docker_helper = None
        
        # Then do the original manager-specific cleanup
        if self.docker_manager and self.docker_environment:
            try:
                print(f"[INFO] Releasing Docker environment: {self.docker_environment}")
                self.docker_manager.release_environment(self.docker_environment)
                
                # Print statistics
                stats = self.docker_manager.get_statistics()
                print(f"[INFO] Docker statistics: {json.dumps(stats, indent=2)}")
            except Exception as e:
                print(f"[WARNING] Error releasing Docker environment: {e}")
    
    def _configure_environment(self, args: argparse.Namespace):
        """Configure test environment based on arguments."""
        # Load test environment secrets first to prevent validation errors
        self._load_test_environment_secrets()
        
        # Determine categories to run early to check for E2E categories
        categories_to_run = self._determine_categories_to_run(args)
        
        # Check if running E2E categories - if so, enable real LLM by default per CLAUDE.md
        e2e_categories = {'e2e', 'e2e_critical', 'cypress'}
        running_e2e = bool(set(categories_to_run) & e2e_categories)
        
        # Auto-configure E2E bypass key for staging environment
        if self._detect_staging_environment(args) and running_e2e:
            self._configure_staging_e2e_auth()
        
        # Real LLM should be enabled if:
        # 1. Explicitly requested with --real-llm flag
        # 2. Running E2E categories (real LLM is DEFAULT per CLAUDE.md)
        # 3. Running in dev/staging environments (no mocks allowed per CLAUDE.md)
        use_real_llm = args.real_llm or running_e2e or args.env in ['dev', 'staging']
        
        # Configure LLM testing with proper environment variables
        if use_real_llm:
            # Set primary control variable (NETRA_REAL_LLM_ENABLED)
            env = get_env()
            env.set('NETRA_REAL_LLM_ENABLED', 'true', 'test_runner_llm')
            
            # Set all legacy variables for backward compatibility
            env.set('ENABLE_REAL_LLM_TESTING', 'true', 'test_runner_llm')
            env.set('USE_REAL_LLM', 'true', 'test_runner_llm')
            env.set('TEST_USE_REAL_LLM', 'true', 'test_runner_llm')
            env.set('TEST_LLM_MODE', 'real', 'test_runner_llm')
            
            # Configure LLM testing framework
            configure_llm_testing(
                mode=LLMTestMode.REAL,
                model="gemini-2.5-pro",
                timeout=60,
                parallel="auto",
                use_dedicated_env=True
            )
        else:
            # Only allow mock mode for unit tests in test environment per CLAUDE.md
            if args.env == 'test' and not running_e2e:
                env = get_env()
                env.set('NETRA_REAL_LLM_ENABLED', 'false', 'test_runner_llm')
                env.set('ENABLE_REAL_LLM_TESTING', 'false', 'test_runner_llm')
                env.set('USE_REAL_LLM', 'false', 'test_runner_llm')
                env.set('TEST_USE_REAL_LLM', 'false', 'test_runner_llm')
                env.set('TEST_LLM_MODE', 'mock', 'test_runner_llm')
                configure_llm_testing(mode=LLMTestMode.MOCK)
            else:
                # Force real LLM for non-unit tests - mocks forbidden per CLAUDE.md
                use_real_llm = True
                env = get_env()
                env.set('NETRA_REAL_LLM_ENABLED', 'true', 'test_runner_llm')
                env.set('ENABLE_REAL_LLM_TESTING', 'true', 'test_runner_llm')
                env.set('USE_REAL_LLM', 'true', 'test_runner_llm')
                env.set('TEST_USE_REAL_LLM', 'true', 'test_runner_llm')
                env.set('TEST_LLM_MODE', 'real', 'test_runner_llm')
                configure_llm_testing(
                    mode=LLMTestMode.REAL,
                    model="gemini-2.5-pro",
                    timeout=60,
                    parallel="auto",
                    use_dedicated_env=True
                )
        
        # Initialize Docker environment first (if needed)
        self._initialize_docker_environment(args, running_e2e)
        
        # Configure services
        if self._detect_staging_environment(args):
            # For staging, don't use Docker port discovery - use remote staging services
            # Configure test environment with discovered ports
            env = get_env()
            # CRITICAL: Enable local config file loading for all staging tests
            # This allows staging.env to be loaded for ClickHouse and other configurations
            env.set('ENABLE_LOCAL_CONFIG_FILES', 'true', 'staging_config')
            env.set('ENVIRONMENT', 'staging', 'staging_config')
            env.set('NETRA_ENVIRONMENT', 'staging', 'staging_config')
            env.set('TEST_ENV', 'staging', 'staging_config')  # Required by environment_markers.py
            if self.docker_ports:
                # Set discovered PostgreSQL URL
                postgres_port = self.docker_ports.get('postgres', 5434)
                env.set('TEST_POSTGRES_PORT', str(postgres_port), 'docker_manager')
                env.set('DATABASE_URL', f'postgresql://test:test@localhost:{postgres_port}/netra_test', 'docker_manager')
                
                # Set discovered Redis URL
                redis_port = self.docker_ports.get('redis', 6381)
                env.set('TEST_REDIS_PORT', str(redis_port), 'docker_manager')
                env.set('REDIS_URL', f'redis://localhost:{redis_port}/0', 'docker_manager')
                
                logger.info(f"Configured test environment with dynamic ports - Postgres: {postgres_port}, Redis: {redis_port}")
            env = get_env()
            env.set('USE_REAL_SERVICES', 'true', 'test_runner')
            # Import SSOT for staging URLs
            from netra_backend.app.core.network_constants import URLConstants
            # Set staging service URLs from SSOT
            env.set('BACKEND_URL', URLConstants.STAGING_BACKEND_URL, 'test_runner')
            env.set('AUTH_SERVICE_URL', URLConstants.STAGING_AUTH_URL, 'test_runner')
            env.set('WEBSOCKET_URL', URLConstants.STAGING_WEBSOCKET_URL, 'test_runner')
            self.port_discovery = None  # No port discovery for staging
        elif args.env == "dev":
            configure_dev_environment()
            # Use DEV services for dev environment
            self.port_discovery = DockerPortDiscovery(use_test_services=False)
            env = get_env()
            env.set('USE_REAL_SERVICES', 'true', 'test_runner')
            env.set('BACKEND_URL', env.get('BACKEND_URL', 'http://localhost:8000'), 'test_runner')
            env.set('AUTH_SERVICE_URL', env.get('AUTH_SERVICE_URL', 'http://localhost:8081'), 'test_runner')
            env.set('WEBSOCKET_URL', env.get('WEBSOCKET_URL', 'ws://localhost:8000'), 'test_runner')
        elif args.real_services or running_e2e:
            # Configure test environment with discovered ports
            env = get_env()
            
            # CRITICAL: Enable E2E tests execution when running e2e category
            # Without this, all e2e tests are skipped per conftest_e2e.py
            if running_e2e:
                env.set('RUN_E2E_TESTS', 'true', 'test_runner')
                logger.info("Enabled E2E tests execution (RUN_E2E_TESTS=true)")
            if self.docker_ports:
                # Set discovered PostgreSQL URL
                postgres_port = self.docker_ports.get('postgres', 5434)
                env.set('TEST_POSTGRES_PORT', str(postgres_port), 'docker_manager')
                env.set('DATABASE_URL', f'postgresql://test:test@localhost:{postgres_port}/netra_test', 'docker_manager')
                
                # Set discovered Redis URL
                redis_port = self.docker_ports.get('redis', 6381)
                env.set('TEST_REDIS_PORT', str(redis_port), 'docker_manager')
                env.set('REDIS_URL', f'redis://localhost:{redis_port}/0', 'docker_manager')
                
                logger.info(f"Configured test environment with dynamic ports - Postgres: {postgres_port}, Redis: {redis_port}")
            # Use appropriate services based on environment
            # For dev environment, use dev services; for test environment, use test services
            use_test_services = (args.env != 'dev')
            self.port_discovery = DockerPortDiscovery(use_test_services=use_test_services)
            env = get_env()
            env.set('USE_REAL_SERVICES', 'true', 'test_runner')
            # Use test-specific ports
            env.set('BACKEND_URL', env.get('BACKEND_URL', 'http://localhost:8001'), 'test_runner')
            env.set('AUTH_SERVICE_URL', env.get('AUTH_SERVICE_URL', 'http://localhost:8082'), 'test_runner')
            env.set('WEBSOCKET_URL', env.get('WEBSOCKET_URL', 'ws://localhost:8001'), 'test_runner')
        else:
            # Only allow mock environment for pure unit tests in test environment
            configure_mock_environment()
            # Create port discovery even for mock environment to enable port discovery if Docker is available
            self.port_discovery = DockerPortDiscovery(use_test_services=True)
        
        # Update service URLs with centralized Docker manager ports (if available)
        if CENTRALIZED_DOCKER_AVAILABLE and self.docker_manager and self.docker_ports and args.env != 'staging':
            env = get_env()
            
            # Update PostgreSQL DATABASE_URL
            if 'postgres' in self.docker_ports:
                postgres_port = self.docker_ports['postgres']
                
                # Construct #removed-legacywith discovered port and correct user/password for each environment
                if args.env == "dev":
                    # Dev environment uses "netra" user with password "netra123"
                    discovered_db_url = f"postgresql://netra:netra123@localhost:{postgres_port}/netra_dev"
                else:
                    # Test environment uses "test_user" user with password "test_pass" (from docker-compose.test.yml)
                    discovered_db_url = f"postgresql://test_user:test_pass@localhost:{postgres_port}/netra_test"
                    
                env.set('DATABASE_URL', discovered_db_url, 'docker_manager')
                print(f"[INFO] Updated #removed-legacywith Docker port: {postgres_port}")
            
            # Update Redis URL
            if 'redis' in self.docker_ports:
                redis_port = self.docker_ports['redis']
                
                if args.env == "dev":
                    discovered_redis_url = f"redis://localhost:{redis_port}"
                else:
                    discovered_redis_url = f"redis://localhost:{redis_port}/1"  # Use DB 1 for tests
                    
                env.set('REDIS_URL', discovered_redis_url, 'docker_manager')
                print(f"[INFO] Updated REDIS_URL with Docker port: {redis_port}")
            
            # Update ClickHouse URL
            if 'clickhouse' in self.docker_ports:
                clickhouse_port = self.docker_ports['clickhouse']
                # Use appropriate credentials based on environment
                if args.env == 'test' or args.env == 'testing':
                    clickhouse_user = 'test'
                    clickhouse_password = 'test'
                    clickhouse_db = 'netra_test_analytics'
                    clickhouse_native_port = '9002'  # Test native port
                else:  # development environment
                    clickhouse_user = 'netra'
                    clickhouse_password = 'netra123'
                    clickhouse_db = 'netra_analytics'
                    clickhouse_native_port = '9001'  # Dev native port
                
                discovered_clickhouse_url = f"clickhouse://{clickhouse_user}:{clickhouse_password}@localhost:{clickhouse_port}/{clickhouse_db}"
                env.set('CLICKHOUSE_URL', discovered_clickhouse_url, 'docker_manager')
                env.set('CLICKHOUSE_HTTP_PORT', str(clickhouse_port), 'docker_manager')
                env.set('CLICKHOUSE_NATIVE_PORT', clickhouse_native_port, 'docker_manager')
                env.set('CLICKHOUSE_USER', clickhouse_user, 'docker_manager')
                env.set('CLICKHOUSE_PASSWORD', clickhouse_password, 'docker_manager')
                env.set('CLICKHOUSE_DB', clickhouse_db, 'docker_manager')
                print(f"[INFO] Updated ClickHouse configuration with Docker port: {clickhouse_port} (native: {clickhouse_native_port})")
            
            # Update backend/auth/websocket URLs
            if 'backend' in self.docker_ports:
                backend_port = self.docker_ports['backend']
                env.set('BACKEND_URL', f'http://localhost:{backend_port}', 'docker_manager')
                env.set('WEBSOCKET_URL', f'ws://localhost:{backend_port}', 'docker_manager')
                print(f"[INFO] Updated BACKEND_URL with Docker port: {backend_port}")
            
            if 'auth' in self.docker_ports:
                auth_port = self.docker_ports['auth']
                env.set('AUTH_SERVICE_URL', f'http://localhost:{auth_port}', 'docker_manager')
                print(f"[INFO] Updated AUTH_SERVICE_URL with Docker port: {auth_port}")
        # Fallback to old port discovery for backward compatibility
        elif hasattr(self, 'port_discovery') and self.port_discovery and args.env != 'staging':
            port_mappings = self.port_discovery.discover_all_ports()
            env = get_env()
            
            # Update PostgreSQL DATABASE_URL
            if 'postgres' in port_mappings and port_mappings['postgres'].is_available:
                postgres_port = port_mappings['postgres'].external_port
                
                # Construct #removed-legacywith discovered port and correct user/password for each environment
                if args.env == "dev":
                    # Dev environment uses "netra" user with password "netra123"
                    discovered_db_url = f"postgresql://netra:netra123@localhost:{postgres_port}/netra_dev"
                else:
                    # Test environment uses "test_user" user with password "test_pass" (from docker-compose.test.yml)
                    discovered_db_url = f"postgresql://test_user:test_pass@localhost:{postgres_port}/netra_test"
                    
                env.set('DATABASE_URL', discovered_db_url, 'test_runner_port_discovery')
                print(f"[INFO] Updated #removed-legacywith discovered PostgreSQL port: {postgres_port}")
            else:
                print(f"[WARNING] PostgreSQL service not found via port discovery, using configured defaults")
            
            # Update Redis URL
            if 'redis' in port_mappings and port_mappings['redis'].is_available:
                redis_port = port_mappings['redis'].external_port
                
                if args.env == "dev":
                    discovered_redis_url = f"redis://localhost:{redis_port}"
                else:
                    discovered_redis_url = f"redis://localhost:{redis_port}/1"  # Use DB 1 for tests
                    
                env.set('REDIS_URL', discovered_redis_url, 'test_runner_port_discovery')
                print(f"[INFO] Updated REDIS_URL with discovered Redis port: {redis_port}")
            
            # Update ClickHouse URL
            if 'clickhouse' in port_mappings and port_mappings['clickhouse'].is_available:
                clickhouse_port = port_mappings['clickhouse'].external_port
                # Use appropriate credentials based on environment
                if args.env == 'test' or args.env == 'testing':
                    clickhouse_user = 'test'
                    clickhouse_password = 'test'
                    clickhouse_db = 'netra_test_analytics'
                    clickhouse_native_port = '9002'  # Test native port
                else:  # development environment
                    clickhouse_user = 'netra'
                    clickhouse_password = 'netra123'
                    clickhouse_db = 'netra_analytics'
                    clickhouse_native_port = '9001'  # Dev native port
                
                discovered_clickhouse_url = f"clickhouse://{clickhouse_user}:{clickhouse_password}@localhost:{clickhouse_port}/{clickhouse_db}"
                env.set('CLICKHOUSE_URL', discovered_clickhouse_url, 'test_runner_port_discovery')
                env.set('CLICKHOUSE_HTTP_PORT', str(clickhouse_port), 'test_runner_port_discovery')
                env.set('CLICKHOUSE_NATIVE_PORT', clickhouse_native_port, 'test_runner_port_discovery')
                env.set('CLICKHOUSE_USER', clickhouse_user, 'test_runner_port_discovery')
                env.set('CLICKHOUSE_PASSWORD', clickhouse_password, 'test_runner_port_discovery')
                env.set('CLICKHOUSE_DB', clickhouse_db, 'test_runner_port_discovery')
                print(f"[INFO] Updated ClickHouse configuration with discovered port: {clickhouse_port} (native: {clickhouse_native_port})")
        
        # Set environment variables using IsolatedEnvironment
        env = get_env()
        env.set("TEST_ENV", args.env, "test_runner")
        
        # Log LLM configuration for debugging
        print(f"[INFO] LLM Configuration: real_llm={use_real_llm}, running_e2e={running_e2e}, env={args.env}")
        
        if args.no_coverage:
            env.set("COVERAGE_ENABLED", "false", "test_runner")
    
    def _load_test_environment_secrets(self):
        """Load test environment secrets to prevent validation errors during testing."""
        # Set essential test environment variables
        test_env_vars = {
            'ENVIRONMENT': 'testing',
            'TESTING': '1',
            'GOOGLE_CLIENT_ID': 'test-google-client-id-for-integration-testing',
            'GOOGLE_CLIENT_SECRET': 'test-google-client-secret-for-integration-testing',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-integration-testing-must-be-32-chars-minimum',
            'SERVICE_SECRET': 'test-service-secret-for-cross-service-auth-32-chars-minimum-length',
            'FERNET_KEY': 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=',
            'CLICKHOUSE_PASSWORD': 'test-clickhouse-password-for-integration-testing'
        }
        
        # Only set if not already present (don't override existing values)
        env = get_env()
        for key, value in test_env_vars.items():
            if not env.get(key):
                env.set(key, value, "test_runner_secrets")
        
        # Try to load .env.mock file (or legacy .env.test) if it exists
        test_env_file = self.project_root / ".env.mock"
        if not test_env_file.exists():
            test_env_file = self.project_root / ".env.test"  # Legacy fallback
        if test_env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(test_env_file, override=False)
            except ImportError:
                # dotenv not available, use manual loading
                pass
            except Exception as e:
                print(f"Warning: Could not load {test_env_file.name} file: {e}")
    
    def _configure_staging_e2e_auth(self):
        """Automatically configure E2E bypass key for staging environment."""
        try:
            env = get_env()
            
            # Check if E2E_OAUTH_SIMULATION_KEY is already set
            if env.get('E2E_OAUTH_SIMULATION_KEY'):
                print("[INFO] E2E_OAUTH_SIMULATION_KEY already configured")
                return
            
            print("[INFO] Auto-configuring E2E bypass key for staging...")
            
            # Try to fetch the bypass key from Google Secrets Manager
            import subprocess
            result = subprocess.run(
                ['gcloud', 'secrets', 'versions', 'access', 'latest', 
                 '--secret=e2e-bypass-key', '--project=netra-staging'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                bypass_key = result.stdout.strip()
                env.set('E2E_OAUTH_SIMULATION_KEY', bypass_key, 'staging_e2e_auth')
                env.set('ENVIRONMENT', 'staging', 'staging_e2e_auth')
                env.set('NETRA_ENVIRONMENT', 'staging', 'staging_e2e_auth')
                env.set('TEST_ENV', 'staging', 'staging_e2e_auth')  # Required by environment_markers.py
                env.set('STAGING_AUTH_URL', 'https://api.staging.netrasystems.ai', 'staging_e2e_auth')
                # CRITICAL: Enable local config file loading for staging tests
                env.set('ENABLE_LOCAL_CONFIG_FILES', 'true', 'staging_e2e_auth')
                print("[INFO]  PASS:  E2E bypass key and staging config loading configured successfully")
            else:
                print(f"[WARNING] Could not fetch E2E bypass key from Google Secrets Manager: {result.stderr}")
                print("[WARNING] E2E tests requiring authentication may fail")
                
        except Exception as e:
            print(f"[WARNING] Failed to configure E2E bypass key: {e}")
            print("[WARNING] E2E tests requiring authentication may fail")
    
    def _check_service_availability(self, args: argparse.Namespace):
        """Check availability of required real services before running tests."""
        
        # Skip service availability check for tests that specifically test service startup/resilience
        test_pattern = getattr(args, 'pattern', '') or ''
        if 'dev_launcher_critical_path' in test_pattern or 'startup' in test_pattern:
            print("[INFO] Skipping service availability check for dev launcher/startup resilience test")
            return
            
        print("Checking real service availability...")
        
        # Determine categories to check for LLM requirements
        categories_to_run = self._determine_categories_to_run(args)
        e2e_categories = {'e2e', 'e2e_critical', 'cypress'}
        running_e2e = bool(set(categories_to_run) & e2e_categories)
        
        # Determine which services to check based on arguments and environment
        required_services = []
        
        # Per CLAUDE.md - real services are required for dev/staging and E2E
        # But for staging environment, skip local service checks (use remote staging services)
        if args.real_services or args.env in ['dev'] or (running_e2e and args.env != 'staging'):
            required_services.extend(['postgresql', 'redis'])
            # Add clickhouse if available in docker ports
            if hasattr(self, 'docker_ports') and self.docker_ports and 'clickhouse' in self.docker_ports:
                required_services.append('clickhouse')
        elif self._detect_staging_environment(args):
            print("[INFO] Staging environment: using remote staging services, skipping local service checks")
            
        # Per CLAUDE.md - real LLM is required for E2E and dev/staging
        if args.real_llm or running_e2e or args.env in ['dev', 'staging']:
            required_services.append('llm')
            
        # Check Docker availability for containerized services, but skip for staging with --no-docker
        if args.env in ['dev'] or (running_e2e and args.env != 'staging'):
            # Try to detect if Docker is available and running
            try:
                import subprocess
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    required_services.append('docker')
            except (subprocess.SubprocessError, FileNotFoundError):
                print("[WARNING] Docker not available - tests may fail if they require containerized services")
        elif self._detect_staging_environment(args):
            print("[INFO] Staging environment: using remote staging services, Docker check skipped")
        
        if not required_services:
            return
        
        # Remove duplicates while preserving order
        required_services = list(dict.fromkeys(required_services))
        
        try:
            # Check services with appropriate timeout
            timeout = 10.0 if self._detect_staging_environment(args) else 5.0
            require_real_services(
                services=required_services,
                timeout=timeout
            )
            print(f"[OK] All required services are available: {', '.join(required_services)}")
            
        except ServiceUnavailableError as e:
            print(f"\n[FAIL] SERVICE AVAILABILITY CHECK FAILED\n")
            print(str(e))
            print(f"\nTIP: For mock testing, remove --real-services or --real-llm flags")
            print(f"TIP: For quick development setup, run: python scripts/dev_launcher.py")
            print(f"TIP: To use Alpine-based services: docker-compose -f docker-compose.alpine-test.yml up -d\n")
            
            # Exit immediately - don't waste time on tests that will fail
            import sys
            sys.exit(1)
        
        except Exception as e:
            print(f" WARNING: [U+FE0F]  Unexpected error during service availability check: {e}")
            print("Continuing with tests, but failures may occur if services are unavailable...")
    
    def _docker_required_for_tests(self, args: argparse.Namespace, running_e2e: bool) -> bool:
        """Determine if Docker is required for the selected test categories.
        
        Returns True if Docker is needed, False if tests can run without Docker.
        """
        # Skip Docker if explicitly disabled via command line (highest priority)
        if hasattr(args, 'no_docker') and args.no_docker:
            print("[INFO] Docker explicitly disabled via --no-docker flag")
            # Special handling for staging environment with --prefer-staging
            if self._detect_staging_environment(args) and hasattr(args, 'prefer_staging') and args.prefer_staging:
                print("[INFO] Staging environment with --prefer-staging: using remote services instead of Docker")
                return False
            # Special handling for staging environment  
            elif self._detect_staging_environment(args):
                print("[INFO] Staging environment: using remote staging services instead of Docker")
                return False
            # For other environments with --no-docker, truly disable Docker
            return False
        
        # Always require Docker if explicitly requested (but --no-docker overrides this above)
        if args.real_services:
            return True
        
        # E2E tests need Docker UNLESS running in staging with remote services
        if running_e2e:
            if self._detect_staging_environment(args):
                print("[INFO] E2E tests in staging environment: using remote staging services")
                return False
            return True
        
        # Dev environments need Docker, staging can use remote services per Issue #548 fix
        if args.env == 'dev':
            return True
        elif self._detect_staging_environment(args):
            print("[INFO] Staging environment: using remote staging services, Docker not required")
            return False
        
        # Get categories to run
        categories_to_run = self._determine_categories_to_run(args)
        
        # Categories that require Docker/real services
        docker_required_categories = {
            'e2e', 'e2e_critical', 'cypress',  # E2E tests
            'database',  # Database tests need PostgreSQL
            'api',  # API tests typically need backend services
            'websocket',  # WebSocket tests need backend
            'post_deployment',  # Post-deployment tests need services
            'deployment_critical',  # Cloud Run deployment tests need real services - P0 Issue #146
        }
        
        # Categories that DON'T require Docker
        docker_optional_categories = {
            'smoke',  # Quick validation tests
            'unit',  # Unit tests should be isolated
            'frontend',  # Frontend component tests can run without backend
            'agent',  # Agent tests can use mock LLM if needed
            'performance',  # Performance tests can run on mock data
            'security',  # Security tests can run on static analysis
            'startup',  # Startup tests are about service initialization
        }
        
        # Categories that can be mixed (some need services, some don't)
        docker_conditional_categories = {
            'integration',  # Some integration tests need services, some can run standalone
        }
        
        # Check if any of the selected categories require Docker
        for category in categories_to_run:
            if category in docker_required_categories:
                print(f"[INFO] Docker required for category: {category}")
                return True
        
        # Handle conditional categories (like integration) when --no-docker is specified
        has_conditional_categories = any(cat in docker_conditional_categories for cat in categories_to_run)
        if has_conditional_categories and hasattr(args, 'no_docker') and args.no_docker:
            print(f"[INFO] Conditional categories {[cat for cat in categories_to_run if cat in docker_conditional_categories]} running in --no-docker mode - will skip service-dependent tests")
            # Return False to skip Docker, tests will individually skip based on service availability
            return False
        
        # If only running categories that don't need Docker, skip it
        if all(cat in docker_optional_categories for cat in categories_to_run if cat):
            print(f"[INFO] Running only Docker-optional categories: {categories_to_run}")
            return False
        
        # Check for specific test patterns that indicate Docker is not needed
        test_pattern = getattr(args, 'pattern', '') or ''
        if test_pattern:
            # Unit test patterns
            if any(pattern in test_pattern for pattern in ['test_unit', 'unit_test', '/unit/', '_unit_']):
                print(f"[INFO] Unit test pattern detected, Docker not required: {test_pattern}")
                return False
            # Mock test patterns
            if any(pattern in test_pattern for pattern in ['mock', 'fake', 'stub']):
                print(f"[INFO] Mock test pattern detected, Docker not required: {test_pattern}")
                return False
        
        # If we have conditional categories but no --no-docker flag, require Docker
        if has_conditional_categories:
            print(f"[INFO] Docker required for conditional categories: {[cat for cat in categories_to_run if cat in docker_conditional_categories]}")
            return True
        
        # Default to requiring Docker for safety if we can't determine
        print(f"[INFO] Unable to determine Docker requirement, defaulting to required for categories: {categories_to_run}")
        return True
    
    def _determine_categories_to_run(self, args: argparse.Namespace) -> List[str]:
        """Determine which categories to run based on arguments."""
        categories = []
        
        # Handle service-specific selection (legacy compatibility)
        if hasattr(args, 'service') and args.service:
            categories.extend(self._get_categories_for_service(args.service))
        
        # Handle specific category selection
        if args.category:
            categories.append(args.category)
        
        if args.categories:
            categories.extend(args.categories)
        
        # Default to categories marked as default in tracker
        if not categories:
            if self.test_tracker:
                categories = self.test_tracker.get_default_categories()
            else:
                # Fallback defaults: quick tests that should usually pass
                categories = ["smoke", "unit", "integration"]
        
        # Filter categories that exist in the system
        valid_categories = [cat for cat in categories if cat in self.category_system.categories]
        if valid_categories != categories:
            missing = set(categories) - set(valid_categories)
            if missing:
                print(f"Warning: Categories not found: {missing}")
        
        return valid_categories
    
    def _get_categories_for_service(self, service: str) -> List[str]:
        """Get categories relevant to a specific service (legacy compatibility)."""
        service_category_mapping = {
            "backend": ["unit", "integration", "api", "database", "agent", "websocket", "security", "deployment_critical"],
            "frontend": ["unit", "integration", "e2e", "cypress", "performance"],
            "auth": ["unit", "integration", "auth", "security"],
            "auth_service": ["unit", "integration", "auth", "security"],
            "all": ["smoke", "unit", "integration", "api", "e2e", "database", "agent", "websocket", "security", "deployment_critical"]
        }
        
        categories = service_category_mapping.get(service, ["unit", "integration"])
        print(f"[LEGACY SERVICE MODE] Service '{service}' mapped to categories: {', '.join(categories)}")
        print("[DEPRECATION WARNING] --service flag is deprecated. Use --category or --categories instead.")
        return categories
    
    def _handle_resume(self, categories: List[str], resume_from: str) -> List[str]:
        """Handle resume functionality by skipping already completed categories."""
        if resume_from not in categories:
            print(f"Warning: Resume category '{resume_from}' not in execution list")
            return categories
        
        resume_index = categories.index(resume_from)
        return categories[resume_index:]
    
    def _show_execution_plan(self, execution_plan: ExecutionPlan, args: argparse.Namespace):
        """Display the execution plan to the user."""
        if not execution_plan or not execution_plan.phases:
            return
        
        print(f"\1{'='*60}")
        print("EXECUTION PLAN")
        print(f"{'='*60}")
        print(f"Total Categories: {len(execution_plan.execution_order)}")
        print(f"Execution Phases: {len(execution_plan.phases)}")
        print(f"Estimated Duration: {execution_plan.total_estimated_duration}")
        
        for phase_num, phase_categories in enumerate(execution_plan.phases):
            print(f"\1Phase {phase_num + 1}: {len(phase_categories)} categories")
            for category_name in phase_categories:
                category = self.category_system.get_category(category_name)
                if category:
                    duration = category.estimated_duration
                    priority = category.priority.name
                    print(f"  - {category_name} ({priority}, ~{duration})")
        
        print(f"\n{'='*60}\n")
    
    def _execute_categories_by_phases(self, execution_plan: ExecutionPlan, args: argparse.Namespace) -> Dict:
        """Execute categories according to the execution plan."""
        results = {}
        
        for phase_num, phase_categories in enumerate(execution_plan.phases):
            print(f"\1{'='*40}")
            print(f"PHASE {phase_num + 1}: {len(phase_categories)} categories")
            print(f"{'='*40}")
            
            # Execute categories in this phase
            phase_results = self._execute_phase_categories(phase_categories, phase_num, args)
            results.update(phase_results)
            
            # Check if we should stop due to fail-fast
            if self.fail_fast_strategy:
                failed_categories = [cat for cat, result in phase_results.items() if not result["success"]]
                if failed_categories:
                    for failed_cat in failed_categories:
                        # Record the failure
                        self.fail_fast_strategy.record_failure(
                            test_name=f"{failed_cat}_tests",
                            category=failed_cat,
                            error_message="Category failed",
                            error_type="CategoryFailure"
                        )
                    
                    should_stop, decision = self.fail_fast_strategy.should_fail_fast(
                        current_stats=self.progress_tracker.get_current_progress() if self.progress_tracker else None
                    )
                    # Check if --no-phase-dependencies flag allows continuing despite failures
                    if should_stop and decision and not getattr(args, 'no_phase_dependencies', False):
                        print(f"\1Stopping execution: {decision.reason}")
                        # Mark remaining categories as skipped
                        for remaining_phase in execution_plan.phases[phase_num + 1:]:
                            for category_name in remaining_phase:
                                results[category_name] = {
                                    "success": False,
                                    "duration": 0,
                                    "output": "",
                                    "errors": f"Skipped: {decision.reason}",
                                    "skipped": True
                                }
                        break
                    elif should_stop and decision and getattr(args, 'no_phase_dependencies', False):
                        print(f"\1Phase dependency override: Continuing despite failures ({decision.reason})")
                        # Continue with next phase despite failures
        
        return results
    
    def _execute_phase_categories(self, category_names: List[str], phase_num: int, args: argparse.Namespace) -> Dict:
        """Execute categories in a single phase."""
        results = {}
        
        for category_name in category_names:
            print(f"\1Executing category: {category_name}")
            
            # Start category tracking
            if self.progress_tracker:
                self.progress_tracker.start_category(category_name, phase=phase_num)
            
            # Execute the category
            result = self._execute_single_category(category_name, args)
            results[category_name] = result
            
            # Validate E2E test timing BEFORE recording results
            if 'e2e' in category_name.lower():
                timing_valid = self._validate_e2e_test_timing(category_name, result)
                if not timing_valid:
                    # Force test failure for 0-second e2e tests
                    result["success"] = False
                    result["errors"] = (result.get("errors", "") + 
                                      "\n\n ALERT:  E2E TESTS FAILED: 0-second execution detected. "
                                      "All e2e tests returning in 0 seconds are automatic hard failures.").strip()
            
            # Record test results in tracker
            if self.test_tracker and TestRunRecord:
                self._record_test_results(category_name, result, args.env)
            
            # Update progress tracking
            if self.progress_tracker:
                test_counts = self._extract_test_counts_from_result(result)
                self.progress_tracker.complete_category(
                    category_name,
                    success=result["success"],
                    test_counts=test_counts
                )
            
            # Check for early termination
            if args.fast_fail and not result["success"]:
                print(f"Fast-fail triggered by category: {category_name}")
                break
        
        return results
    
    def _execute_single_category(self, category_name: str, args: argparse.Namespace) -> Dict:
        """Execute a single category."""
        category = self.category_system.get_category(category_name)
        if not category:
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": f"Category '{category_name}' not found"
            }
        
        # Map category to services
        category_services = self._get_services_for_category(category_name)
        
        if len(category_services) > 1:
            # Run multiple services
            all_results = {}
            for service in category_services:
                service_result = self._run_service_tests_for_category(service, category_name, args)
                all_results[service] = service_result
            
            # Combine results
            overall_success = all(r["success"] for r in all_results.values())
            combined_output = "\n".join(r.get("output", "") for r in all_results.values())
            combined_errors = "\n".join(r.get("errors", "") for r in all_results.values())
            total_duration = sum(r.get("duration", 0) for r in all_results.values())
            
            return {
                "success": overall_success,
                "duration": total_duration,
                "output": combined_output,
                "errors": combined_errors,
                "service_results": all_results
            }
        else:
            # Run single service
            return self._run_service_tests_for_category(category_services[0], category_name, args)
    
    def _get_services_for_category(self, category_name: str) -> List[str]:
        """Determine which services to run for a category."""
        category_service_mapping = {
            "smoke": ["backend"],  # Auth service has no smoke tests
            "unit": ["backend", "auth"],
            "integration": ["backend"],
            "api": ["backend"],
            "database": ["backend"],
            "post_deployment": ["backend"],  # Post-deployment tests run from backend
            "websocket": ["backend"],
            "agent": ["backend"],
            "security": ["auth"],
            "frontend": ["frontend"],
            "e2e": ["backend"],  # E2E tests run from backend
            "e2e_critical": ["backend"],  # Critical e2e tests
            "e2e_full": ["backend"],  # Full e2e suite
            "cypress": ["cypress"],  # Special handler for Cypress E2E tests
            "performance": ["backend", "auth"]
        }
        
        return category_service_mapping.get(category_name, ["backend"])
    

    def _fast_path_collect_tests(self, pattern: str, category: str) -> List[str]:
        """Fast-path test collection bypassing heavy setup"""

        # Skip Docker/service setup for simple collection
        if hasattr(self, '_collection_cache'):
            cache_key = f"{pattern}:{category}"
            if cache_key in self._collection_cache:
                return self._collection_cache[cache_key]

        # E2E-specific optimized collection for large volume directories
        if category == 'e2e' or 'e2e' in pattern.lower():
            return self._collect_e2e_optimized(pattern)

        # Use simple file discovery instead of full pytest collection
        test_files = []
        test_dirs = [
            self.project_root / "netra_backend" / "tests",
            self.project_root / "tests"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                # Use glob for fast file discovery with safe pattern
                if pattern == '*':
                    glob_pattern = "**/*test*.py"
                else:
                    clean_pattern = pattern.replace('*', '')
                    if clean_pattern:
                        glob_pattern = f"**/*{clean_pattern}*.py"
                    else:
                        glob_pattern = "**/*test*.py"

                pattern_files = list(test_dir.rglob(glob_pattern))
                test_files.extend([str(f) for f in pattern_files if f.is_file()])
        
        # Cache result
        if not hasattr(self, '_collection_cache'):
            self._collection_cache = {}
        self._collection_cache[f"{pattern}:{category}"] = test_files
        
        return test_files

    def _collect_e2e_optimized(self, pattern: str) -> List[str]:
        """Optimized E2E test collection using the E2E collection optimizer"""
        try:
            # Import the E2E collection optimizer
            from tests.e2e_collection_optimizer import E2ECollectionOptimizer

            optimizer = E2ECollectionOptimizer(self.project_root)
            test_files = optimizer.collect_tests_optimized(pattern)

            # Cache the result in our cache as well
            if not hasattr(self, '_collection_cache'):
                self._collection_cache = {}
            self._collection_cache[f"e2e_optimized:{pattern}"] = test_files

            return test_files

        except ImportError as e:
            print(f"[WARNING] E2E optimizer not available, falling back to standard collection: {e}")
            return self._fallback_e2e_collection(pattern)
        except Exception as e:
            print(f"[WARNING] E2E optimization failed, falling back to standard collection: {e}")
            return self._fallback_e2e_collection(pattern)

    def _fallback_e2e_collection(self, pattern: str) -> List[str]:
        """Fallback E2E collection without optimization"""
        e2e_dir = self.project_root / "tests" / "e2e"
        if not e2e_dir.exists():
            return []

        test_files = []
        if pattern == '*':
            glob_pattern = "**/*test*.py"
        else:
            clean_pattern = pattern.replace('*', '')
            glob_pattern = f"**/*{clean_pattern}*.py" if clean_pattern else "**/*test*.py"

        pattern_files = list(e2e_dir.rglob(glob_pattern))
        test_files = [str(f) for f in pattern_files if f.is_file() and 'test_' in f.name]

        return test_files

    def _parallel_collect_tests(self, patterns: List[str]) -> Dict[str, List[str]]:
        """Collect tests in parallel for multiple patterns"""
        
        def collect_single_pattern(pattern: str) -> Tuple[str, List[str]]:
            """Collect tests for a single pattern"""
            try:
                tests = self._fast_path_collect_tests(pattern, "unknown")
                return pattern, tests
            except Exception as e:
                print(f"Warning: Failed to collect tests for pattern {pattern}: {e}")
                return pattern, []
        
        # Use ThreadPoolExecutor for I/O-bound file discovery
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(collect_single_pattern, pattern) for pattern in patterns]
            results = {}
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    pattern, tests = future.result()
                    results[pattern] = tests
                except Exception as e:
                    print(f"Warning: Parallel collection failed: {e}")
        
        return results


    def _run_service_tests_for_category(self, service: str, category_name: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service and category combination."""
        # Special handling for Cypress tests
        if service == "cypress":
            return self._run_cypress_tests(category_name, args)
            
        config = self.test_configs.get(service)
        if not config:
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": f"Service '{service}' not configured"
            }
        
        # Set environment for test execution
        self._set_test_environment(args)
        
        # Build test command
        if service == "frontend":
            cmd = self._build_frontend_command(category_name, args)
        else:
            cmd = self._build_pytest_command(service, category_name, args)
        
        # Debug output
        if args.verbose:
            print(f"[DEBUG] Running command for {service}: {cmd}")
            print(f"[DEBUG] Python command used: {self.python_command}")
            print(f"[DEBUG] Working directory: {config['path']}")

        # Execute tests with timeout
        start_time = time.time()
        # Set timeout based on service type and category
        if service == "frontend":
            timeout_seconds = 120  # 2 minutes for frontend tests (mostly unit tests)
        elif category_name == "unit":
            timeout_seconds = 180  # 3 minutes for unit tests specifically
        else:
            timeout_seconds = 600  # 10 minutes timeout for integration tests
        try:
            # Fix stdout flush issue with Windows-safe flushing
            import sys
            try:
                if hasattr(sys.stdout, 'flush') and not getattr(sys.stdout, 'closed', False):
                    sys.stdout.flush()
            except (ValueError, OSError):
                pass  # Skip flush if stdout is closed or has issues
            
            try:
                if hasattr(sys.stderr, 'flush') and not getattr(sys.stderr, 'closed', False):
                    sys.stderr.flush()
            except (ValueError, OSError):
                pass  # Skip flush if stderr is closed or has issues
            
            # TEMPORARY FIX: Use regular environment instead of isolated environment
            # to test if isolation is causing the pytest issue
            subprocess_env = dict(os.environ)
            print(f"[TEMP_DEBUG] Using regular os.environ instead of isolated environment")

            # # Original code with isolated environment:
            # env_manager = get_env()
            # subprocess_env = env_manager.get_subprocess_env()
            
            # CRITICAL: Apply Windows encoding fixes to subprocess environment
            if sys.platform == "win32":
                from shared.windows_encoding import get_subprocess_env
                subprocess_env = get_subprocess_env(subprocess_env)
            
            subprocess_env.update({'PYTHONUNBUFFERED': '1', 'PYTHONUTF8': '1'})

            # CRITICAL: Set PYTHONPATH to ensure test_framework can be imported
            subprocess_env['PYTHONPATH'] = str(self.project_root)
            
            # Use subprocess.Popen for better process control on Windows 
            # CRITICAL FIX: Apply Windows file handle management to all services, not just frontend
            if sys.platform == "win32":
                # Special handling for all processes on Windows to prevent I/O closed file errors
                # Configure Windows-specific creation flags and file handle management
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                
                # CRITICAL: Windows-specific subprocess environment already set by get_subprocess_env above
                # Add additional Windows-specific variables for testing stability
                subprocess_env.update({
                    'PYTHONLEGACYWINDOWSSTDIO': '0',  # Use new Windows stdio for better Unicode support
                    'PYTHONDONTWRITEBYTECODE': '1',  # Prevent .pyc files during testing
                })
                
                # DEBUG: Log subprocess details
                print(f"[SUBPROCESS_DEBUG] Command: {cmd}")
                print(f"[SUBPROCESS_DEBUG] Working dir: {config['path']}")
                print(f"[SUBPROCESS_DEBUG] Environment PATH first 100 chars: {subprocess_env.get('PATH', 'NOT_SET')[:100]}...")
                print(f"[SUBPROCESS_DEBUG] Environment PYTHON: {subprocess_env.get('PYTHON', 'NOT_SET')}")
                print(f"[SUBPROCESS_DEBUG] Environment PYTHONPATH: {subprocess_env.get('PYTHONPATH', 'NOT_SET')}")

                # CRITICAL: Use explicit encoding and error handling for Windows Unicode issues
                process = subprocess.Popen(
                    cmd,
                    cwd=config["path"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,  # Provide stdin to prevent handle issues
                    shell=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',  # CRITICAL: Replace invalid characters instead of failing
                    env=subprocess_env,
                    creationflags=creationflags,
                    # CRITICAL: Close file descriptors on Windows to prevent leaks
                    close_fds=False,  # Keep False on Windows as it's incompatible with shell=True
                    # Additional Windows-specific options to prevent encoding issues
                    bufsize=0  # Unbuffered to prevent issues with mixed text/binary
                )
                
                # Track the process for automatic cleanup
                track_subprocess(process)
                
                try:
                    # CRITICAL: Close stdin immediately to prevent hanging
                    process.stdin.close()
                    stdout, stderr = process.communicate(timeout=timeout_seconds)
                    returncode = process.returncode

                    # DEBUG: Log subprocess results
                    print(f"[SUBPROCESS_DEBUG] Return code: {returncode}")
                    print(f"[SUBPROCESS_DEBUG] Stdout (first 200 chars): {stdout[:200]!r}")
                    print(f"[SUBPROCESS_DEBUG] Stderr (first 200 chars): {stderr[:200]!r}")
                except subprocess.TimeoutExpired:
                    # Clean up hanging process on timeout
                    cleanup_subprocess(process, timeout=5)
                    raise
                except Exception as e:
                    # CRITICAL: Robust error handling for Windows I/O issues in process communication
                    error_messages = [
                        f"[WARNING] Process communication error: {e}",
                        f"[DEBUG] Error type: {type(e)}",
                        f"[DEBUG] Error args: {e.args}"
                    ]
                    
                    # Try to get full traceback safely
                    try:
                        import traceback
                        error_messages.append(f"[DEBUG] Full traceback: {traceback.format_exc()}")
                    except Exception:
                        error_messages.append("[DEBUG] Unable to get full traceback")
                    
                    # Print error messages with I/O error resilience
                    for msg in error_messages:
                        try:
                            print(msg)
                        except Exception:
                            # If print fails, try direct stderr write
                            try:
                                if hasattr(sys.stderr, 'write') and not getattr(sys.stderr, 'closed', False):
                                    sys.stderr.write(msg + '\n')
                                    sys.stderr.flush()
                            except Exception:
                                # Complete failure - continue without logging
                                pass
                    
                    # Try to clean up gracefully
                    try:
                        cleanup_subprocess(process, timeout=2)
                    except Exception as cleanup_e:
                        try:
                            print(f"[DEBUG] Cleanup error: {cleanup_e}")
                        except Exception:
                            # Ignore if we can't print the cleanup error
                            pass
                    raise
                finally:
                    # Always ensure process is cleaned up
                    cleanup_subprocess(process, timeout=2)
                
                result = subprocess.CompletedProcess(
                    args=cmd,
                    returncode=returncode,
                    stdout=stdout if 'stdout' in locals() else "",
                    stderr=stderr if 'stderr' in locals() else ""
                )
            else:
                # Use standard subprocess.run for non-Windows platforms
                result = subprocess.run(
                    cmd,
                    cwd=config["path"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout_seconds,
                    env=subprocess_env
                )
            # Handle unicode encoding issues by cleaning the output
            if result.stdout:
                result.stdout = result.stdout.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            if result.stderr:
                result.stderr = result.stderr.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            success = result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"[ERROR] {service} tests timed out after {timeout_seconds} seconds")
            print(f"[ERROR] Command: {cmd}")
            
            # Clean up any hanging processes after timeout
            if cleanup_manager:
                stats = cleanup_manager.cleanup_all()
                if stats["total_cleaned"] > 0:
                    print(f"[INFO] Cleaned up {stats['total_cleaned']} hanging processes after timeout")
            
            success = False
            result = subprocess.CompletedProcess(
                args=cmd, 
                returncode=1, 
                stdout="", 
                stderr=f"Tests timed out after {timeout_seconds} seconds"
            )
        except Exception as e:
            print(f"[ERROR] Failed to run {service} tests: {e}")
            print(f"[DEBUG] Exception type: {type(e)}")
            print(f"[DEBUG] Exception args: {e.args}")
            import traceback
            print(f"[DEBUG] Full exception traceback:")
            print(traceback.format_exc())
            success = False
            result = None
        
        duration = time.time() - start_time
        
        return {
            "success": success,
            "duration": duration,
            "output": result.stdout if result else "",
            "errors": result.stderr if result else ""
        }
    
    def _can_run_cypress_tests(self) -> Tuple[bool, str]:
        """Check if Cypress tests can run given current environment."""
        from dev_launcher.docker_services import check_docker_availability
        import socket
        
        # Check Docker availability
        docker_available = check_docker_availability()
        
        # Use port discovery to get actual service ports
        port_mappings = self.port_discovery.discover_all_ports()
        
        # Quick service availability checks with discovered ports
        def quick_service_check(host: str, port: int, timeout: float = 1.0) -> bool:
            """Quick, non-blocking check if a service is available."""
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except (socket.timeout, socket.error, ConnectionRefusedError, OSError):
                return False
        
        # Check services with discovered ports - use test defaults when in test mode
        postgres_port = port_mappings['postgres'].external_port if 'postgres' in port_mappings else 5433
        redis_port = port_mappings['redis'].external_port if 'redis' in port_mappings else 6381
        backend_port = port_mappings['backend'].external_port if 'backend' in port_mappings else 8001
        
        local_postgres = quick_service_check("localhost", postgres_port)
        local_redis = quick_service_check("localhost", redis_port)
        local_backend = quick_service_check("localhost", backend_port)
        
        # Check if we can start missing services
        if not (local_postgres and local_redis) and docker_available:
            print("[INFO] Some services not running, attempting to start via Docker...")
            required = ['postgres', 'redis'] if not local_postgres else ['redis']
            success, started = self.port_discovery.start_missing_services(required)
            if success:
                print(f"[INFO] Started services: {started}")
                # Re-check after starting
                import time
                time.sleep(5)  # Give services time to start
                port_mappings = self.port_discovery.discover_all_ports()
                postgres_port = port_mappings['postgres'].external_port if 'postgres' in port_mappings else 5432
                redis_port = port_mappings['redis'].external_port if 'redis' in port_mappings else 6379
                local_postgres = quick_service_check("localhost", postgres_port)
                local_redis = quick_service_check("localhost", redis_port)
        
        # Hard fail if services still not available
        if not docker_available and not (local_postgres and local_redis):
            raise RuntimeError(
                "HARD FAIL: Cannot run E2E tests - Docker Desktop not running and "
                "required local services not available.\n"
                f"Either start Docker Desktop or run local PostgreSQL (port {postgres_port}) "
                f"and Redis (port {redis_port}) services.\n"
                "Quick fix: python scripts/docker.py start"
            )
        
        if not local_backend:
            raise RuntimeError(
                f"HARD FAIL: Cannot run E2E tests - Backend service not running on port {backend_port}. "
                "Start the backend service first using 'python scripts/dev_launcher.py backend' or docker-compose."
            )
        
        return True, "Services available for Cypress tests"
    
    def _get_cypress_runner(self):
        """Get Cypress runner, initializing it lazily."""
        if self.cypress_runner is None:
            self.cypress_runner = CypressTestRunner(self.project_root)
        return self.cypress_runner
    
    def _run_cypress_tests(self, category_name: str, args: argparse.Namespace) -> Dict:
        """Run Cypress E2E tests using the CypressTestRunner."""
        print(f"Running Cypress tests for category: {category_name}")
        
        # Early check for service availability - will raise exception if services unavailable
        try:
            can_run, message = self._can_run_cypress_tests()
            print(f"[INFO] {message}")
        except RuntimeError as e:
            # Hard failure for E2E tests when services unavailable
            print(f"\n[ERROR] {str(e)}")
            print("\n[HARD FAIL] E2E tests cannot proceed without required services.")
            print("\nTo fix this issue:")
            print("  1. Quick fix: python scripts/docker.py start")
            print("  2. Start Docker Desktop if not running")
            print("  3. OR manually start required services locally")
            print("\nFor more help: python scripts/docker.py help")
            raise SystemExit(1)  # Hard exit with error code
        
        try:
            # Create Cypress execution options
            options = CypressExecutionOptions(
                headed=args.cypress_headed if hasattr(args, 'cypress_headed') else False,
                browser=args.cypress_browser if hasattr(args, 'cypress_browser') else "chrome",
                timeout=1800,  # 30 minutes timeout
                retries=2,
                parallel=False,  # Cypress parallel execution not enabled for now
                env_vars={}
            )
            
            # Set spec pattern based on category if needed
            if category_name == "cypress":
                # Run all Cypress tests
                options.spec_pattern = None
            elif category_name == "smoke":
                # Run critical tests only
                options.spec_pattern = "cypress/e2e/critical-basic-flow.cy.ts,cypress/e2e/basic-ui-test.cy.ts"
            else:
                # Category-specific patterns
                cypress_runner = self._get_cypress_runner()
                spec_patterns = cypress_runner.config_manager.get_spec_patterns(category_name)
                if spec_patterns:
                    options.spec_pattern = ",".join(spec_patterns)
            
            # Run Cypress tests (handle async call with event loop detection)
            cypress_runner = self._get_cypress_runner()
            import asyncio
            try:
                # Try to get existing event loop
                loop = asyncio.get_running_loop()
                # If we have a loop, we need to run in a separate thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(cypress_runner.run_tests(options)))
                    success, results = future.result(timeout=options.timeout)
            except RuntimeError:
                # No event loop running, safe to create new one
                success, results = asyncio.run(cypress_runner.run_tests(options))
            
            # Convert to unified format
            result_dict = {
                "success": success,
                "duration": results.get("execution_time_seconds", 0),
                "output": results.get("raw_output", {}).get("stdout", ""),
                "errors": results.get("raw_output", {}).get("stderr", "") if not success else "",
                "category": "cypress",
                "test_count": results.get("total_tests", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "skipped": results.get("skipped", 0)
            }
            
            # Add Docker-specific error handling if present
            if not success and "docker_info" in results:
                docker_info = results["docker_info"]
                if not docker_info.get("docker_available", True):
                    print("ERROR: Cypress tests failed due to missing services")
                    print(f"HINT: {results.get('suggestion', 'Please ensure required services are running')}")
                    result_dict["docker_error"] = True
            
            return result_dict
            
        except Exception as e:
            error_msg = f"Cypress test execution failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            
            # Check if this is a Docker-related error
            if "Docker" in str(e) or "docker" in str(e).lower():
                print("HINT: This appears to be a Docker-related issue.")
                print("      Either start Docker Desktop or ensure required services are running locally.")
                print("      Quick fix: python scripts/docker.py start")
                print("      For help: python scripts/docker.py help")
            
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": error_msg,
                "category": "cypress"
            }
    
    def _build_pytest_command(self, service: str, category_name: str, args: argparse.Namespace) -> str:
        """Build pytest command for backend/auth services."""
        config = self.test_configs[service]
        
        cmd_parts = [self.python_command, "-m", "pytest"]
        
        # Add category-specific selection (service-aware paths)
        # FIXED: Use service-specific paths instead of hardcoded backend paths
        if service == "backend":
            category_markers = {
                "smoke": [str(config["test_dir"]), "-m", "smoke"],
                "unit": ["netra_backend/tests/unit", "netra_backend/tests/core"],
                "integration": ["netra_backend/tests/integration", "netra_backend/tests/startup"],
                "api": ["netra_backend/tests/test_api_core_critical.py", "netra_backend/tests/test_api_error_handling_critical.py", "netra_backend/tests/test_api_threads_messages_critical.py", "netra_backend/tests/test_api_agent_generation_critical.py", "netra_backend/tests/test_api_endpoints_critical.py"],
                "database": ["netra_backend/tests/test_database_connections.py", "netra_backend/tests/clickhouse"],
                "post_deployment": ["tests/post_deployment"],
                "websocket": [str(config["test_dir"]), "-k", '"websocket or ws"'],
                "agent": ["netra_backend/tests/agents"],
                "security": [str(config["test_dir"]), "-k", '"auth or security"'],
                # CRITICAL: Cloud Run deployment tests - P0 Issue #146
                "deployment_critical": ["tests/integration/test_cloud_run_port_config.py", "tests/integration/test_health_endpoints.py", "tests/e2e/test_staging_deployment.py", "tests/unit/test_deployment_configs.py", "-m", "deployment_critical"],
                # FIXED: E2E category now points only to actual e2e tests
                "e2e_critical": ["tests/e2e/critical"],  # Curated critical e2e tests
                "e2e": ["tests/e2e/integration"],  # Actual e2e integration tests only
                "e2e_full": ["tests/e2e"],  # Full e2e suite (use with caution - may timeout),
                "performance": [str(config["test_dir"]), "-k", "performance"]
            }
        elif service == "auth":
            category_markers = {
                "smoke": [str(config["test_dir"]), "-m", "smoke"],
                "unit": ["auth_service/tests", "-m", "unit"],
                "integration": ["auth_service/tests", "-m", "integration"],
                "security": ["auth_service/tests", "-m", "security"],
                "performance": ["auth_service/tests", "-m", "performance"]
            }
        else:
            # Fallback for unknown services
            category_markers = {
                "smoke": [str(config["test_dir"]), "-m", "smoke"],
                "unit": [str(config["test_dir"]), "-m", "unit"],
                "integration": [str(config["test_dir"]), "-m", "integration"],
                "security": [str(config["test_dir"]), "-m", "security"],
                "performance": [str(config["test_dir"]), "-m", "performance"]
            }
        
        # Add service-specific configuration file
        if "config" in config:
            cmd_parts.extend(["-c", str(config["config"])])
        
        if category_name in category_markers:
            cmd_parts.extend(category_markers[category_name])
        else:
            # Default: use the test directory
            cmd_parts.append(str(config["test_dir"]))
        
        # Add environment-specific filtering (skip for API category which doesn't use env markers)
        # TEMPORARILY DISABLED: Environment markers cause pytest to hang when no matching tests exist
        # TODO: Implement smarter environment marker detection
        # if hasattr(args, 'env') and args.env and category_name != "api":
        #     # Add environment marker to filter tests - use pytest markers, not -k expressions
        #     env_marker = f'env_{args.env}'
        #     cmd_parts.extend(["-m", env_marker])
        
        # Add coverage options - only if pytest-cov is available
        if not args.no_coverage and PYTEST_COV_AVAILABLE:
            cmd_parts.extend([
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        elif not args.no_coverage and not PYTEST_COV_AVAILABLE:
            # Log that coverage is being skipped due to missing pytest-cov
            print(f"[WARNING] Coverage requested but pytest-cov not available - skipping coverage for {service}:{category_name}")
        
        # Add parallelization
        if args.parallel:
            cmd_parts.extend(["-n", str(args.workers)])
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Environment-aware timeout configuration - replaces global pyproject.toml timeout
        # This provides sophisticated timeout handling for different environments and test types
        if self._detect_staging_environment(args):
            # Staging environment needs longer timeouts due to network latency and GCP constraints
            if category_name == "unit":
                cmd_parts.extend(["--timeout=300", "--timeout-method=thread"])  # 5min for staging unit tests
            elif category_name in ["e2e", "integration", "e2e_critical", "e2e_full"]:
                cmd_parts.extend(["--timeout=900", "--timeout-method=thread"])  # 15min for staging e2e tests
            else:
                cmd_parts.extend(["--timeout=600", "--timeout-method=thread"])  # 10min for staging integration tests
        elif category_name == "unit":
            cmd_parts.extend(["--timeout=180", "--timeout-method=thread"])  # 3min for local unit tests
        elif category_name in ["e2e", "integration", "e2e_critical", "e2e_full"]:
            cmd_parts.extend(["--timeout=600", "--timeout-method=thread"])   # 10min for local e2e tests
        elif category_name == "frontend":
            cmd_parts.extend(["--timeout=120", "--timeout-method=thread"])   # 2min for frontend tests
        else:
            cmd_parts.extend(["--timeout=300", "--timeout-method=thread"])   # 5min for other test categories
        
        # Add specific test pattern
        if args.pattern:
            # Clean up pattern - remove asterisks that are invalid for pytest -k expressions
            # pytest -k expects Python-like expressions, not glob patterns
            clean_pattern = args.pattern.strip('*')
            cmd_parts.extend(["-k", f'"{clean_pattern}"'])
        
        return " ".join(cmd_parts)
    
    def _build_frontend_command(self, category_name: str, args: argparse.Namespace) -> str:
        """Build test command for frontend."""
        # Determine categories and check for E2E testing
        categories_to_run = self._determine_categories_to_run(args)
        e2e_categories = {'e2e', 'e2e_critical', 'cypress'}
        running_e2e = bool(set(categories_to_run) & e2e_categories)
        
        # Real LLM is DEFAULT for all frontend tests per CLAUDE.md (mocks forbidden)
        # Only exception: pure unit tests in test environment
        use_real_llm = True  # Default to real LLM
        use_real_services = args.real_services or args.env in ['dev', 'staging'] or running_e2e
        
        # Set environment variables using IsolatedEnvironment
        env = get_env()
        
        # CRITICAL: Real LLM is DEFAULT per CLAUDE.md - mocks forbidden except for unit tests
        env.set('USE_REAL_LLM', 'true', 'test_runner_frontend')
        env.set('NETRA_REAL_LLM_ENABLED', 'true', 'test_runner_frontend')
        env.set('ENABLE_REAL_LLM_TESTING', 'true', 'test_runner_frontend')
        env.set('TEST_USE_REAL_LLM', 'true', 'test_runner_frontend')
        env.set('TEST_LLM_MODE', 'real', 'test_runner_frontend')
        
        # Configure services
        if use_real_services:
            setup_file = "jest.setup.real.js"
            env.set('USE_REAL_SERVICES', 'true', 'test_runner_frontend')
            if args.env == 'dev':
                env.set('USE_DOCKER_SERVICES', 'true', 'test_runner_frontend')
        else:
            setup_file = "jest.setup.js"
            env.set('USE_REAL_SERVICES', 'false', 'test_runner_frontend')
            env.set('USE_DOCKER_SERVICES', 'false', 'test_runner_frontend')
        
        category_commands = {
            "unit": f"npm run test:unit -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "integration": f"npm run test:integration -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "e2e": f"npm run test:critical -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "frontend": f"npm run test:fast"
        }
        
        base_command = category_commands.get(category_name, f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}'")
        
        # Add additional flags
        if args.no_coverage:
            base_command += " --coverage=false"
        if args.fast_fail:
            base_command += " --bail"
        if args.verbose:
            base_command += " --verbose"
        if hasattr(args, 'max_workers') and args.max_workers:
            base_command += f" --maxWorkers={args.max_workers}"
        
        return base_command
    
    def _set_test_environment(self, args: argparse.Namespace):
        """Set environment variables for test execution."""
        # Set TEST_ENV for environment-aware testing using IsolatedEnvironment
        env = get_env()
        if hasattr(args, 'env'):
            env.set('TEST_ENV', args.env, 'test_runner_pytest')
        
        # Set production protection
        if hasattr(args, 'allow_prod') and args.allow_prod:
            env.set('ALLOW_PROD_TESTS', 'true', 'test_runner_pytest')
        else:
            # Note: Cannot unset in IsolatedEnvironment, set to false instead
            env.set('ALLOW_PROD_TESTS', 'false', 'test_runner_pytest')
        
        # Map env to existing env var patterns
        env_mapping = {
            'test': 'local',
            'dev': 'dev',
            'staging': 'staging',
            'prod': 'prod'
        }
        
        if hasattr(args, 'env'):
            env = get_env()
            mapped_env = env_mapping.get(args.env, args.env)
            env.set('ENVIRONMENT', mapped_env, 'test_runner_nodetest')
            
            # Set specific flags based on environment
            if args.env == 'test':
                env.set('TEST_MODE', 'mock', 'test_runner_nodetest')
                env.set('USE_TEST_DATABASE', 'true', 'test_runner_nodetest')
            elif args.env in ['dev', 'staging', 'prod']:
                env.set('TEST_MODE', 'real', 'test_runner_nodetest')
                env.set('USE_TEST_DATABASE', 'false', 'test_runner_nodetest')
    
    def _extract_test_counts_from_result(self, result: Dict) -> Dict[str, int]:
        """Extract test counts from execution result."""
        # Parse pytest output for actual counts
        output = result.get("output", "")
        test_counts = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0
        }
        
        # Simple parsing - could be enhanced
        if "passed" in output:
            import re
            passed_match = re.search(r'(\d+) passed', output)
            if passed_match:
                test_counts["passed"] = int(passed_match.group(1))
        
        if "failed" in output:
            import re
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                test_counts["failed"] = int(failed_match.group(1))
        
        test_counts["total"] = test_counts["passed"] + test_counts["failed"]
        
        return test_counts
    
    def _validate_e2e_test_timing(self, category_name: str, result: Dict) -> bool:
        """Validate that e2e tests have non-zero execution time.
        
        CRITICAL: E2E tests returning in 0 seconds are automatic hard failures.
        This indicates tests are not actually executing or are being skipped/mocked.
        See STAGING_100_TESTS_REPORT.md for context.
        """
        if not category_name or 'e2e' not in category_name.lower():
            return True  # Only validate e2e tests
            
        duration = result.get("duration", 0)
        output = result.get("output", "")
        
        # Check for 0-second test patterns in output
        import re
        zero_time_pattern = r'\[(0\.00+s|0s)\]'  # Matches [0.00s], [0.000s], [0s]
        zero_time_matches = re.findall(zero_time_pattern, output)
        
        # Count actual test executions with 0 time
        test_pattern = r'(test_\w+).*?\[(\d+\.\d+s|\d+s)\]'
        all_tests = re.findall(test_pattern, output)
        zero_time_tests = [(test, time) for test, time in all_tests if time in ['0.00s', '0.000s', '0s']]
        
        if zero_time_tests:
            print(f"\n{'='*60}")
            print(f" ALERT:  CRITICAL E2E TEST FAILURE: 0-SECOND EXECUTION DETECTED")
            print(f"{'='*60}")
            print(f"Category: {category_name}")
            print(f"Total tests with 0-second execution: {len(zero_time_tests)}")
            print(f"\nTests that returned in 0 seconds (AUTOMATIC HARD FAIL):")
            for test_name, exec_time in zero_time_tests[:10]:  # Show first 10
                print(f"   FAIL:  {test_name}: {exec_time}")
            if len(zero_time_tests) > 10:
                print(f"  ... and {len(zero_time_tests) - 10} more")
            print(f"\nThis indicates tests are:")
            print(f"  - Not actually executing")
            print(f"  - Being skipped/mocked inappropriately")
            print(f"  - Missing proper async/await handling")
            print(f"  - Not connecting to real services")
            print(f"\nSee reports/staging/STAGING_100_TESTS_REPORT.md for details")
            print(f"{'='*60}\n")
            return False
            
        # Also check if the entire category ran in under 1 second (suspicious for e2e)
        if duration < 1.0 and result.get("success", False):
            print(f"\n WARNING: [U+FE0F]  WARNING: E2E category '{category_name}' completed in {duration:.2f}s")
            print(f"   This is suspiciously fast for e2e tests that should connect to real services.")
            print(f"   Verify tests are actually executing and not being skipped.\n")
            
        return True
    
    def _record_test_results(self, category_name: str, result: Dict, environment: str):
        """Record test execution results in the tracker."""
        if not self.test_tracker or not TestRunRecord:
            return
            
        import re
        from datetime import datetime
        
        # Parse output to extract individual test results if possible
        output = result.get("output", "")
        
        # Try to parse pytest output for individual test results
        test_pattern = r"(\S+\.py::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
        matches = re.findall(test_pattern, output)
        
        if matches:
            # Record individual test results
            for test_path, status in matches:
                # Extract file path and test name
                parts = test_path.split("::") 
                file_path = parts[0] if parts else test_path
                test_name = parts[1] if len(parts) > 1 else "unknown"
                
                # Map status
                status_map = {
                    "PASSED": "passed",
                    "FAILED": "failed",
                    "SKIPPED": "skipped",
                    "ERROR": "error"
                }
                
                record = TestRunRecord(
                    test_id="",  # Will be generated by tracker
                    file_path=file_path,
                    test_name=test_name,
                    category=category_name,
                    subcategory=self._determine_subcategory(file_path),
                    status=status_map.get(status, "unknown"),
                    duration=0.0,  # Would need more parsing to extract
                    timestamp=datetime.now().isoformat(),
                    environment=environment,
                    error_message=None,  # Would need more parsing
                    failure_type=None
                )
                
                self.test_tracker.record_test_run(record)
        else:
            # Record category-level result
            record = TestRunRecord(
                test_id="",
                file_path=f"category_{category_name}",
                test_name=f"{category_name}_tests",
                category=category_name,
                subcategory=category_name,
                status="passed" if result["success"] else "failed",
                duration=result.get("duration", 0.0),
                timestamp=datetime.now().isoformat(),
                environment=environment,
                error_message=result.get("errors") if not result["success"] else None,
                failure_type="category_failure" if not result["success"] else None
            )
            
            self.test_tracker.record_test_run(record)
    
    def _determine_subcategory(self, file_path: str) -> str:
        """Determine test subcategory from file path."""
        if "unit" in file_path:
            return "unit"
        elif "integration" in file_path:
            return "integration"
        elif "e2e" in file_path:
            return "e2e"
        elif "api" in file_path:
            return "api"
        elif "websocket" in file_path:
            return "websocket"
        else:
            return "other"
    
    def _safe_print_unicode(self, text):
        """Safely print text with Unicode characters, falling back to ASCII on encoding errors."""
        try:
            print(text)
        except UnicodeEncodeError:
            # Replace Unicode symbols with ASCII equivalents for Windows console compatibility
            ascii_text = text.replace(" PASS: ", "[PASS]").replace(" FAIL: ", "[FAIL]").replace("[U+23ED][U+FE0F]", "[SKIP]")
            print(ascii_text)

    def _generate_report(self, results: Dict, args: argparse.Namespace):
        """Generate test execution report."""
        report_dir = self.project_root / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Build report data
        report_data = {
            "timestamp": timestamp,
            "environment": args.env,
            "categories": results,
            "overall_success": all(r["success"] for r in results.values()),
            "total_duration": sum(r["duration"] for r in results.values()),
            "execution_plan": self.execution_plan.to_dict() if hasattr(self.execution_plan, 'to_dict') else None,
            "category_statistics": self.category_system.get_category_statistics()
        }
        
        # Add progress tracking data
        if self.progress_tracker:
            progress_data = self.progress_tracker.get_current_progress()
            if progress_data:
                report_data["progress_tracking"] = progress_data
        
        # Save JSON report with optimization
        json_report = report_dir / f"test_report_{timestamp}.json"
        optimized_data, optimization_info = self._optimize_json_output(report_data, args)

        try:
            with open(json_report, "w") as f:
                if args.json_format == "compact":
                    json_content = self.json_formatter.format_compact(optimized_data)
                elif args.json_format == "pretty":
                    json_content = self.json_formatter.format_pretty(optimized_data)
                else:  # auto
                    json_content = self.json_formatter.format_auto(optimized_data, args.json_size_limit)

                f.write(json_content)

            # Log optimization results if significant changes were made
            if optimization_info.get("optimized", False):
                original_size = optimization_info.get("original_size_kb", 0)
                final_size = optimization_info.get("final_size_kb", 0)
                savings = optimization_info.get("size_reduction_percent", 0)
                print(f"\nJSON Optimization Applied:")
                print(f"  Original size: {original_size:.1f} KB")
                print(f"  Optimized size: {final_size:.1f} KB")
                print(f"  Size reduction: {savings:.1f}%")
                if optimization_info.get("truncated", False):
                    print(f"  Applied truncation to stay within {args.json_size_limit} KB limit")

        except JsonSizeExceedsLimitError as e:
            if args.json_auto_truncate:
                print(f"WARNING: JSON output exceeded size limit, auto-truncating: {e}")
                # Try again with auto-truncation
                limiter = JsonSizeLimiter(max_size_mb=args.json_size_limit / 1024)
                truncated_data = limiter.process_with_auto_truncation(report_data)
                with open(json_report, "w") as f:
                    json_content = self.json_formatter.format_compact(truncated_data)
                    f.write(json_content)
                print(f"JSON report auto-truncated and saved to: {json_report}")
            else:
                print(f"ERROR: JSON output exceeded size limit: {e}")
                print(f"Use --json-auto-truncate to enable automatic truncation")
                raise
        
        # Print summary
        print(f"\1{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Environment: {args.env}")
        print(f"Total Duration: {report_data['total_duration']:.2f}s")
        print(f"Categories Executed: {len(results)}")
        
        print(f"\1Category Results:")
        for category_name, result in results.items():
            status = " PASS:  PASSED" if result["success"] else " FAIL:  FAILED"
            if result.get("skipped"):
                status = "[U+23ED][U+FE0F] SKIPPED"
            self._safe_print_unicode(f"  {category_name:15} {status:15} ({result['duration']:.2f}s)")
        
        overall_status = " PASS:  PASSED" if report_data['overall_success'] else " FAIL:  FAILED"
        self._safe_print_unicode(f"\nOverall: {overall_status}")
        print(f"Report: {json_report}")

    def _optimize_json_output(self, report_data: Dict[str, any], args: argparse.Namespace) -> Tuple[Dict[str, any], Dict[str, any]]:
        """
        Optimize JSON output based on configured settings.

        Args:
            report_data: Original report data
            args: Command line arguments with optimization settings

        Returns:
            Tuple of (optimized_data, optimization_info)
        """
        # Initialize JSON optimizer with configured size limit
        if self.json_optimizer is None:
            self.json_optimizer = JsonOutputOptimizer(default_size_limit_kb=args.json_size_limit)

        # Get original size metrics
        original_metrics = self.json_optimizer.get_size_metrics(report_data)
        original_size_kb = original_metrics.get("size_kb", 0)

        optimization_info = {
            "original_size_kb": original_size_kb,
            "optimized": False,
            "truncated": False,
            "size_reduction_percent": 0.0
        }

        # Start with the original data
        optimized_data = report_data.copy()

        # Apply verbosity level filtering
        if args.json_verbosity != 3:  # 3 is the default "verbose" level
            optimized_data = self.json_verbosity_controller.apply_verbosity_level(
                optimized_data, args.json_verbosity
            )
            optimization_info["optimized"] = True

        # Apply progressive detail reduction for large test suites
        progressive_controller = ProgressiveDetailController()
        progressive_optimized = progressive_controller.apply_progressive_detail(optimized_data)
        if progressive_optimized != optimized_data:
            optimized_data = progressive_optimized
            optimization_info["optimized"] = True

        # Check if data exceeds size limit
        if self.json_optimizer.detect_large_output(optimized_data, args.json_size_limit):
            if args.json_auto_truncate:
                # Apply truncation with preserved fields
                truncator = JsonTruncator()
                optimized_data = truncator.truncate_preserving_essentials(
                    optimized_data,
                    target_size_kb=args.json_size_limit,
                    preserve_fields=args.json_preserve_fields
                )
                optimization_info["optimized"] = True
                optimization_info["truncated"] = True
            else:
                # Check if we should raise an exception
                final_metrics = self.json_optimizer.get_size_metrics(optimized_data)
                if final_metrics.get("size_kb", 0) > args.json_size_limit:
                    raise JsonSizeExceedsLimitError(
                        f"JSON output ({final_metrics.get('size_kb', 0):.1f} KB) "
                        f"exceeds configured limit ({args.json_size_limit} KB). "
                        f"Use --json-auto-truncate to enable automatic size reduction."
                    )

        # Calculate final metrics and savings
        final_metrics = self.json_optimizer.get_size_metrics(optimized_data)
        final_size_kb = final_metrics.get("size_kb", 0)

        if final_size_kb > 0 and original_size_kb > 0:
            size_reduction = ((original_size_kb - final_size_kb) / original_size_kb) * 100
            optimization_info["size_reduction_percent"] = max(0, size_reduction)
            optimization_info["final_size_kb"] = final_size_kb

        return optimized_data, optimization_info


async def execute_orchestration_mode(args) -> int:
    """
    Execute tests using the new Master Orchestration Controller system.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if not orchestration_config.master_orchestration_available:
        print(" FAIL:  Master Orchestration system not available. Please check imports.")
        print("Falling back to legacy mode...")
        return 1
    
    project_root = PROJECT_ROOT
    
    # Handle orchestration status command
    if args.orchestration_status:
        print("\n" + "="*60)
        print("ORCHESTRATION STATUS")
        print("="*60)
        print("Feature: Show running orchestration status")
        print("Status: Not yet implemented - requires persistent orchestration service")
        print("Available: Run 'python unified_test_runner.py --use-layers --help' for options")
        print("="*60)
        return 0
    
    # Determine execution mode and create appropriate controller
    controller = None
    execution_args = {
        "env": args.env,
        "real_llm": args.real_llm,
        "real_services": args.real_services,
        "fast_fail": getattr(args, 'fast_fail', False),
        "timeout": getattr(args, 'timeout', 30),
        "max_parallel": getattr(args, 'max_parallel', None) or 8
    }
    
    try:
        # Create controller based on execution mode
        if args.execution_mode == "fast_feedback" or (args.layers and "fast_feedback" in args.layers and len(args.layers) == 1):
            print("[U+1F680] Starting Fast Feedback execution (2-minute cycle)")
            controller = create_fast_feedback_controller(
                project_root=project_root,
                thread_id=args.websocket_thread_id
            )
            layers = ["fast_feedback"]
            
        elif args.execution_mode == "background" or args.background_e2e:
            print(" CYCLE:  Starting Background E2E execution")
            controller = create_background_only_controller(
                project_root=project_root,
                thread_id=args.websocket_thread_id
            )
            layers = ["e2e_background"]
            
        elif args.execution_mode == "hybrid":
            print(" LIGHTNING:  Starting Hybrid execution (foreground + background)")
            controller = create_hybrid_controller(
                project_root=project_root,
                thread_id=args.websocket_thread_id
            )
            layers = args.layers or ["fast_feedback", "core_integration", "service_integration", "e2e_background"]
            
        elif args.execution_mode == "nightly" or not args.execution_mode:
            print("[U+1F319] Starting Full Layered execution")
            controller = create_full_layered_controller(
                project_root=project_root,
                thread_id=args.websocket_thread_id,
                enable_background=not getattr(args, 'background_e2e', False)
            )
            layers = args.layers or ["fast_feedback", "core_integration", "service_integration"]
            if not getattr(args, 'background_e2e', False):
                layers.append("e2e_background")
        
        else:
            print(f" FAIL:  Invalid execution mode: {args.execution_mode}")
            return 1
        
        # Configure progress output mode
        if hasattr(controller.config, 'output_mode') and ProgressOutputMode:
            if args.progress_mode == "json":
                controller.config.output_mode = ProgressOutputMode.JSON
            elif args.progress_mode == "silent":
                controller.config.output_mode = ProgressOutputMode.SILENT
            elif args.progress_mode == "websocket":
                controller.config.output_mode = ProgressOutputMode.WEBSOCKET
        
        print(f"[U+1F4CB] Executing layers: {', '.join(layers)}")
        print(f"[U+1F30D] Environment: {args.env}")
        print(f"[U+1F916] Real LLM: {'Yes' if args.real_llm else 'No'}")
        print(f"[U+2699][U+FE0F]  Real Services: {'Yes' if args.real_services else 'No'}")
        print(f" CHART:  Progress Mode: {args.progress_mode}")
        print("-" * 60)
        
        # Execute orchestration
        results = await controller.execute_orchestration(
            execution_args=execution_args,
            layers=layers
        )
        
        # Process results
        success = results.get("success", False)
        
        if success:
            print("\n" + "="*60)
            print(" CELEBRATION:  Orchestrated test execution completed successfully!")
            print("="*60)
            
            # Show summary if available
            summary = results.get("summary", {})
            if summary:
                test_counts = summary.get("test_counts", {})
                if test_counts.get("total", 0) > 0:
                    print(f" CHART:  Tests: {test_counts.get('total', 0)} total, "
                          f"{test_counts.get('passed', 0)} passed, "
                          f"{test_counts.get('failed', 0)} failed")
                
                duration = summary.get("total_duration", 0)
                if duration > 0:
                    print(f"[U+23F1][U+FE0F]  Duration: {duration:.1f} seconds")
            
            return 0
        else:
            print("\n" + "="*60)
            print(" FAIL:  Orchestrated test execution failed")
            print("="*60)
            error = results.get("error")
            if error:
                print(f"Error: {error}")
            return 1
            
    except Exception as e:
        print(f" FAIL:  Orchestration execution failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    finally:
        if controller:
            await controller.shutdown()

    
    # Issue #485 fix: Add missing collection method for test infrastructure validation  
    def collect_tests_for_category(self, category: str) -> List[str]:
        """
        Collect tests for a specific category.
        
        Args:
            category: Test category name
            
        Returns:
            List of test file paths for the category
        """
        try:
            # Get category configuration
            category_obj = self.category_system.get_category(category)
            if not category_obj:
                logger.warning(f"Category '{category}' not found")
                return []
            
            # Get services for this category
            services = self._get_services_for_category(category)
            collected_tests = []
            
            for service in services:
                service_config = self.test_configs.get(service)
                if not service_config:
                    logger.warning(f"Service '{service}' not configured")
                    continue
                
                test_dir = Path(service_config["path"]) / service_config["test_dir"]
                if not test_dir.exists():
                    logger.warning(f"Test directory not found: {test_dir}")
                    continue
                
                # Use fast path collection to avoid Docker dependencies
                try:
                    # Find tests matching category patterns
                    category_patterns = getattr(category_obj, 'patterns', [f"*{category}*", f"test_{category}*"])
                    
                    for pattern in category_patterns:
                        pattern_tests = self._fast_path_collect_tests(pattern, category)
                        collected_tests.extend(pattern_tests)
                    
                    # Also search by directory structure
                    category_dirs = [
                        test_dir / category,
                        test_dir / f"{category}_tests", 
                        test_dir / "unit" if category == "unit" else test_dir / category
                    ]
                    
                    for cat_dir in category_dirs:
                        if cat_dir.exists():
                            test_files = list(cat_dir.rglob("test_*.py"))
                            collected_tests.extend([str(f) for f in test_files])
                    
                except Exception as e:
                    logger.error(f"Error collecting tests for service '{service}', category '{category}': {e}")
                    continue
            
            # Remove duplicates and return
            unique_tests = list(set(collected_tests))
            logger.info(f"Collected {len(unique_tests)} tests for category '{category}'")
            return unique_tests
            
        except Exception as e:
            logger.error(f"Error collecting tests for category '{category}': {e}")
            return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra Apex Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Service selection (for compatibility with legacy scripts)
    parser.add_argument(
        "--service",
        choices=["backend", "frontend", "auth", "auth_service", "all"],
        help="Run tests for specific service (legacy compatibility mode)"
    )
    
    # Category selection
    parser.add_argument(
        "--category",
        help="Run specific category (e.g., 'unit', 'integration', 'api')"
    )
    
    parser.add_argument(
        "--categories",
        nargs='+',
        help="Run multiple categories (e.g., '--categories unit integration api')"
    )
    
    # Environment configuration
    parser.add_argument(
        "--env",
        choices=["test", "dev", "staging", "prod"],
        default="test",
        help="Environment to test against (default: test)"
    )
    
    parser.add_argument(
        "--exclude-env",
        choices=["test", "dev", "staging", "prod"],
        help="Exclude tests for specific environment"
    )
    
    parser.add_argument(
        "--allow-prod",
        action="store_true",
        help="Allow production tests to run (requires explicit flag)"
    )
    
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Force real LLM for all tests (E2E tests use real LLM by default per CLAUDE.md)"
    )
    
    parser.add_argument(
        "--real-services",
        action="store_true",
        help="Use real backend services (Docker or local) for frontend tests"
    )

    parser.add_argument(
        "--staging-e2e",
        action="store_true",
        help="Run staging-based E2E tests (Docker-independent validation of business-critical functionality)"
    )

    parser.add_argument(
        "--no-docker",
        "--skip-docker",
        action="store_true",
        help="Skip Docker initialization for tests that don't need it (e.g., unit tests)"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of worker processes for Jest (frontend tests)"
    )
    
    # Coverage options
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--coverage",
        "--cov",
        action="store_true",
        help="Enable coverage reporting (legacy compatibility)"
    )
    
    parser.add_argument(
        "--no-dependencies",
        "--skip-deps",
        action="store_true",
        help="Skip dependency resolution - run only the specified categories without their dependencies"
    )

    parser.add_argument(
        "--no-phase-dependencies",
        action="store_true",
        help="Allow later phases to run even if earlier phases fail (remove phase dependency restrictions)"
    )
    
    parser.add_argument(
        "--min-coverage",
        type=int,
        default=70,
        help="Minimum coverage percentage required (default: 70)"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--fast-fail",
        action="store_true",
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--pattern",
        help="Run tests matching pattern"
    )
    
    # Legacy compatibility arguments from frontend/backend runners
    parser.add_argument(
        "--markers",
        "-m",
        help="Only run tests matching given mark expression (pytest backend)"
    )
    
    parser.add_argument(
        "--keyword",
        "-k", 
        help="Only run tests matching the given keyword expression"
    )
    
    parser.add_argument(
        "--lint",
        "-l",
        action="store_true",
        help="Run linting checks (frontend: ESLint)"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix linting issues"
    )
    
    parser.add_argument(
        "--build",
        "-b", 
        action="store_true",
        help="Build frontend for production"
    )
    
    parser.add_argument(
        "--type-check",
        "-t",
        action="store_true", 
        help="Run TypeScript type checking (frontend)"
    )
    
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Run in watch mode (frontend Jest)"
    )
    
    parser.add_argument(
        "--update-snapshots",
        "-u",
        action="store_true",
        help="Update Jest snapshots (frontend)"
    )
    
    parser.add_argument(
        "--cypress-open",
        action="store_true",
        help="Open Cypress interactive runner (frontend)"
    )
    
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run E2E tests with Cypress (frontend)"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check test dependencies before running"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies if missing (frontend)"
    )
    
    parser.add_argument(
        "--failed-first",
        "--ff",
        action="store_true",
        help="Run previously failed tests first (pytest backend)"
    )
    
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Generate JSON test report"
    )

    # JSON Output Optimization Arguments
    parser.add_argument(
        "--json-verbosity",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=2,
        help="JSON output verbosity level (1=minimal, 2=standard, 3=verbose, 4=debug, 5=full)"
    )

    parser.add_argument(
        "--json-size-limit",
        type=int,
        default=100,
        help="JSON output size limit in KB (default: 100KB)"
    )

    parser.add_argument(
        "--json-auto-truncate",
        action="store_true",
        help="Automatically truncate large JSON outputs instead of failing"
    )

    parser.add_argument(
        "--json-format",
        choices=["compact", "pretty", "auto"],
        default="auto",
        help="JSON formatting mode (compact=minimal size, pretty=readable, auto=size-based)"
    )

    parser.add_argument(
        "--json-preserve-fields",
        nargs="*",
        default=["summary", "overall_success", "total_duration", "failed_tests"],
        help="Fields to preserve when truncating JSON (space-separated list)"
    )

    parser.add_argument(
        "--html-output",
        action="store_true",
        help="Generate HTML test report"
    )
    
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Show slowest tests"
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output"
    )
    
    # Performance optimization arguments
    parser.add_argument(
        "--fast-collection",
        action="store_true",
        help="Enable fast test collection mode (skip service setup)"
    )
    parser.add_argument(
        "--parallel-collection", 
        action="store_true",
        help="Use parallel test discovery"
    )
    parser.add_argument(
        "--collection-timeout",
        type=int,
        default=30,
        help="Timeout for test collection in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--docker-pull-policy",
        choices=["always", "never", "missing"],
        default="missing",
        help="Docker pull policy for base images (default: missing - only pull if not cached locally)"
    )
    
    parser.add_argument(
        "--show-warnings",
        action="store_true",
        help="Show warning messages (backend pytest)"
    )
    
    # Enhanced features
    parser.add_argument(
        "--window-size",
        type=int,
        default=15,
        help="Auto-split window size in minutes (default: 15)"
    )
    
    parser.add_argument(
        "--fail-fast-mode",
        choices=["disabled", "first_failure", "category_failure", "critical_failure", 
                "threshold_based", "smart_adaptive", "dependency_aware"],
        default="category_failure",
        help="Fail-fast strategy mode (default: category_failure)"
    )
    
    parser.add_argument(
        "--progress-mode",
        choices=["simple", "rich", "json"],
        default="simple",
        help="Progress display mode (default: simple)"
    )
    
    parser.add_argument(
        "--resume-from",
        help="Resume execution from specific category"
    )
    
    parser.add_argument(
        "--disable-auto-split",
        action="store_true",
        help="Disable automatic test splitting"
    )
    
    parser.add_argument(
        "--splitting-strategy",
        choices=["time_based", "count_based", "category_based", 
                "complexity_based", "dependency_aware", "hybrid"],
        default="hybrid",
        help="Test splitting strategy (default: hybrid)"
    )
    
    # Discovery options
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and their configuration"
    )
    
    parser.add_argument(
        "--show-category-stats",
        action="store_true",
        help="Show historical category statistics"
    )
    
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip test structure and configuration validation (validation runs by default)"
    )
    
    parser.add_argument(
        "--full-validate",
        action="store_true",
        help="Run full validation on all Python files (default: quick mode with test files only)"
    )
    
    # Cypress-specific arguments
    parser.add_argument(
        "--cypress-headed",
        action="store_true",
        help="Run Cypress tests in headed mode (show browser UI)"
    )
    
    parser.add_argument(
        "--cypress-browser",
        choices=["chrome", "firefox", "edge", "electron"],
        default="chrome",
        help="Browser to use for Cypress tests (default: chrome)"
    )
    
    # Docker management arguments
    docker_group = parser.add_argument_group('Docker Management')
    
    docker_group.add_argument(
        "--docker-dedicated",
        action="store_true",
        help="Use dedicated Docker environment instead of shared (prevents conflicts)"
    )
    
    docker_group.add_argument(
        "--docker-production",
        action="store_true",
        help="Use production Docker images for reduced memory usage"
    )
    
    docker_group.add_argument(
        "--docker-no-cleanup",
        action="store_true",
        help="Don't clean up Docker environment after tests (for debugging)"
    )
    
    docker_group.add_argument(
        "--docker-force-restart",
        action="store_true",
        help="Force restart of Docker services even with cooldown"
    )
    
    docker_group.add_argument(
        "--docker-stats",
        action="store_true",
        help="Show Docker management statistics after test run"
    )
    
    docker_group.add_argument(
        "--no-alpine",
        action="store_true",
        help="Use regular images instead of Alpine (Alpine is default)"
    )
    
    docker_group.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Don't rebuild Docker images (rebuilding is default)"
    )
    
    docker_group.add_argument(
        "--rebuild-all",
        action="store_true",
        help="Rebuild all services, not just backend (default is backend only)"
    )
    
    # Service Orchestration arguments (GitHub Issue #136)
    service_group = parser.add_argument_group('Service Orchestration')
    
    service_group.add_argument(
        "--auto-services",
        action="store_true",
        help="Automatically start required Docker services for tests (resolves localhost:8000 timeouts)"
    )
    
    service_group.add_argument(
        "--prefer-staging",
        action="store_true", 
        help="Prefer staging endpoints over local services when both available"
    )
    
    service_group.add_argument(
        "--service-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for service startup and health checks (default: 60)"
    )
    
    service_group.add_argument(
        "--no-service-cleanup",
        action="store_true",
        help="Don't cleanup services started by auto-services (useful for debugging)"
    )
    
    service_group.add_argument(
        "--service-category",
        help="Override service requirements for specific test category (mission_critical, integration, etc.)"
    )
    
    # Add orchestrator arguments if available
    if orchestration_config.orchestrator_available:
        add_orchestrator_arguments(parser)
    
    # Add background E2E arguments if available
    if orchestration_config.background_e2e_available:
        add_background_e2e_arguments(parser)
    
    # NEW: Add Master Orchestration Controller arguments (only if not already added)
    if orchestration_config.master_orchestration_available and not orchestration_config.orchestrator_available:
        orchestration_group = parser.add_argument_group('Master Orchestration System')
        
        orchestration_group.add_argument(
            "--use-layers",
            action="store_true",
            help="Use new layered orchestration system instead of legacy categories"
        )
        
        orchestration_group.add_argument(
            "--layers",
            nargs="*",
            choices=["fast_feedback", "core_integration", "service_integration", "e2e_background"],
            help="Specific layers to execute (use with --use-layers)"
        )
        
        orchestration_group.add_argument(
            "--execution-mode",
            choices=["fast_feedback", "nightly", "background", "hybrid"],
            help="Predefined execution mode"
        )
        
        orchestration_group.add_argument(
            "--background-e2e",
            action="store_true",
            help="Execute E2E tests in background only"
        )
    
    # Add Master Orchestration specific arguments (non-conflicting)
    if orchestration_config.master_orchestration_available:
        if not orchestration_config.orchestrator_available:
            orchestration_group = parser.add_argument_group('Master Orchestration System')
        else:
            # Add to existing orchestration group
            for group in parser._action_groups:
                if group.title == 'Test Orchestrator Options':
                    orchestration_group = group
                    break
            else:
                orchestration_group = parser.add_argument_group('Master Orchestration System')
        
        orchestration_group.add_argument(
            "--orchestration-status",
            action="store_true",
            help="Show current orchestration status and exit"
        )
        
        orchestration_group.add_argument(
            "--enable-monitoring",
            action="store_true",
            default=True,
            help="Enable resource monitoring during execution"
        )
        
        orchestration_group.add_argument(
            "--websocket-thread-id",
            type=str,
            help="WebSocket thread ID for real-time updates"
        )
        
        orchestration_group.add_argument(
            "--master-orchestration",
            action="store_true",
            help="Use new Master Orchestration Controller (enhanced version)"
        )
    
    args = parser.parse_args()
    
    # Set Docker pull policy in environment for UnifiedDockerManager
    # This prevents Docker Hub rate limit issues by controlling when images are pulled
    if hasattr(args, 'docker_pull_policy'):
        os.environ['DOCKER_PULL_POLICY'] = args.docker_pull_policy
        if args.docker_pull_policy == 'never':
            print("[U+2139][U+FE0F] Docker pull policy set to 'never' - will only use locally cached images")
        elif args.docker_pull_policy == 'always':
            print(" WARNING: [U+FE0F] Docker pull policy set to 'always' - may hit Docker Hub rate limits")
    
    # Handle special operations
    if args.list_categories:
        config_loader = CategoryConfigLoader(PROJECT_ROOT)
        category_system = config_loader.create_category_system()
        
        print(f"\1{'='*60}")
        print("AVAILABLE TEST CATEGORIES")
        print(f"{'='*60}")
        
        for priority in CategoryPriority:
            categories = category_system.get_categories_by_priority(priority)
            if categories:
                print(f"\1{priority.name} Priority:")
                for category in sorted(categories, key=lambda x: x.name):
                    print(f"  {category.name:15} - {category.description}")
                    if category.dependencies:
                        print(f"                    Dependencies: {', '.join(category.dependencies)}")
                    if category.conflicts:
                        print(f"                    Conflicts: {', '.join(category.conflicts)}")
                    print(f"                    Est. Duration: {category.estimated_duration}")
        
        print(f"\1Total Categories: {len(category_system.categories)}")
        return 0
    
    if args.show_category_stats:
        config_loader = CategoryConfigLoader(PROJECT_ROOT)
        category_system = config_loader.create_category_system()
        stats = category_system.get_category_statistics()
        
        print(f"\1{'='*60}")
        print("CATEGORY STATISTICS")
        print(f"{'='*60}")
        print(f"Total Categories: {stats['total_categories']}")
        print(f"Parallel Safe: {stats['parallel_safe']}")
        print(f"Require Real Services: {stats['requires_real_services']}")
        print(f"Require Real LLM: {stats['requires_real_llm']}")
        print(f"Memory Intensive: {stats['memory_intensive']}")
        print(f"CPU Intensive: {stats['cpu_intensive']}")
        print(f"Database Dependent: {stats['database_dependent']}")
        print(f"Average Duration: {stats['average_estimated_duration']}")
        print(f"Categories with History: {stats['categories_with_history']}")
        print(f"Average Success Rate: {stats['average_success_rate']:.2%}")
        
        print(f"\1By Priority:")
        for priority, count in stats['by_priority'].items():
            print(f"  {priority:10}: {count}")
        
        print(f"\1By Type:")
        for cat_type, count in stats['by_type'].items():
            print(f"  {cat_type:12}: {count}")
        
        return 0
    
    # PERFORMANCE: Handle fast collection mode early (skip validation)
    if hasattr(args, 'fast_collection') and args.fast_collection:
        print("[INFO] Fast collection mode - running streamlined test discovery")
        
        # Create a simple runner for fast collection
        from pathlib import Path
        
        # Determine test pattern
        pattern = getattr(args, 'pattern', '*')
        if not pattern:
            pattern = '*'

        # Create proper glob pattern - avoid creating invalid patterns like "**.py"
        if pattern == '*':
            glob_pattern = "**/*test*.py"
        else:
            # Clean pattern and create safe glob
            clean_pattern = pattern.replace('*', '')
            if clean_pattern:
                glob_pattern = f"**/*{clean_pattern}*.py"
            else:
                glob_pattern = "**/*test*.py"

        # Fast test discovery
        test_dirs = [
            PROJECT_ROOT / "netra_backend" / "tests",
            PROJECT_ROOT / "tests"
        ]

        total_files = 0
        for test_dir in test_dirs:
            if test_dir.exists():
                files = list(test_dir.rglob(glob_pattern))
                valid_files = [f for f in files if f.is_file() and 'test' in f.name]
                total_files += len(valid_files)
                print(f"Found {len(valid_files)} test files in {test_dir.name}")
        
        print(f"✅ Fast collection completed: {total_files} test files discovered")
        return 0
    
    # Run validation by default unless --no-validate is specified
    if not getattr(args, 'no_validate', False):
        validator = TestValidation()
        full_mode = getattr(args, 'full_validate', False)
        mode_desc = "full" if full_mode else "quick"
        print(f"Running comprehensive test validation ({mode_desc} mode)...")
        
        # 1. Syntax validation
        print("\n=== SYNTAX VALIDATION ===")
        syntax_result = validator.validate_syntax(quick_mode=not full_mode)
        if syntax_result["success"]:
            mode_info = f" ({syntax_result.get('quick_mode', 'unknown')} mode)" if 'quick_mode' in syntax_result else ""
            print(f" PASS:  Syntax validation passed: {syntax_result['files_checked']} files checked{mode_info}")
        else:
            print(f" FAIL:  Syntax validation failed: {len(syntax_result['syntax_errors'])} errors found")
            for error in syntax_result['syntax_errors']:
                print(f"  - {error['file']}: {error['error']}")
            return 1
        
        # 2. Test structure validation
        print("\n=== TEST STRUCTURE VALIDATION ===")
        print("Test structure validation not fully implemented yet.")
        
        print("\n PASS:  All validations passed!")
        
        # If user ran ONLY validation (no other test arguments), exit here
        # Check if user provided any actual test execution arguments
        test_execution_args = [
            args.category, args.categories, getattr(args, 'path', None), getattr(args, 'keyword', None), 
            getattr(args, 'show_category_stats', False),
            getattr(args, 'master_orchestration', False),
            getattr(args, 'orchestration_status', False),
            getattr(args, 'use_layers', False),
            getattr(args, 'show_layers', False),
            getattr(args, 'cleanup_old_environments', False)
        ]
        
        # If no test execution arguments provided, exit after validation
        if not any(test_execution_args):
            return 0
        
        print("\n=== PROCEEDING TO TEST EXECUTION ===")
    else:
        print(" WARNING: [U+FE0F]  Skipping validation (--no-validate specified)")
    
    # NEW: Handle Master Orchestration Controller execution first
    if orchestration_config.master_orchestration_available and (
        getattr(args, 'master_orchestration', False) or
        getattr(args, 'orchestration_status', False) or
        (getattr(args, 'use_layers', False) and getattr(args, 'websocket_thread_id', None))
    ):
        # Use new orchestration system
        import asyncio
        return asyncio.run(execute_orchestration_mode(args))
    
    # Handle orchestrator execution if requested (legacy orchestrator)
    if orchestration_config.orchestrator_available and hasattr(args, 'use_layers') and args.use_layers:
        # Use async executor for orchestrator
        import asyncio
        return asyncio.run(execute_with_orchestrator(args))
    
    # Handle orchestrator show commands (legacy orchestrator)
    if orchestration_config.orchestrator_available and hasattr(args, 'show_layers') and args.show_layers:
        import asyncio
        return asyncio.run(execute_with_orchestrator(args))
    
    # Handle background E2E commands if requested
    if orchestration_config.background_e2e_available:
        background_exit_code = handle_background_e2e_commands(args, PROJECT_ROOT)
        if background_exit_code is not None:
            return background_exit_code
    
    # Clean up old Docker environments if requested
    if hasattr(args, 'cleanup_old_environments') and args.cleanup_old_environments:
        if CENTRALIZED_DOCKER_AVAILABLE:
            print("[INFO] Cleaning up old Docker test environments...")
            manager = UnifiedDockerManager()
            manager.cleanup_old_environments(max_age_hours=4)
            print("[INFO] Cleanup complete")
    
    # Set Docker environment variables from args
    env = get_env()
    # DEDICATED is now the default, no need for TEST_USE_SHARED_DOCKER
    if hasattr(args, 'docker_production') and args.docker_production:
        env.set('TEST_USE_PRODUCTION_IMAGES', 'true', 'docker_args')
    
    # Handle staging-e2e flag first (Docker-independent e2e testing)
    if hasattr(args, 'staging_e2e') and args.staging_e2e:
        print("[INFO] Running staging-based E2E tests (Docker-independent validation)")
        print("[INFO] Validating business-critical $500K+ ARR functionality via staging environment")

        import subprocess
        staging_tests = [
            "tests/e2e/staging/test_priority1_critical.py",
            "tests/e2e/staging/test_real_agent_execution_staging.py",
            "tests/mission_critical/test_staging_websocket_agent_events.py"
        ]

        cmd = [sys.executable, "-m", "pytest"] + staging_tests + ["-v", "--tb=short"]
        print(f"[INFO] Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        sys.exit(result.returncode)

    # CRITICAL: Set USE_REAL_SERVICES early BEFORE any test imports or TestRunner creation
    # This ensures environment isolation respects real services flag from the start
    running_e2e = (args.category in ['e2e', 'websocket', 'agent'] if args.category else False) or \
                  (args.categories and any(cat in ['e2e', 'websocket', 'agent'] for cat in args.categories))
    
    # WINDOWS SAFETY: Detect Windows and use safe runner for e2e tests
    import platform
    if platform.system() == 'Windows' and running_e2e:
        print("[WARNING] Windows detected with e2e tests - using safe runner to prevent Docker crash")
        print("[INFO] See tests/e2e/WINDOWS_SAFE_TESTING_GUIDE.md for details")
        
        # Use the safe runner script for e2e tests on Windows
        import subprocess
        safe_runner = PROJECT_ROOT / 'tests' / 'e2e' / 'run_safe_windows.py'
        if safe_runner.exists():
            # Build command for safe runner
            cmd = [sys.executable, str(safe_runner)]
            if args.category == 'e2e':
                # Run all e2e tests safely
                pass  # Default behavior
            elif args.categories and 'e2e' in args.categories:
                # Run specific e2e tests
                pass  # Will handle all e2e tests
            
            print(f"[INFO] Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=PROJECT_ROOT)
            sys.exit(result.returncode)
        else:
            print("[WARNING] Safe runner not found, proceeding with caution...")
            # Set safety environment variables
            env.set('PYTEST_XDIST_WORKER_COUNT', '1', 'windows_safety')
            env.set('PYTEST_TIMEOUT', '120', 'windows_safety')
            env.set('PYTHONDONTWRITEBYTECODE', '1', 'windows_safety')
                  
    if args.env in ['staging', 'dev'] or args.real_services or running_e2e:
        env.set('USE_REAL_SERVICES', 'true', 'main_early_setup')
        env.set('SKIP_MOCKS', 'true', 'main_early_setup')
        print(f"[INFO] USE_REAL_SERVICES set to true early in process (env={args.env}, real_services={args.real_services}, running_e2e={running_e2e})")
    else:
        env.set('USE_REAL_SERVICES', 'false', 'main_early_setup')
        env.set('SKIP_MOCKS', 'false', 'main_early_setup')
    
    # Run tests with traditional category system
    runner = UnifiedTestRunner()
    try:
        exit_code = runner.run(args)
        
        # Show Docker statistics if requested
        if hasattr(args, 'docker_stats') and args.docker_stats and runner.docker_manager:
            stats = runner.docker_manager.get_statistics()
            print("\n[DOCKER STATISTICS]")
            print(json.dumps(stats, indent=2))
        
        return exit_code
    finally:
        # Clean up service orchestrator if it was used
        if hasattr(runner, 'service_orchestrator') and runner.service_orchestrator:
            try:
                if not (hasattr(args, 'no_service_cleanup') and args.no_service_cleanup):
                    print("[INFO] Cleaning up auto-started services...")
                    import asyncio
                    if asyncio.get_event_loop().is_running():
                        # We're in an async context - need to use thread
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            executor.submit(
                                lambda: asyncio.run(runner.service_orchestrator.teardown_after_tests())
                            ).result(timeout=30)
                    else:
                        asyncio.run(runner.service_orchestrator.teardown_after_tests())
                    print("[SUCCESS] Service cleanup completed")
                else:
                    print("[INFO] Service cleanup skipped (--no-service-cleanup)")
            except Exception as e:
                print(f"[WARNING] Service cleanup failed: {e}")
        
        # Clean up Docker environment unless --docker-no-cleanup specified
        if not (hasattr(args, 'docker_no_cleanup') and args.docker_no_cleanup):
            runner._cleanup_docker_environment()


if __name__ == "__main__":
    sys.exit(main())
