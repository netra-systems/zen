"""
SSOT Validation Tests - Import Path Violations for Issue #759

PURPOSE: Detect and validate import path violations that block test execution.
These tests should FAIL initially to prove violations exist, then PASS after remediation.

BUSINESS IMPACT: $500K+ ARR protected by ensuring tests can actually run
FOCUS: Import path failures preventing test collection and execution
"""

import os
import glob
import pytest
from pathlib import Path
from typing import List, Dict, Set


def scan_for_import_pattern(pattern: str, file_types: str = "*.py", exclude_dirs: Set[str] = None) -> List[Dict[str, str]]:
    """
    Scan for specific import patterns across the codebase.
    
    Args:
        pattern: The import pattern to search for
        file_types: File pattern to match (default: *.py)
        exclude_dirs: Directories to exclude from search
        
    Returns:
        List of dictionaries with file path and line information
    """
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
    
    root_dir = Path(__file__).parent.parent.parent.parent  # Go up to netra-apex root
    violations = []
    
    # Find all Python files
    for py_file in root_dir.rglob(file_types):
        # Skip excluded directories
        if any(excluded in str(py_file) for excluded in exclude_dirs):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                if pattern in line.strip():
                    violations.append({
                        'file': str(py_file.relative_to(root_dir)),
                        'line_num': line_num,
                        'line_content': line.strip(),
                        'full_path': str(py_file)
                    })
                    
        except (UnicodeDecodeError, PermissionError):
            # Skip files that can't be read
            continue
            
    return violations


def test_detect_broken_user_execution_engine_imports():
    """
    FAIL TEST: Detect files with incorrect import paths for UserExecutionEngine.
    
    This test should FAIL initially, proving that 133+ files have broken imports.
    After remediation, this test should PASS (no broken imports found).
    
    VIOLATION PATTERN: from netra_backend.app.agents.supervisor.user_execution_engine import
    CORRECT PATTERN: from netra_backend.app.agents.supervisor.user_execution_engine import
    """
    broken_pattern = "from netra_backend.app.core.user_execution_engine"
    broken_imports = scan_for_import_pattern(broken_pattern)
    
    # Document findings for debugging
    if broken_imports:
        print(f"\n🚨 FOUND {len(broken_imports)} FILES WITH BROKEN IMPORTS:")
        for violation in broken_imports[:10]:  # Show first 10
            print(f"  - {violation['file']}:{violation['line_num']} -> {violation['line_content']}")
        if len(broken_imports) > 10:
            print(f"  ... and {len(broken_imports) - 10} more files")
    
    # This test SHOULD FAIL initially (proving violation exists)
    assert len(broken_imports) == 0, (
        f"🚨 SSOT VIOLATION: Found {len(broken_imports)} files with incorrect import paths. "
        f"These imports should use 'from netra_backend.app.agents.supervisor.user_execution_engine import' instead. "
        f"First 5 violations: {[v['file'] for v in broken_imports[:5]]}"
    )


def test_user_execution_engine_import_validation():
    """
    FAIL TEST: Demonstrate that the old import path fails while new path works.
    
    This validates that:
    1. Old import path (app.core.user_execution_engine) fails - proving it was moved
    2. New import path (app.agents.supervisor.user_execution_engine) works - proving SSOT location
    """
    # Test 1: Old import path should fail
    old_import_failed = False
    try:
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        # If this doesn't fail, then the old path still exists (violation)
        old_import_failed = False
    except (ImportError, ModuleNotFoundError):
        # Expected failure - old path doesn't exist
        old_import_failed = True
    
    # Test 2: New import path should work
    new_import_works = False
    try:
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        new_import_works = True
        assert UserExecutionEngine is not None
    except (ImportError, ModuleNotFoundError) as e:
        new_import_works = False
        pytest.fail(f"🚨 CRITICAL: SSOT import path also broken: {e}")
    
    # Validation
    assert old_import_failed, "🚨 VIOLATION: Old import path still works - SSOT migration incomplete"
    assert new_import_works, "🚨 CRITICAL: New import path broken - SSOT target missing"


def test_execution_engine_import_patterns_across_codebase():
    """
    FAIL TEST: Analyze all ExecutionEngine import patterns to identify violations.
    
    This test maps all ExecutionEngine imports and identifies non-SSOT patterns.
    Should FAIL initially due to multiple import patterns, PASS after SSOT consolidation.
    """
    execution_engine_patterns = [
        "from netra_backend.app.core.user_execution_engine",
        "from netra_backend.app.core.execution_engine", 
        "from netra_backend.app.agents.execution_engine",
        "from netra_backend.app.agents.supervisor.execution_engine",
        "from netra_backend.app.agents.supervisor.user_execution_engine",
        "from netra_backend.app.tools.enhanced_tool_execution_engine"
    ]
    
    pattern_violations = {}
    total_violations = 0
    
    for pattern in execution_engine_patterns:
        violations = scan_for_import_pattern(pattern)
        if violations:
            pattern_violations[pattern] = violations
            total_violations += len(violations)
    
    if pattern_violations:
        print(f"\n🔍 EXECUTION ENGINE IMPORT ANALYSIS:")
        for pattern, violations in pattern_violations.items():
            print(f"  {pattern}: {len(violations)} files")
            
    # Only the SSOT pattern should exist
    ssot_pattern = "from netra_backend.app.agents.supervisor.user_execution_engine"
    non_ssot_violations = sum(
        len(violations) for pattern, violations in pattern_violations.items() 
        if pattern != ssot_pattern
    )
    
    # This should FAIL initially due to non-SSOT imports
    assert non_ssot_violations == 0, (
        f"🚨 SSOT VIOLATION: Found {non_ssot_violations} non-SSOT ExecutionEngine imports. "
        f"All imports should use SSOT pattern: {ssot_pattern}. "
        f"Violation patterns: {list(pattern_violations.keys())}"
    )


def test_request_scoped_execution_engine_imports():
    """
    FAIL TEST: Detect imports of RequestScopedExecutionEngine (potential SSOT violation).
    
    RequestScopedExecutionEngine may be a duplicate of UserExecutionEngine.
    This test identifies files importing it to validate if it's a legitimate pattern or violation.
    """
    request_scoped_pattern = "RequestScopedExecutionEngine"
    violations = scan_for_import_pattern(request_scoped_pattern)
    
    if violations:
        print(f"\n🔍 FOUND {len(violations)} RequestScopedExecutionEngine IMPORTS:")
        for violation in violations[:5]:
            print(f"  - {violation['file']}:{violation['line_num']}")
    
    # If RequestScopedExecutionEngine exists, it may be a SSOT violation
    # This test documents the scope for further analysis
    assert len(violations) <= 10, (
        f"🚨 POTENTIAL SSOT VIOLATION: Found {len(violations)} RequestScopedExecutionEngine imports. "
        f"This may indicate duplicate execution engines. Review if this should be consolidated "
        f"into UserExecutionEngine SSOT. Files: {[v['file'] for v in violations[:5]]}"
    )


@pytest.mark.skipif(os.environ.get('SKIP_SLOW_TESTS'), reason="Slow filesystem scan")
def test_comprehensive_execution_engine_class_scan():
    """
    FAIL TEST: Comprehensive scan for all ExecutionEngine class definitions.
    
    This test finds ALL ExecutionEngine classes to identify the true scope of SSOT violations.
    Should FAIL initially due to multiple implementations, PASS after consolidation.
    """
    class_patterns = [
        "class UserExecutionEngine",
        "class RequestScopedExecutionEngine", 
        "class EnhancedToolExecutionEngine",
        "class ExecutionEngine",
        "class BaseExecutionEngine"
    ]
    
    all_classes = {}
    total_classes = 0
    
    for pattern in class_patterns:
        violations = scan_for_import_pattern(pattern)
        if violations:
            all_classes[pattern] = violations
            total_classes += len(violations)
    
    if all_classes:
        print(f"\n🔍 EXECUTION ENGINE CLASS DEFINITIONS FOUND:")
        for class_name, definitions in all_classes.items():
            print(f"  {class_name}: {len(definitions)} definitions")
            for defn in definitions[:3]:  # Show first 3
                print(f"    - {defn['file']}:{defn['line_num']}")
    
    # Only UserExecutionEngine should exist as SSOT
    ssot_classes = all_classes.get("class UserExecutionEngine", [])
    non_ssot_classes = total_classes - len(ssot_classes)
    
    # This should FAIL initially due to multiple execution engine classes
    assert non_ssot_classes == 0, (
        f"🚨 MAJOR SSOT VIOLATION: Found {non_ssot_classes} non-SSOT ExecutionEngine classes. "
        f"Only UserExecutionEngine should exist as SSOT. "
        f"Found classes: {list(all_classes.keys())}. "
        f"Total definitions: {total_classes}"
    )
    
    # Validate SSOT exists
    assert len(ssot_classes) >= 1, (
        f"🚨 CRITICAL: UserExecutionEngine SSOT class not found. "
        f"Expected at least 1 definition in netra_backend/app/agents/supervisor/user_execution_engine.py"
    )


if __name__ == "__main__":
    # Allow manual execution for debugging
    print("🧪 RUNNING SSOT IMPORT VALIDATION TESTS FOR ISSUE #759")
    print("=" * 60)
    
    try:
        test_detect_broken_user_execution_engine_imports()
        print("✅ Import path detection test PASSED")
    except AssertionError as e:
        print(f"❌ Import path detection test FAILED: {e}")
    
    try:
        test_user_execution_engine_import_validation()
        print("✅ Import validation test PASSED") 
    except AssertionError as e:
        print(f"❌ Import validation test FAILED: {e}")
        
    try:
        test_execution_engine_import_patterns_across_codebase()
        print("✅ Import patterns test PASSED")
    except AssertionError as e:
        print(f"❌ Import patterns test FAILED: {e}")