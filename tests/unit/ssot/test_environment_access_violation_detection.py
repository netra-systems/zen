#!/usr/bin/env python3
"""
Test Environment Access Violation Detection

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Detect and prevent SSOT violations in codebase
- Value Impact: Eliminates configuration drift causing Golden Path failures
- Strategic Impact: $500K+ ARR protected through automated violation detection

CRITICAL PURPOSE:
This test scans the codebase for direct `os.environ` access patterns that bypass
the SSOT IsolatedEnvironment. These violations cause:
1. Test configuration pollution between test scenarios
2. Environment variable inconsistencies in multi-user contexts
3. Golden Path blockers due to missing test defaults
4. Thread safety violations in concurrent scenarios

EXPECTED BEHAVIOR:
- Should FAIL initially (detecting 15+ violations in mission-critical tests)
- Should PASS after SSOT migration is complete
- Provides actionable violation reports for remediation
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass

import pytest

# SSOT Import - Use ONLY this pattern for environment access
from shared.isolated_environment import get_env


@dataclass
class EnvironmentViolation:
    """Represents a detected environment access violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str  # 'os_environ_get', 'os_environ_set', 'os_environ_in', etc.
    severity: str  # 'critical', 'high', 'medium', 'low'
    context: str  # surrounding code context


class EnvironmentAccessViolationDetector:
    """Detects direct os.environ access patterns in codebase."""
    
    # Patterns that indicate SSOT violations
    VIOLATION_PATTERNS = {
        'os_environ_get': re.compile(r'os\.environ\.get\s*\('),
        'os_environ_setitem': re.compile(r'os\.environ\s*\[\s*[\'"]'),
        'os_environ_getitem': re.compile(r'os\.environ\s*\[\s*[\'"]'),
        'os_environ_in': re.compile(r'\w+\s+in\s+os\.environ'),
        'os_environ_update': re.compile(r'os\.environ\.update\s*\('),
        'os_environ_pop': re.compile(r'os\.environ\.pop\s*\('),
        'os_environ_clear': re.compile(r'os\.environ\.clear\s*\('),
        'os_environ_dict': re.compile(r'dict\s*\(\s*os\.environ\s*\)'),
        'os_environ_direct': re.compile(r'os\.environ(?!\.)(?![a-zA-Z_])'),
    }
    
    # Files to scan for violations (focusing on mission-critical areas)
    CRITICAL_SCAN_PATHS = [
        "tests/mission_critical",
        "netra_backend/tests/startup",
        "netra_backend/tests/integration",
        "tests/integration",
        "tests/e2e",
    ]
    
    # Files that are allowed to use os.environ (SSOT implementations)
    ALLOWED_FILES = {
        "shared/isolated_environment.py",  # SSOT implementation
        "dev_launcher/isolated_environment.py",  # Legacy compatibility
        "test_framework/environment_lock.py",  # System-level locking
    }
    
    # Test patterns that should use SSOT
    TEST_FILE_PATTERNS = [
        re.compile(r'test_.*\.py$'),
        re.compile(r'.*_test\.py$'),
    ]
    
    def __init__(self, project_root: Path):
        """Initialize detector with project root path."""
        self.project_root = project_root
        self.violations: List[EnvironmentViolation] = []
    
    def is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        filename = file_path.name
        return any(pattern.match(filename) for pattern in self.TEST_FILE_PATTERNS)
    
    def is_allowed_file(self, file_path: Path) -> bool:
        """Check if file is allowed to use os.environ."""
        relative_path = str(file_path.relative_to(self.project_root))
        return any(allowed in relative_path for allowed in self.ALLOWED_FILES)
    
    def get_severity(self, violation_type: str, file_path: Path) -> str:
        """Determine violation severity."""
        if self.is_test_file(file_path):
            if any(critical_path in str(file_path) for critical_path in 
                   ["mission_critical", "startup", "e2e"]):
                return "critical"
            return "high"
        
        if "netra_backend/app" in str(file_path):
            return "high"
        
        return "medium"
    
    def extract_context(self, lines: List[str], line_number: int, context_size: int = 2) -> str:
        """Extract surrounding context for a violation."""
        start = max(0, line_number - context_size - 1)
        end = min(len(lines), line_number + context_size)
        
        context_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_number - 1 else "    "
            context_lines.append(f"{prefix}{i+1:3d}: {lines[i].rstrip()}")
        
        return "\n".join(context_lines)
    
    def scan_file(self, file_path: Path) -> List[EnvironmentViolation]:
        """Scan a single file for environment access violations."""
        if self.is_allowed_file(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            # Skip files that can't be read
            return []
        
        violations = []
        
        for line_number, line in enumerate(lines, 1):
            line_content = line.strip()
            
            # Skip comments and empty lines
            if not line_content or line_content.startswith('#'):
                continue
            
            # Check for violation patterns
            for violation_type, pattern in self.VIOLATION_PATTERNS.items():
                if pattern.search(line_content):
                    severity = self.get_severity(violation_type, file_path)
                    context = self.extract_context(lines, line_number)
                    
                    violation = EnvironmentViolation(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_number,
                        line_content=line_content,
                        violation_type=violation_type,
                        severity=severity,
                        context=context
                    )
                    violations.append(violation)
        
        return violations
    
    def scan_directory(self, directory: Path) -> List[EnvironmentViolation]:
        """Scan directory recursively for violations."""
        violations = []
        
        if not directory.exists():
            return violations
        
        # Find all Python files
        python_files = list(directory.rglob("*.py"))
        
        for file_path in python_files:
            file_violations = self.scan_file(file_path)
            violations.extend(file_violations)
        
        return violations
    
    def scan_critical_paths(self) -> Dict[str, List[EnvironmentViolation]]:
        """Scan all critical paths for violations."""
        results = {}
        
        for path in self.CRITICAL_SCAN_PATHS:
            full_path = self.project_root / path
            violations = self.scan_directory(full_path)
            if violations:
                results[path] = violations
        
        return results
    
    def generate_violation_report(self, violations: Dict[str, List[EnvironmentViolation]]) -> str:
        """Generate a detailed violation report."""
        report_lines = []
        report_lines.append("ENVIRONMENT ACCESS VIOLATION REPORT")
        report_lines.append("=" * 50)
        report_lines.append("")
        
        total_violations = sum(len(v) for v in violations.values())
        total_files = sum(len(set(violation.file_path for violation in v)) for v in violations.values())
        
        report_lines.append(f"SUMMARY:")
        report_lines.append(f"- Total Violations: {total_violations}")
        report_lines.append(f"- Files Affected: {total_files}")
        report_lines.append("")
        
        # Group by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for violation_list in violations.values():
            for violation in violation_list:
                severity_counts[violation.severity] += 1
        
        report_lines.append("SEVERITY BREAKDOWN:")
        for severity, count in severity_counts.items():
            if count > 0:
                report_lines.append(f"- {severity.upper()}: {count}")
        report_lines.append("")
        
        # Detailed violations by path
        for path, path_violations in violations.items():
            if not path_violations:
                continue
            
            report_lines.append(f"PATH: {path}")
            report_lines.append("-" * (len(path) + 6))
            
            # Group by file
            files = {}
            for violation in path_violations:
                if violation.file_path not in files:
                    files[violation.file_path] = []
                files[violation.file_path].append(violation)
            
            for file_path, file_violations in files.items():
                report_lines.append(f"")
                report_lines.append(f"FILE: {file_path} ({len(file_violations)} violations)")
                
                for violation in file_violations:
                    report_lines.append(f"  Line {violation.line_number}: {violation.violation_type} ({violation.severity})")
                    report_lines.append(f"  Code: {violation.line_content}")
                    if violation.context:
                        report_lines.append("  Context:")
                        for context_line in violation.context.split('\n'):
                            report_lines.append(f"    {context_line}")
                    report_lines.append("")
            
            report_lines.append("")
        
        # Remediation suggestions
        report_lines.append("REMEDIATION SUGGESTIONS:")
        report_lines.append("- Replace 'os.environ.get(key)' with 'get_env().get(key)'")
        report_lines.append("- Replace 'os.environ[key] = value' with 'get_env().set(key, value, source=\"test\")'")
        report_lines.append("- Replace 'key in os.environ' with 'get_env().exists(key)'")
        report_lines.append("- Import: 'from shared.isolated_environment import get_env'")
        report_lines.append("")
        
        return "\n".join(report_lines)


@pytest.mark.unit
class TestEnvironmentAccessViolationDetection:
    """Test environment access violation detection."""
    
    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.detector = EnvironmentAccessViolationDetector(self.project_root)
    
    def test_violation_detector_initialization(self):
        """Test that violation detector initializes correctly."""
        assert self.detector.project_root.exists(), "Project root should exist"
        assert len(self.detector.VIOLATION_PATTERNS) > 0, "Should have violation patterns"
        assert len(self.detector.CRITICAL_SCAN_PATHS) > 0, "Should have scan paths"
    
    def test_violation_pattern_matching(self):
        """Test that violation patterns match expected code patterns."""
        test_lines = [
            "value = os.environ.get('TEST_VAR')",  # Should match os_environ_get
            "os.environ['TEST_VAR'] = 'value'",   # Should match os_environ_setitem
            "if 'TEST_VAR' in os.environ:",       # Should match os_environ_in
            "os.environ.update({'key': 'value'})", # Should match os_environ_update
            "result = os.environ['TEST_VAR']",    # Should match os_environ_getitem
        ]
        
        matches = {}
        for line in test_lines:
            for violation_type, pattern in self.detector.VIOLATION_PATTERNS.items():
                if pattern.search(line):
                    if violation_type not in matches:
                        matches[violation_type] = []
                    matches[violation_type].append(line)
        
        # Should detect at least some violations
        assert len(matches) > 0, f"Should detect violations in test patterns, found: {matches}"
        
        # Specific pattern checks
        assert any('os.environ.get' in line for lines in matches.values() for line in lines), \
            "Should detect os.environ.get pattern"
    
    def test_test_file_detection(self):
        """Test that test files are correctly identified."""
        test_files = [
            Path("test_example.py"),
            Path("tests/unit/test_something.py"),
            Path("something_test.py"),
        ]
        
        non_test_files = [
            Path("app.py"),
            Path("models.py"),
            Path("utils.py"),
        ]
        
        for test_file in test_files:
            assert self.detector.is_test_file(test_file), f"{test_file} should be identified as test file"
        
        for non_test_file in non_test_files:
            assert not self.detector.is_test_file(non_test_file), f"{non_test_file} should not be test file"
    
    def test_allowed_file_detection(self):
        """Test that allowed files are correctly identified."""
        allowed_paths = [
            self.project_root / "shared/isolated_environment.py",
            self.project_root / "test_framework/environment_lock.py",
        ]
        
        not_allowed_paths = [
            self.project_root / "tests/mission_critical/test_example.py",
            self.project_root / "netra_backend/app/models.py",
        ]
        
        for allowed_path in allowed_paths:
            if allowed_path.exists():  # Only test if file exists
                assert self.detector.is_allowed_file(allowed_path), f"{allowed_path} should be allowed"
        
        for not_allowed_path in not_allowed_paths:
            assert not self.detector.is_allowed_file(not_allowed_path), f"{not_allowed_path} should not be allowed"
    
    def test_severity_assignment(self):
        """Test that violation severity is assigned correctly."""
        # Critical: mission-critical test files
        critical_path = self.project_root / "tests/mission_critical/test_example.py"
        severity = self.detector.get_severity("os_environ_get", critical_path)
        assert severity == "critical", "Mission critical test files should have critical severity"
        
        # High: regular test files
        high_path = self.project_root / "tests/unit/test_example.py"
        severity = self.detector.get_severity("os_environ_get", high_path)
        assert severity == "high", "Regular test files should have high severity"
        
        # High: backend application files
        backend_path = self.project_root / "netra_backend/app/models.py"
        severity = self.detector.get_severity("os_environ_get", backend_path)
        assert severity == "high", "Backend app files should have high severity"
        
        # Medium: other files
        other_path = self.project_root / "scripts/utility.py"
        severity = self.detector.get_severity("os_environ_get", other_path)
        assert severity == "medium", "Other files should have medium severity"
    
    @pytest.mark.parametrize("scan_path", [
        "tests/mission_critical",
        "tests/integration",
        "tests/e2e",
    ])
    def test_scan_critical_paths_for_violations(self, scan_path):
        """
        Test scanning critical paths for SSOT violations.
        
        This test is EXPECTED TO FAIL initially because there are 15+ violations
        in mission-critical tests using direct os.environ access.
        
        After SSOT migration, this test should PASS.
        """
        full_path = self.project_root / scan_path
        
        if not full_path.exists():
            pytest.skip(f"Scan path {scan_path} does not exist")
        
        # Scan for violations
        violations = self.detector.scan_directory(full_path)
        
        # Generate detailed report
        if violations:
            violation_report = self.detector.generate_violation_report({scan_path: violations})
            
            # Count critical and high severity violations
            critical_violations = [v for v in violations if v.severity == "critical"]
            high_violations = [v for v in violations if v.severity == "high"]
            
            failure_message = (
                f"\n\nSSOT VIOLATIONS DETECTED in {scan_path}:\n"
                f"- Critical violations: {len(critical_violations)}\n"
                f"- High violations: {len(high_violations)}\n"
                f"- Total violations: {len(violations)}\n\n"
                f"DETAILED REPORT:\n{violation_report}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"Replace direct os.environ access with SSOT pattern:\n"
                f"  BAD:  os.environ.get('KEY')\n"
                f"  GOOD: get_env().get('KEY')\n\n"
                f"This test will PASS after SSOT migration is complete."
            )
            
            # Fail with detailed report
            pytest.fail(failure_message)
        
        # If no violations found, test passes
        assert len(violations) == 0, f"No SSOT violations should remain in {scan_path}"
    
    def test_comprehensive_violation_scan(self):
        """
        Comprehensive scan across all critical paths.
        
        This is the main test that will initially fail but should pass after migration.
        """
        all_violations = self.detector.scan_critical_paths()
        
        if all_violations:
            # Generate comprehensive report
            report = self.detector.generate_violation_report(all_violations)
            
            total_violations = sum(len(v) for v in all_violations.values())
            critical_count = sum(len([vio for vio in v if vio.severity == "critical"]) 
                                for v in all_violations.values())
            
            failure_message = (
                f"\n\nSSOT ENVIRONMENT ACCESS VIOLATIONS DETECTED!\n"
                f"Total violations: {total_violations}\n"
                f"Critical violations: {critical_count}\n\n"
                f"IMPACT ON GOLDEN PATH:\n"
                f"- Direct os.environ access bypasses test defaults\n"
                f"- Causes configuration pollution between tests\n"
                f"- Thread safety violations in multi-user scenarios\n"
                f"- Golden Path blockers due to missing OAuth test credentials\n\n"
                f"COMPREHENSIVE VIOLATION REPORT:\n{report}\n\n"
                f"NEXT STEPS:\n"
                f"1. Replace all os.environ usage with get_env() pattern\n"
                f"2. Import: 'from shared.isolated_environment import get_env'\n"
                f"3. Update patterns: os.environ.get(k) -> get_env().get(k)\n"
                f"4. Re-run this test to verify fixes\n"
            )
            
            pytest.fail(failure_message)
        
        # Test passes if no violations found
        assert len(all_violations) == 0, "All SSOT violations have been resolved"
    
    def test_violation_remediation_examples(self):
        """Test that provides examples of correct SSOT patterns."""
        # This test always passes but documents correct patterns
        
        env = get_env()
        env.enable_isolation()
        
        # CORRECT PATTERNS (these should be used instead of os.environ)
        
        # Setting environment variables
        success = env.set("EXAMPLE_VAR", "example_value", source="test_example")
        assert success, "SSOT set() should succeed"
        
        # Getting environment variables
        value = env.get("EXAMPLE_VAR", "default_value")
        assert value == "example_value", "SSOT get() should return set value"
        
        # Checking if variable exists
        exists = env.exists("EXAMPLE_VAR")
        assert exists, "SSOT exists() should return True for set variable"
        
        # Getting all variables
        all_vars = env.get_all()
        assert "EXAMPLE_VAR" in all_vars, "SSOT get_all() should include set variable"
        
        # Deleting variables
        deleted = env.delete("EXAMPLE_VAR", source="test_cleanup")
        assert deleted, "SSOT delete() should succeed"
        
        # Variable should no longer exist
        value_after_delete = env.get("EXAMPLE_VAR", "not_found")
        assert value_after_delete == "not_found", "Variable should not exist after delete"
        
        env.disable_isolation()
        
        # This test documents the CORRECT way to access environment variables
        # and serves as a reference for migration from os.environ patterns