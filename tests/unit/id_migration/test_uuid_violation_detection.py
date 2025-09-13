"""
UUID4 Violation Detection Tests - Issue #89

This test suite detects uuid.uuid4() usage violations across the codebase
as specified in the comprehensive test plan. These tests are designed to FAIL
until the migration to UnifiedIDManager is complete.

Business Value Justification:
- Segment: Platform/All Tiers (ID collision affects all users equally)
- Business Goal: Revenue Protection ($500K+ ARR chat functionality stability)
- Value Impact: Prevents ID collision risks that threaten multi-user isolation
- Strategic Impact: Ensures reliable ID generation for enterprise-grade operations

Test Strategy: Create FAILING tests that demonstrate current violations
"""

import os
import re
import uuid
import inspect
import ast
from typing import List, Dict, Set, Tuple, Any
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestUuidViolationDetection(SSotBaseTestCase):
    """
    Test suite to detect uuid.uuid4() violations across production code.

    These tests are designed to FAIL initially, demonstrating the current
    state of 732 uuid.uuid4() violations that need migration.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.unified_id_manager = UnifiedIDManager()
        self.project_root = Path(__file__).parent.parent.parent.parent

        # Define production code paths (exclude tests)
        self.production_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared",
            self.project_root / "frontend" / "lib",
            self.project_root / "frontend" / "components",
            self.project_root / "scripts",
        ]

        # Exclude patterns for test files and non-critical paths
        self.exclude_patterns = [
            r".*test.*\.py$",
            r".*tests.*\.py$",
            r".*__pycache__.*",
            r".*\.pyc$",
            r".*migration.*\.py$",  # Exclude migration scripts themselves
            r".*node_modules.*",
            r".*\.git.*",
        ]

    def test_detect_uuid4_violations_in_production_code(self):
        """
        FAILING TEST: Detect all uuid.uuid4() usage in production files.

        Expected: 0 violations
        Actual: ~60 violations in production code (732 total including tests)

        This test scans production code for direct uuid.uuid4() calls that
        should be replaced with UnifiedIDManager patterns.
        """
        violations = self._scan_production_files_for_uuid4_usage()

        # Record metrics about violations found
        self.record_metric("total_production_violations", len(violations))
        self.record_metric("violation_files", list(violations.keys()))

        # Provide detailed violation information
        violation_summary = {}
        total_violations = 0

        for file_path, file_violations in violations.items():
            violation_count = len(file_violations)
            total_violations += violation_count
            violation_summary[file_path] = {
                "violation_count": violation_count,
                "violations": file_violations
            }

        self.record_metric("violation_summary", violation_summary)

        # The test should FAIL until migration is complete
        assert len(violations) == 0, (
            f"Found {total_violations} uuid.uuid4() violations in {len(violations)} production files. "
            f"Production code must use UnifiedIDManager instead of direct UUID generation. "
            f"Violations: {list(violations.keys())}"
        )

    def test_unified_id_manager_usage_compliance(self):
        """
        FAILING TEST: Verify all ID generation uses UnifiedIDManager.

        This test scans for proper UnifiedIDManager usage patterns and
        ensures no modules bypass the centralized ID generation system.
        """
        compliant_modules = self._verify_unified_id_manager_usage()
        production_modules = self._get_production_modules()

        non_compliant = []
        for module_path in production_modules:
            if module_path not in compliant_modules:
                non_compliant.append(module_path)

        # Record metrics
        self.record_metric("total_production_modules", len(production_modules))
        self.record_metric("compliant_modules", len(compliant_modules))
        self.record_metric("non_compliant_modules", len(non_compliant))
        self.record_metric("compliance_percentage",
                          (len(compliant_modules) / max(1, len(production_modules))) * 100)

        # The test should FAIL if modules are non-compliant
        assert len(non_compliant) == 0, (
            f"Found {len(non_compliant)} non-compliant modules out of {len(production_modules)} total. "
            f"Non-compliant modules: {non_compliant}. "
            f"All production modules must use UnifiedIDManager for ID generation."
        )

    def test_detect_uuid_import_patterns_in_production(self):
        """
        FAILING TEST: Detect problematic UUID import patterns in production code.

        This test looks for import statements that enable direct uuid.uuid4() usage
        instead of going through UnifiedIDManager.
        """
        import_violations = self._scan_uuid_import_patterns()

        # Categorize violations by type
        violation_types = {
            "direct_uuid4_import": [],
            "uuid_module_import": [],
            "uuid4_function_calls": []
        }

        for file_path, violations in import_violations.items():
            for violation in violations:
                if "from uuid import uuid4" in violation["pattern"]:
                    violation_types["direct_uuid4_import"].append(violation)
                elif "import uuid" in violation["pattern"]:
                    violation_types["uuid_module_import"].append(violation)
                elif "uuid4(" in violation["pattern"]:
                    violation_types["uuid4_function_calls"].append(violation)

        # Record detailed metrics
        for violation_type, violations in violation_types.items():
            self.record_metric(f"{violation_type}_count", len(violations))
            self.record_metric(f"{violation_type}_details", violations)

        total_import_violations = sum(len(violations) for violations in violation_types.values())

        # The test should FAIL if import violations exist
        assert total_import_violations == 0, (
            f"Found {total_import_violations} UUID import violations in production code. "
            f"Direct UUID imports: {len(violation_types['direct_uuid4_import'])}, "
            f"UUID module imports: {len(violation_types['uuid_module_import'])}, "
            f"UUID4 function calls: {len(violation_types['uuid4_function_calls'])}. "
            f"Production code must import from UnifiedIDManager instead."
        )

    def test_production_code_id_generation_patterns(self):
        """
        FAILING TEST: Verify production code uses approved ID generation patterns.

        This test validates that ID generation follows UnifiedIDManager patterns
        rather than ad-hoc UUID generation.
        """
        pattern_violations = self._analyze_id_generation_patterns()

        # Categorize pattern violations
        pattern_analysis = {
            "raw_uuid_generation": 0,
            "string_uuid_conversion": 0,
            "missing_unified_manager": 0,
            "improper_id_types": 0
        }

        for file_path, violations in pattern_violations.items():
            for violation in violations:
                violation_type = violation.get("type", "unknown")
                if violation_type in pattern_analysis:
                    pattern_analysis[violation_type] += 1

        # Record pattern analysis
        self.record_metric("pattern_violation_analysis", pattern_analysis)
        self.record_metric("total_pattern_violations", sum(pattern_analysis.values()))
        self.record_metric("pattern_violation_files", list(pattern_violations.keys()))

        total_violations = sum(pattern_analysis.values())

        # The test should FAIL if pattern violations exist
        assert total_violations == 0, (
            f"Found {total_violations} ID generation pattern violations. "
            f"Raw UUID generation: {pattern_analysis['raw_uuid_generation']}, "
            f"String UUID conversion: {pattern_analysis['string_uuid_conversion']}, "
            f"Missing UnifiedIDManager: {pattern_analysis['missing_unified_manager']}, "
            f"Improper ID types: {pattern_analysis['improper_id_types']}. "
            f"All ID generation must use UnifiedIDManager patterns."
        )

    def _scan_production_files_for_uuid4_usage(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan production files for uuid.uuid4() usage.

        Returns:
            Dictionary mapping file paths to lists of violations found
        """
        violations = {}

        for production_path in self.production_paths:
            if not production_path.exists():
                continue

            for file_path in production_path.rglob("*.py"):
                # Skip excluded files
                if self._should_exclude_file(file_path):
                    continue

                file_violations = self._scan_file_for_uuid4(file_path)
                if file_violations:
                    violations[str(file_path)] = file_violations

        return violations

    def _scan_file_for_uuid4(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Scan a single file for uuid.uuid4() usage.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of violation dictionaries with details
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            # Look for uuid.uuid4() patterns
            uuid4_patterns = [
                r'uuid\.uuid4\(',
                r'uuid4\(',
                r'from uuid import uuid4',
                r'import uuid.*',  # Check for uuid imports that could lead to uuid4 usage
            ]

            for line_num, line in enumerate(lines, 1):
                for pattern in uuid4_patterns:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    if matches:
                        violations.append({
                            "line_number": line_num,
                            "line_content": line.strip(),
                            "pattern": pattern,
                            "matches": matches
                        })

        except Exception as e:
            # Record scanning errors but don't fail the test
            self.record_metric(f"scan_error_{file_path.name}", str(e))

        return violations

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from scanning."""
        file_str = str(file_path)

        for pattern in self.exclude_patterns:
            if re.search(pattern, file_str, re.IGNORECASE):
                return True

        return False

    def _verify_unified_id_manager_usage(self) -> Set[str]:
        """
        Verify which modules properly use UnifiedIDManager.

        Returns:
            Set of module paths that are compliant
        """
        compliant_modules = set()

        for production_path in self.production_paths:
            if not production_path.exists():
                continue

            for file_path in production_path.rglob("*.py"):
                if self._should_exclude_file(file_path):
                    continue

                if self._file_uses_unified_id_manager(file_path):
                    compliant_modules.add(str(file_path))

        return compliant_modules

    def _file_uses_unified_id_manager(self, file_path: Path) -> bool:
        """
        Check if a file properly uses UnifiedIDManager for ID generation.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file uses UnifiedIDManager properly
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for proper UnifiedIDManager usage patterns
            unified_patterns = [
                r'from.*unified_id_manager.*import',
                r'UnifiedIDManager',
                r'unified_id_manager',
                r'generate_id\(',
                r'IDType\.',
            ]

            # Check for problematic patterns
            problematic_patterns = [
                r'uuid\.uuid4\(',
                r'str\(uuid\.uuid4\(\)\)',
                r'from uuid import uuid4',
            ]

            has_unified = any(re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                            for pattern in unified_patterns)
            has_problematic = any(re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                                for pattern in problematic_patterns)

            # File is compliant if it uses UnifiedIDManager and doesn't use problematic patterns
            # OR if it doesn't do any ID generation at all
            if has_problematic:
                return False

            # If it has ID generation, it should use UnifiedIDManager
            id_generation_patterns = [
                r'id\s*=',
                r'_id\s*=',
                r'uuid',
                r'generate',
            ]

            has_id_generation = any(re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
                                  for pattern in id_generation_patterns)

            if has_id_generation and not has_unified:
                return False

            return True

        except Exception:
            # If we can't read the file, assume non-compliant
            return False

    def _get_production_modules(self) -> List[str]:
        """Get list of all production Python modules."""
        modules = []

        for production_path in self.production_paths:
            if not production_path.exists():
                continue

            for file_path in production_path.rglob("*.py"):
                if self._should_exclude_file(file_path):
                    continue
                modules.append(str(file_path))

        return modules

    def _scan_uuid_import_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan for problematic UUID import patterns.

        Returns:
            Dictionary mapping file paths to import violations
        """
        violations = {}

        for production_path in self.production_paths:
            if not production_path.exists():
                continue

            for file_path in production_path.rglob("*.py"):
                if self._should_exclude_file(file_path):
                    continue

                import_violations = self._analyze_file_imports(file_path)
                if import_violations:
                    violations[str(file_path)] = import_violations

        return violations

    def _analyze_file_imports(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze a file's import statements for UUID violations.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List of import violation details
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST to get import information
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            if 'uuid' in name.name:
                                violations.append({
                                    "type": "import",
                                    "line_number": node.lineno,
                                    "pattern": f"import {name.name}",
                                    "module": name.name
                                })

                    elif isinstance(node, ast.ImportFrom):
                        if node.module and 'uuid' in node.module:
                            for name in node.names:
                                violations.append({
                                    "type": "from_import",
                                    "line_number": node.lineno,
                                    "pattern": f"from {node.module} import {name.name}",
                                    "module": node.module,
                                    "name": name.name
                                })

            except SyntaxError:
                # If AST parsing fails, fall back to regex
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    if re.search(r'import.*uuid|from.*uuid.*import', line, re.IGNORECASE):
                        violations.append({
                            "type": "regex_fallback",
                            "line_number": line_num,
                            "pattern": line.strip(),
                            "note": "AST parsing failed, using regex"
                        })

        except Exception as e:
            self.record_metric(f"import_analysis_error_{file_path.name}", str(e))

        return violations

    def _analyze_id_generation_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze ID generation patterns across production code.

        Returns:
            Dictionary mapping file paths to pattern violations
        """
        violations = {}

        for production_path in self.production_paths:
            if not production_path.exists():
                continue

            for file_path in production_path.rglob("*.py"):
                if self._should_exclude_file(file_path):
                    continue

                pattern_violations = self._analyze_file_patterns(file_path)
                if pattern_violations:
                    violations[str(file_path)] = pattern_violations

        return violations

    def _analyze_file_patterns(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze ID generation patterns in a single file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List of pattern violation details
        """
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            # Pattern analysis
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # Check for raw UUID generation
                if re.search(r'uuid\.uuid4\(\)', line_stripped):
                    violations.append({
                        "type": "raw_uuid_generation",
                        "line_number": line_num,
                        "line_content": line_stripped,
                        "description": "Direct uuid.uuid4() call should use UnifiedIDManager"
                    })

                # Check for string UUID conversion
                if re.search(r'str\(uuid\.uuid4\(\)\)', line_stripped):
                    violations.append({
                        "type": "string_uuid_conversion",
                        "line_number": line_num,
                        "line_content": line_stripped,
                        "description": "String UUID conversion should use UnifiedIDManager.generate_id()"
                    })

                # Check for ID assignment without UnifiedIDManager
                if re.search(r'.*_id\s*=.*uuid', line_stripped, re.IGNORECASE):
                    if not re.search(r'unified|IDType|generate_id', line_stripped, re.IGNORECASE):
                        violations.append({
                            "type": "missing_unified_manager",
                            "line_number": line_num,
                            "line_content": line_stripped,
                            "description": "ID assignment should use UnifiedIDManager patterns"
                        })

                # Check for hardcoded ID types instead of IDType enum
                id_type_patterns = [
                    r'"user"', r"'user'",
                    r'"session"', r"'session'",
                    r'"request"', r"'request'",
                    r'"agent"', r"'agent'",
                    r'"websocket"', r"'websocket'",
                    r'"execution"', r"'execution'",
                ]

                for pattern in id_type_patterns:
                    if re.search(pattern, line_stripped) and 'id' in line_stripped.lower():
                        violations.append({
                            "type": "improper_id_types",
                            "line_number": line_num,
                            "line_content": line_stripped,
                            "description": f"Should use IDType enum instead of string literal: {pattern}"
                        })

        except Exception as e:
            self.record_metric(f"pattern_analysis_error_{file_path.name}", str(e))

        return violations


if __name__ == "__main__":
    # Run tests to demonstrate current violations
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])