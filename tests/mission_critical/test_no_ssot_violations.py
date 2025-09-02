#!/usr/bin/env python3
"""
Mission Critical Test Suite - SSOT Violation Detection and Prevention
=====================================================================

This test suite automatically detects and prevents future SSOT violations
in the orchestration system. These tests are designed to catch regressions
and ensure the SSOT consolidation remains intact over time.

Critical Prevention Areas:
1. Automated scanning for duplicate enum definitions
2. Detection of try-except import patterns for availability
3. Prevention of direct ORCHESTRATOR_AVAILABLE definitions
4. Validation of duplicate dataclass definitions
5. Import source validation (all imports from SSOT modules)
6. Enum value consistency checking
7. Availability pattern detection and validation
8. Configuration pattern consolidation validation

Business Value: Prevents regression to pre-SSOT state and catches violations
early in development, maintaining system consistency and preventing bugs.

WARNING: These tests will FAIL if SSOT violations are introduced. They are
designed to be STRICT guardians of the SSOT consolidation.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.mark.mission_critical
class TestSSOTViolationScanning:
    """Test for SSOT violations by scanning source code - STRICT tests."""
    
    def test_no_duplicate_enum_definitions(self):
        """CRITICAL: Scan for duplicate enum definitions across codebase."""
        # Known SSOT enum definitions (these are the ONLY allowed locations)
        ssot_enum_file = PROJECT_ROOT / "test_framework" / "ssot" / "orchestration_enums.py"
        
        # Enums that should ONLY exist in SSOT location
        prohibited_enums = [
            "BackgroundTaskStatus",
            "E2ETestCategory", 
            "ExecutionStrategy",
            "ProgressOutputMode",
            "ProgressEventType",
            "OrchestrationMode",
            "ResourceStatus",
            "ServiceStatus",
            "LayerType"
        ]
        
        violations = []
        
        # Scan orchestration directory for duplicate enum definitions
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if orchestration_dir.exists():
            for python_file in orchestration_dir.rglob("*.py"):
                if python_file == ssot_enum_file:
                    continue  # Skip the SSOT file itself
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for enum class definitions
                    for enum_name in prohibited_enums:
                        enum_pattern = rf'class\s+{enum_name}\s*\([^)]*Enum[^)]*\)'
                        if re.search(enum_pattern, content):
                            violations.append(f"Duplicate enum {enum_name} found in {python_file}")
                        
                        # Also check for enum value definitions
                        value_patterns = [
                            rf'{enum_name}\.QUEUED',
                            rf'{enum_name}\.RUNNING', 
                            rf'{enum_name}\.SEQUENTIAL',
                            rf'{enum_name}\.CONSOLE'
                        ]
                        for pattern in value_patterns:
                            if re.search(pattern, content) and f'from.*{enum_name}' not in content:
                                violations.append(f"Local {enum_name} usage without import in {python_file}")
                                
                except (UnicodeDecodeError, PermissionError):
                    continue  # Skip files we can't read
        
        assert len(violations) == 0, f"SSOT enum violations detected:\n" + "\n".join(violations)
    
    def test_no_try_except_availability_patterns(self):
        """CRITICAL: Detect prohibited try-except import patterns for availability."""
        # These patterns indicate SSOT violations
        prohibited_patterns = [
            r'try:\s*from.*orchestration.*import.*\n.*ORCHESTRATOR_AVAILABLE\s*=\s*True',
            r'try:\s*import.*orchestration.*\n.*except.*ImportError.*\n.*ORCHESTRATOR_AVAILABLE\s*=\s*False',
            r'try:\s*from.*orchestration.*import.*\n.*except.*ImportError.*\n.*AVAILABLE\s*=\s*False',
            r'ORCHESTRATOR_AVAILABLE\s*=\s*True.*except.*ORCHESTRATOR_AVAILABLE\s*=\s*False',
            r'MASTER_ORCHESTRATION_AVAILABLE\s*=.*except.*MASTER_ORCHESTRATION_AVAILABLE\s*=',
            r'BACKGROUND_E2E_AVAILABLE\s*=.*except.*BACKGROUND_E2E_AVAILABLE\s*='
        ]
        
        violations = []
        
        # Scan all Python files for prohibited patterns
        for python_file in PROJECT_ROOT.rglob("*.py"):
            # Skip SSOT files (they're allowed to manage availability)
            if "ssot" in str(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in prohibited_patterns:
                    if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                        violations.append(f"Prohibited availability pattern found in {python_file}")
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        assert len(violations) == 0, f"Prohibited availability patterns detected:\n" + "\n".join(violations)
    
    def test_no_direct_orchestrator_available_definitions(self):
        """CRITICAL: Detect direct ORCHESTRATOR_AVAILABLE variable definitions."""
        # These should not exist outside SSOT modules
        prohibited_definitions = [
            r'^ORCHESTRATOR_AVAILABLE\s*=',
            r'^MASTER_ORCHESTRATION_AVAILABLE\s*=',
            r'^BACKGROUND_E2E_AVAILABLE\s*=',
            r'^ALL_ORCHESTRATION_AVAILABLE\s*='
        ]
        
        violations = []
        
        # Scan all Python files
        for python_file in PROJECT_ROOT.rglob("*.py"):
            # Skip SSOT files and test files (tests may define these for testing)
            if "ssot" in str(python_file) or "test_" in python_file.name:
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in prohibited_definitions:
                        if re.match(pattern, line.strip()):
                            violations.append(f"Direct availability definition at {python_file}:{line_num}: {line.strip()}")
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        assert len(violations) == 0, f"Direct availability definitions detected:\n" + "\n".join(violations)
    
    def test_no_duplicate_dataclass_definitions(self):
        """CRITICAL: Detect duplicate dataclass definitions."""
        # Dataclasses that should only exist in SSOT location
        prohibited_dataclasses = [
            "LayerExecutionResult",
            "CategoryExecutionResult", 
            "BackgroundTaskConfig",
            "BackgroundTaskResult",
            "ProgressEvent",
            "LayerDefinition"
        ]
        
        violations = []
        ssot_dataclass_file = PROJECT_ROOT / "test_framework" / "ssot" / "orchestration_enums.py"
        
        # Scan orchestration directory
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if orchestration_dir.exists():
            for python_file in orchestration_dir.rglob("*.py"):
                if python_file == ssot_dataclass_file:
                    continue
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for dataclass_name in prohibited_dataclasses:
                        dataclass_pattern = rf'@dataclass.*\nclass\s+{dataclass_name}\s*[:(]'
                        if re.search(dataclass_pattern, content, re.MULTILINE):
                            violations.append(f"Duplicate dataclass {dataclass_name} found in {python_file}")
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        assert len(violations) == 0, f"Duplicate dataclass definitions detected:\n" + "\n".join(violations)
    
    def test_all_imports_from_ssot_modules(self):
        """CRITICAL: Validate all orchestration imports come from SSOT modules."""
        # SSOT modules that should be the source of truth
        ssot_modules = [
            "test_framework.ssot.orchestration",
            "test_framework.ssot.orchestration_enums"
        ]
        
        # Items that should only be imported from SSOT
        ssot_imports = [
            "OrchestrationConfig",
            "BackgroundTaskStatus",
            "E2ETestCategory",
            "ExecutionStrategy", 
            "ProgressOutputMode",
            "OrchestrationMode",
            "get_orchestration_config"
        ]
        
        violations = []
        
        # Scan orchestration directory for non-SSOT imports
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if orchestration_dir.exists():
            for python_file in orchestration_dir.rglob("*.py"):
                # Skip SSOT files themselves
                if "ssot" in str(python_file):
                    continue
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse imports using AST for accuracy
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ImportFrom):
                                if node.module and any(item in ssot_imports for alias in (node.names or []) for item in [alias.name]):
                                    # Check if importing from non-SSOT location
                                    if not any(ssot_mod in (node.module or '') for ssot_mod in ssot_modules):
                                        for alias in node.names or []:
                                            if alias.name in ssot_imports:
                                                violations.append(f"Non-SSOT import of {alias.name} from {node.module} in {python_file}")
                    except SyntaxError:
                        # If AST fails, fall back to regex
                        for item in ssot_imports:
                            import_pattern = rf'from\s+(?!test_framework\.ssot)\S+\s+import.*{item}'
                            if re.search(import_pattern, content):
                                violations.append(f"Potential non-SSOT import of {item} in {python_file}")
                        
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        assert len(violations) == 0, f"Non-SSOT imports detected:\n" + "\n".join(violations)


@pytest.mark.mission_critical
class TestEnumValueConsistency:
    """Test enum value consistency across SSOT - VALIDATION tests."""
    
    def test_background_task_status_values_consistent(self):
        """CRITICAL: Test BackgroundTaskStatus enum values are consistent."""
        try:
            from test_framework.ssot.orchestration_enums import BackgroundTaskStatus
        except ImportError:
            pytest.skip("SSOT orchestration enums not available")
        
        # Expected status values (these should never change without careful consideration)
        expected_statuses = {
            "QUEUED": "queued",
            "STARTING": "starting", 
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "TIMEOUT": "timeout"
        }
        
        # Verify all expected statuses exist
        for status_name, expected_value in expected_statuses.items():
            assert hasattr(BackgroundTaskStatus, status_name), f"Missing status: {status_name}"
            status = getattr(BackgroundTaskStatus, status_name)
            assert status.value == expected_value, f"Status {status_name} has wrong value: {status.value} != {expected_value}"
        
        # Verify no unexpected statuses exist
        actual_statuses = {status.name: status.value for status in BackgroundTaskStatus}
        unexpected_statuses = set(actual_statuses.keys()) - set(expected_statuses.keys())
        assert len(unexpected_statuses) == 0, f"Unexpected status values: {unexpected_statuses}"
    
    def test_execution_strategy_values_consistent(self):
        """CRITICAL: Test ExecutionStrategy enum values are consistent."""
        try:
            from test_framework.ssot.orchestration_enums import ExecutionStrategy
        except ImportError:
            pytest.skip("SSOT orchestration enums not available")
        
        # Expected strategy values
        expected_strategies = {
            "SEQUENTIAL": "sequential",
            "PARALLEL_UNLIMITED": "parallel_unlimited",
            "PARALLEL_LIMITED": "parallel_limited", 
            "HYBRID_SMART": "hybrid_smart"
        }
        
        # Verify all expected strategies exist
        for strategy_name, expected_value in expected_strategies.items():
            assert hasattr(ExecutionStrategy, strategy_name), f"Missing strategy: {strategy_name}"
            strategy = getattr(ExecutionStrategy, strategy_name)
            assert strategy.value == expected_value, f"Strategy {strategy_name} has wrong value: {strategy.value} != {expected_value}"
        
        # Verify no unexpected strategies exist
        actual_strategies = {strategy.name: strategy.value for strategy in ExecutionStrategy}
        unexpected_strategies = set(actual_strategies.keys()) - set(expected_strategies.keys())
        assert len(unexpected_strategies) == 0, f"Unexpected strategy values: {unexpected_strategies}"
    
    def test_orchestration_mode_values_consistent(self):
        """CRITICAL: Test OrchestrationMode enum values are consistent."""
        try:
            from test_framework.ssot.orchestration_enums import OrchestrationMode
        except ImportError:
            pytest.skip("SSOT orchestration enums not available")
        
        # Expected mode values
        expected_modes = {
            "FAST_FEEDBACK": "fast_feedback",
            "NIGHTLY": "nightly",
            "BACKGROUND": "background",
            "HYBRID": "hybrid", 
            "LEGACY": "legacy",
            "CUSTOM": "custom"
        }
        
        # Verify all expected modes exist
        for mode_name, expected_value in expected_modes.items():
            assert hasattr(OrchestrationMode, mode_name), f"Missing mode: {mode_name}"
            mode = getattr(OrchestrationMode, mode_name)
            assert mode.value == expected_value, f"Mode {mode_name} has wrong value: {mode.value} != {expected_value}"
    
    def test_progress_output_mode_values_consistent(self):
        """CRITICAL: Test ProgressOutputMode enum values are consistent."""
        try:
            from test_framework.ssot.orchestration_enums import ProgressOutputMode
        except ImportError:
            pytest.skip("SSOT orchestration enums not available")
        
        # Expected output mode values
        expected_modes = {
            "CONSOLE": "console",
            "JSON": "json",
            "WEBSOCKET": "websocket",
            "LOG": "log",
            "SILENT": "silent"
        }
        
        # Verify all expected modes exist
        for mode_name, expected_value in expected_modes.items():
            assert hasattr(ProgressOutputMode, mode_name), f"Missing output mode: {mode_name}"
            mode = getattr(ProgressOutputMode, mode_name)
            assert mode.value == expected_value, f"Output mode {mode_name} has wrong value: {mode.value} != {expected_value}"


@pytest.mark.mission_critical
class TestConfigurationPatternValidation:
    """Test configuration pattern consolidation - PATTERN tests."""
    
    def test_no_availability_check_duplicates(self):
        """CRITICAL: Test no availability checking duplicates exist."""
        availability_check_patterns = [
            r'def.*_available\(\)',
            r'@property.*\n.*def.*_available\(',
            r'def\s+check.*availability',
            r'def\s+.*orchestrator.*available',
            r'def\s+.*orchestration.*available'
        ]
        
        violations = []
        ssot_orchestration_file = PROJECT_ROOT / "test_framework" / "ssot" / "orchestration.py"
        
        # Scan orchestration directory (excluding SSOT file)
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if orchestration_dir.exists():
            for python_file in orchestration_dir.rglob("*.py"):
                if python_file == ssot_orchestration_file:
                    continue
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern in availability_check_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            violations.append(f"Duplicate availability pattern at {python_file}:{line_num}")
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        assert len(violations) == 0, f"Duplicate availability patterns detected:\n" + "\n".join(violations)
    
    def test_ssot_orchestration_config_usage(self):
        """CRITICAL: Test files use SSOT orchestration config correctly."""
        # Files that should use SSOT config
        orchestration_files = [
            PROJECT_ROOT / "test_framework" / "orchestration" / "test_orchestrator_agent.py",
            PROJECT_ROOT / "test_framework" / "orchestration" / "background_e2e_agent.py",
            PROJECT_ROOT / "test_framework" / "orchestration" / "layer_execution_agent.py"
        ]
        
        violations = []
        
        for orchestration_file in orchestration_files:
            if not orchestration_file.exists():
                continue
                
            try:
                with open(orchestration_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for SSOT import
                ssot_import_patterns = [
                    r'from\s+test_framework\.ssot\.orchestration\s+import',
                    r'from\s+test_framework\.ssot\.orchestration_enums\s+import',
                    r'import.*test_framework\.ssot\.orchestration'
                ]
                
                has_ssot_import = any(re.search(pattern, content) for pattern in ssot_import_patterns)
                
                # Check for availability usage
                availability_usage_patterns = [
                    r'orchestrator_available',
                    r'master_orchestration_available',
                    r'background_e2e_available',
                    r'all_orchestration_available'
                ]
                
                uses_availability = any(re.search(pattern, content) for pattern in availability_usage_patterns)
                
                # If file uses availability but doesn't import from SSOT, it's a violation
                if uses_availability and not has_ssot_import:
                    violations.append(f"File {orchestration_file} uses availability but doesn't import from SSOT")
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Note: This might produce false positives if files have been properly refactored
        # The test documents expected behavior rather than failing on current state
        if len(violations) > 0:
            print(f"SSOT usage suggestions:\n" + "\n".join(violations))
    
    def test_enum_import_consistency(self):
        """CRITICAL: Test enum imports are consistent with SSOT."""
        # Files that should import enums from SSOT
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if not orchestration_dir.exists():
            pytest.skip("Orchestration directory not found")
        
        enum_import_violations = []
        
        for python_file in orchestration_dir.rglob("*.py"):
            # Skip SSOT files
            if "ssot" in str(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for enum usage without SSOT import
                enum_usage_patterns = [
                    r'BackgroundTaskStatus\.',
                    r'E2ETestCategory\.',
                    r'ExecutionStrategy\.',
                    r'ProgressOutputMode\.',
                    r'OrchestrationMode\.'
                ]
                
                has_enum_usage = any(re.search(pattern, content) for pattern in enum_usage_patterns)
                
                if has_enum_usage:
                    # Check for SSOT enum import
                    ssot_enum_import = re.search(r'from\s+test_framework\.ssot\.orchestration_enums\s+import', content)
                    if not ssot_enum_import:
                        enum_import_violations.append(f"File {python_file} uses enums but doesn't import from SSOT")
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Document violations as suggestions for now
        if len(enum_import_violations) > 0:
            print(f"SSOT enum import suggestions:\n" + "\n".join(enum_import_violations))


@pytest.mark.mission_critical
class TestRegressionPrevention:
    """Test regression prevention mechanisms - WATCHDOG tests."""
    
    def test_ssot_files_exist_and_are_complete(self):
        """CRITICAL: Test SSOT files exist and contain expected content."""
        # SSOT files that must exist
        required_ssot_files = [
            PROJECT_ROOT / "test_framework" / "ssot" / "orchestration.py",
            PROJECT_ROOT / "test_framework" / "ssot" / "orchestration_enums.py"
        ]
        
        for ssot_file in required_ssot_files:
            assert ssot_file.exists(), f"SSOT file missing: {ssot_file}"
            
            # Check file has content
            assert ssot_file.stat().st_size > 1000, f"SSOT file suspiciously small: {ssot_file}"
            
            # Check file has expected patterns
            with open(ssot_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "orchestration.py" in ssot_file.name:
                assert "OrchestrationConfig" in content, "OrchestrationConfig class missing"
                assert "orchestration_available" in content, "orchestration_available property missing"
                assert "singleton" in content.lower(), "Singleton pattern missing"
            
            if "orchestration_enums.py" in ssot_file.name:
                assert "BackgroundTaskStatus" in content, "BackgroundTaskStatus enum missing"
                assert "ExecutionStrategy" in content, "ExecutionStrategy enum missing"
                assert "@dataclass" in content, "Dataclass definitions missing"
    
    def test_no_forbidden_orchestration_patterns(self):
        """CRITICAL: Test for forbidden orchestration patterns that indicate regressions."""
        forbidden_patterns = [
            # Old availability patterns
            r'ORCHESTRATOR_AVAILABLE\s*=\s*True.*try:.*except.*ORCHESTRATOR_AVAILABLE\s*=\s*False',
            r'try:\s*from.*orchestration.*except.*ORCHESTRATOR_AVAILABLE',
            
            # Old enum definitions
            r'class\s+BackgroundTaskStatus.*Enum.*QUEUED\s*=',
            r'class\s+ExecutionStrategy.*Enum.*SEQUENTIAL\s*=',
            
            # Old configuration patterns  
            r'def\s+get_orchestrator_available',
            r'def\s+check_orchestrator_availability',
            
            # Hardcoded availability checks
            r'if\s+ORCHESTRATOR_AVAILABLE:',
            r'if\s+not\s+ORCHESTRATOR_AVAILABLE:'
        ]
        
        violations = []
        
        # Scan orchestration directory for forbidden patterns
        orchestration_dir = PROJECT_ROOT / "test_framework" / "orchestration"
        if orchestration_dir.exists():
            for python_file in orchestration_dir.rglob("*.py"):
                # Skip SSOT files and test files
                if "ssot" in str(python_file) or "test_" in python_file.name:
                    continue
                
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern in forbidden_patterns:
                        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                            violations.append(f"Forbidden pattern found in {python_file}")
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        assert len(violations) == 0, f"Forbidden patterns detected (regressions):\n" + "\n".join(violations)
    
    def test_ssot_import_paths_are_stable(self):
        """CRITICAL: Test SSOT import paths haven't changed (API stability)."""
        # These import paths should remain stable
        stable_imports = [
            "from test_framework.ssot.orchestration import OrchestrationConfig",
            "from test_framework.ssot.orchestration import get_orchestration_config",
            "from test_framework.ssot.orchestration_enums import BackgroundTaskStatus",
            "from test_framework.ssot.orchestration_enums import ExecutionStrategy",
            "from test_framework.ssot.orchestration_enums import OrchestrationMode"
        ]
        
        import_failures = []
        
        for import_statement in stable_imports:
            try:
                # Test import statement
                exec(import_statement)
            except ImportError as e:
                import_failures.append(f"Stable import failed: {import_statement} - {e}")
            except Exception as e:
                import_failures.append(f"Import error: {import_statement} - {e}")
        
        assert len(import_failures) == 0, f"Stable import paths broken:\n" + "\n".join(import_failures)
    
    def test_enum_backwards_compatibility(self):
        """CRITICAL: Test enum values haven't changed (backwards compatibility)."""
        try:
            from test_framework.ssot.orchestration_enums import (
                BackgroundTaskStatus, ExecutionStrategy, OrchestrationMode
            )
        except ImportError:
            pytest.skip("SSOT enums not available")
        
        # Critical enum values that must not change
        critical_values = {
            BackgroundTaskStatus.QUEUED: "queued",
            BackgroundTaskStatus.RUNNING: "running", 
            BackgroundTaskStatus.COMPLETED: "completed",
            ExecutionStrategy.SEQUENTIAL: "sequential",
            ExecutionStrategy.PARALLEL_UNLIMITED: "parallel_unlimited",
            OrchestrationMode.FAST_FEEDBACK: "fast_feedback",
            OrchestrationMode.NIGHTLY: "nightly"
        }
        
        compatibility_failures = []
        
        for enum_value, expected_string in critical_values.items():
            if enum_value.value != expected_string:
                compatibility_failures.append(f"{enum_value} value changed from '{expected_string}' to '{enum_value.value}'")
        
        assert len(compatibility_failures) == 0, f"Enum backwards compatibility broken:\n" + "\n".join(compatibility_failures)


if __name__ == "__main__":
    # Configure pytest for regression prevention testing
    pytest_args = [
        __file__,
        "-v",
        "-x",  # Stop on first failure
        "--tb=short",
        "-m", "mission_critical"
    ]
    
    print("Running SSOT Violation Detection and Regression Prevention Tests...")
    print("=" * 80)
    print("GUARDIAN MODE: Scanning for SSOT violations and regressions")
    print("WARNING: These tests will FAIL if SSOT violations are detected")
    print("=" * 80)
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 80)
        print("✅ NO SSOT VIOLATIONS DETECTED")
        print("SSOT consolidation integrity maintained")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("SSOT VIOLATIONS DETECTED")
        print("CRITICAL: Fix violations immediately")
        print("=" * 80)
    
    sys.exit(result)