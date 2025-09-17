"""
SSOT Inheritance Validation Tests - Issue #1097 Test Plan Implementation

These tests detect and validate unittest.TestCase migration issues for Issue #1097.
They are designed to FAIL initially to prove the problems exist, then track progress.

Business Value: Platform/Internal - System Stability & Development Velocity
Prevents test infrastructure inconsistencies and ensures SSOT compliance.

CRITICAL: These tests follow SSOT patterns and use SSotBaseTestCase.
They scan the codebase for violations and report them clearly.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set

# SSOT imports following project requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestSSotInheritanceValidation(SSotBaseTestCase):
    """
    Validation tests for SSOT inheritance violations in Issue #1097.
    
    These tests detect double inheritance violations where tests inherit from
    both SSotBaseTestCase/SSotAsyncTestCase AND unittest.TestCase, which creates
    conflicts and violates SSOT patterns.
    
    Expected to FAIL initially to prove the problem exists.
    """

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.repo_root = Path("/Users/anthony/Desktop/netra-apex")
        self.test_directories = [
            self.repo_root / "tests",
            self.repo_root / "netra_backend" / "tests",
            self.repo_root / "auth_service" / "tests",
            self.repo_root / "frontend" / "tests",
            self.repo_root / "test_framework" / "tests",
        ]
        
    def _find_python_test_files(self) -> List[Path]:
        """Find all Python test files in the codebase."""
        test_files = []
        
        for test_dir in self.test_directories:
            if test_dir.exists():
                for pattern in ["test_*.py", "*_test.py"]:
                    test_files.extend(test_dir.rglob(pattern))
        
        return test_files
    
    def _parse_file_for_inheritance(self, file_path: Path) -> List[Tuple[str, List[str]]]:
        """
        Parse a Python file to find class definitions and their inheritance.
        
        Returns:
            List of (class_name, base_classes) tuples
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            classes_with_inheritance = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            # Handle cases like unittest.TestCase
                            if isinstance(base.value, ast.Name):
                                base_classes.append(f"{base.value.id}.{base.attr}")
                    
                    if base_classes:  # Only record classes with inheritance
                        classes_with_inheritance.append((node.name, base_classes))
            
            return classes_with_inheritance
            
        except Exception as e:
            # Log parsing errors but don't fail the test
            self.logger.warning(f"Failed to parse {file_path}: {e}")
            return []
    
    def _detect_double_inheritance_violations(self) -> Dict[str, List[Tuple[str, List[str]]]]:
        """
        Detect classes that inherit from both SSOT base classes and unittest.TestCase.
        
        Returns:
            Dictionary mapping file paths to list of violating classes
        """
        violations = {}
        test_files = self._find_python_test_files()
        
        ssot_base_classes = {
            'SSotBaseTestCase', 'SSotAsyncTestCase',
            'BaseTestCase', 'AsyncTestCase',  # Legacy aliases
            'SSotAsyncBaseTestCase'  # Integration alias
        }
        
        unittest_classes = {
            'unittest.TestCase', 'TestCase'
        }
        
        for file_path in test_files:
            classes_with_inheritance = self._parse_file_for_inheritance(file_path)
            
            for class_name, base_classes in classes_with_inheritance:
                has_ssot_base = any(base in ssot_base_classes for base in base_classes)
                has_unittest_base = any(base in unittest_classes for base in base_classes)
                
                if has_ssot_base and has_unittest_base:
                    file_key = str(file_path.relative_to(self.repo_root))
                    if file_key not in violations:
                        violations[file_key] = []
                    violations[file_key].append((class_name, base_classes))
        
        return violations
    
    def test_no_double_inheritance_violations(self):
        """
        Test that no classes inherit from both SSOT base classes and unittest.TestCase.
        
        EXPECTED TO FAIL INITIALLY - This proves Issue #1097 exists.
        """
        violations = self._detect_double_inheritance_violations()
        
        # Record metrics for tracking
        self.record_metric("double_inheritance_violations_count", len(violations))
        self.record_metric("files_with_violations", len(violations))
        
        if violations:
            violation_details = []
            for file_path, classes in violations.items():
                for class_name, base_classes in classes:
                    violation_details.append(
                        f"  {file_path}::{class_name} inherits from {base_classes}"
                    )
            
            failure_message = (
                f"Found {len(violations)} files with double inheritance violations:\n" +
                "\n".join(violation_details) +
                "\n\nThese classes violate SSOT patterns by inheriting from both "
                "SSOT base classes and unittest.TestCase. This creates method "
                "resolution order conflicts and violates the SSOT principle."
            )
            
            # This test is EXPECTED TO FAIL initially
            self.fail(failure_message)
        
        # If we get here, no violations were found (good!)
        self.logger.info("No double inheritance violations found - SSOT compliance achieved!")
    
    def _find_mission_critical_files(self) -> List[Path]:
        """Find mission-critical test files that must use SSOT patterns."""
        mission_critical_patterns = [
            "**/test_websocket_agent_events_suite.py",
            "**/test_mission_critical_*.py",
            "**/test_golden_path_*.py",
            "**/test_*_critical.py",
            "**/tests/mission_critical/**/*.py",
            "**/tests/critical/**/*.py",
        ]
        
        mission_critical_files = []
        for pattern in mission_critical_patterns:
            mission_critical_files.extend(self.repo_root.glob(pattern))
        
        return mission_critical_files
    
    def test_mission_critical_files_use_ssot_base_classes(self):
        """
        Test that mission-critical files use SSOT base classes.
        
        EXPECTED TO FAIL INITIALLY - This validates Issue #1097 scope.
        """
        mission_critical_files = self._find_mission_critical_files()
        non_compliant_files = []
        
        ssot_base_classes = {
            'SSotBaseTestCase', 'SSotAsyncTestCase',
            'BaseTestCase', 'AsyncTestCase',  # Legacy aliases that map to SSOT
        }
        
        for file_path in mission_critical_files:
            if not file_path.exists():
                continue
                
            classes_with_inheritance = self._parse_file_for_inheritance(file_path)
            file_uses_ssot = False
            
            for class_name, base_classes in classes_with_inheritance:
                if any(base in ssot_base_classes for base in base_classes):
                    file_uses_ssot = True
                    break
            
            # Check if file has test classes but doesn't use SSOT
            has_test_classes = any(
                class_name.startswith('Test') or 'Test' in class_name
                for class_name, _ in classes_with_inheritance
            )
            
            if has_test_classes and not file_uses_ssot:
                non_compliant_files.append(str(file_path.relative_to(self.repo_root)))
        
        # Record metrics for tracking
        self.record_metric("mission_critical_files_count", len(mission_critical_files))
        self.record_metric("non_compliant_mission_critical_count", len(non_compliant_files))
        
        if non_compliant_files:
            failure_message = (
                f"Found {len(non_compliant_files)} mission-critical files not using SSOT base classes:\n" +
                "\n".join(f"  {file_path}" for file_path in non_compliant_files) +
                "\n\nMission-critical files MUST use SSOT base classes for business "
                "value protection and consistent test infrastructure."
            )
            
            # This test is EXPECTED TO FAIL initially
            self.fail(failure_message)
        
        # If we get here, all mission-critical files are SSOT compliant
        self.logger.info("All mission-critical files use SSOT base classes - excellent compliance!")
    
    def test_detect_legacy_unittest_usage_scope(self):
        """
        Test to detect and measure the scope of legacy unittest.TestCase usage.
        
        This test provides a baseline measurement for Issue #1097 migration efforts.
        EXPECTED TO FAIL INITIALLY to document the current state.
        """
        test_files = self._find_python_test_files()
        legacy_unittest_files = []
        
        for file_path in test_files:
            classes_with_inheritance = self._parse_file_for_inheritance(file_path)
            
            for class_name, base_classes in classes_with_inheritance:
                # Check for direct unittest.TestCase inheritance (without SSOT)
                has_unittest = any('TestCase' in base for base in base_classes)
                has_ssot = any(
                    base in {'SSotBaseTestCase', 'SSotAsyncTestCase', 'BaseTestCase', 'AsyncTestCase'}
                    for base in base_classes
                )
                
                if has_unittest and not has_ssot:
                    file_key = str(file_path.relative_to(self.repo_root))
                    if file_key not in legacy_unittest_files:
                        legacy_unittest_files.append(file_key)
                    break
        
        # Record comprehensive metrics for migration tracking
        self.record_metric("total_test_files_scanned", len(test_files))
        self.record_metric("legacy_unittest_files_count", len(legacy_unittest_files))
        self.record_metric("ssot_compliance_percentage", 
                          ((len(test_files) - len(legacy_unittest_files)) / len(test_files) * 100)
                          if test_files else 100)
        
        if legacy_unittest_files:
            # Sample first 10 files for readable output
            sample_files = legacy_unittest_files[:10]
            additional_count = len(legacy_unittest_files) - len(sample_files)
            
            failure_message = (
                f"Found {len(legacy_unittest_files)} test files still using legacy unittest.TestCase:\n" +
                "\n".join(f"  {file_path}" for file_path in sample_files)
            )
            
            if additional_count > 0:
                failure_message += f"\n  ... and {additional_count} more files"
            
            failure_message += (
                f"\n\nSSoT compliance: {self.get_metric('ssot_compliance_percentage'):.1f}%\n"
                "These files need migration to SSOT base classes for Issue #1097."
            )
            
            # This test is EXPECTED TO FAIL initially to document scope
            self.fail(failure_message)
        
        # If we get here, all test files are SSOT compliant
        self.logger.info(f"All {len(test_files)} test files use SSOT base classes - migration complete!")
    
    def test_verify_ssot_import_consistency(self):
        """
        Test that SSOT base class imports are consistent across the codebase.
        
        This validates that files importing SSOT base classes are using them correctly.
        """
        test_files = self._find_python_test_files()
        import_inconsistencies = []
        
        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for SSOT imports
                ssot_imports = []
                if 'from test_framework.ssot.base_test_case import' in content:
                    # Extract what's being imported
                    import_matches = re.findall(
                        r'from test_framework\.ssot\.base_test_case import ([^\n]+)',
                        content
                    )
                    for match in import_matches:
                        ssot_imports.extend([imp.strip() for imp in match.split(',')])
                
                # Check for class usage in inheritance
                classes_with_inheritance = self._parse_file_for_inheritance(file_path)
                used_bases = set()
                for _, base_classes in classes_with_inheritance:
                    used_bases.update(base_classes)
                
                # Check for inconsistencies
                ssot_bases_in_use = {
                    base for base in used_bases 
                    if base in {'SSotBaseTestCase', 'SSotAsyncTestCase', 'BaseTestCase', 'AsyncTestCase'}
                }
                
                if ssot_bases_in_use and not ssot_imports:
                    import_inconsistencies.append(
                        f"{file_path.relative_to(self.repo_root)}: Uses {ssot_bases_in_use} but no SSOT imports found"
                    )
                
            except Exception as e:
                self.logger.warning(f"Failed to check imports in {file_path}: {e}")
        
        # Record metrics
        self.record_metric("import_inconsistencies_count", len(import_inconsistencies))
        
        if import_inconsistencies:
            failure_message = (
                f"Found {len(import_inconsistencies)} files with SSOT import inconsistencies:\n" +
                "\n".join(f"  {inconsistency}" for inconsistency in import_inconsistencies[:10])
            )
            
            if len(import_inconsistencies) > 10:
                failure_message += f"\n  ... and {len(import_inconsistencies) - 10} more"
            
            # This may fail initially if there are import issues
            self.fail(failure_message)
        
        self.logger.info("All SSOT imports are consistent across the codebase!")


if __name__ == "__main__":
    # Allow running this test file directly for quick validation
    import pytest
    pytest.main([__file__, "-v"])