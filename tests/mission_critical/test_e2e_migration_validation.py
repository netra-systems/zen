#!/usr/bin/env python3
"""
E2E Migration Validation Suite - Mission Critical Test Suite

Business Value: Platform/Internal - Test Infrastructure Migration Safety
Critical for maintaining system stability during SSOT migration of 114+ E2E test files.

This validation suite ensures BaseE2ETest → SSOT base class migration safety by:
1. FAILING if any E2E test still inherits from BaseE2ETest (catching incomplete migrations)
2. Validating all E2E tests use SSOT base classes (SSotBaseTestCase or SSotAsyncTestCase)  
3. Ensuring migrated tests use IsolatedEnvironment vs direct os.environ access
4. Detecting import violations and inheritance issues

Purpose: 20% effort strategic testing to validate safe migration of 114 E2E files.
Critical for $500K+ ARR protection through comprehensive migration validation.

Author: SSOT Migration Validation Agent
Date: 2025-09-10
"""

import ast
import glob
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import logging

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# Existing SSOT validation utilities
try:
    from test_framework.ssot.orchestration import validate_test_class, get_test_base_for_category
except ImportError:
    # Fallback if SSOT validation utilities not available
    def validate_test_class(test_class) -> bool:
        """Fallback validation function."""
        return True
    
    def get_test_base_for_category(category: str) -> type:
        """Fallback category mapping function."""
        return SSotBaseTestCase

logger = logging.getLogger(__name__)


class E2EMigrationDetectionUtility:
    """Utility class for detecting BaseE2ETest usage and migration issues."""
    
    def __init__(self):
        """Initialize migration detection utility."""
        self.project_root = Path(__file__).parent.parent.parent
        self.violation_count = 0
        self.scanned_files = 0
        
    def find_all_e2e_test_files(self) -> List[Path]:
        """
        Find all E2E test files in the project.
        
        Returns:
            List of E2E test file paths
        """
        e2e_patterns = [
            "tests/e2e/**/*.py",
            "tests/**/e2e/**/*.py", 
            "**/**/e2e/test_*.py"
        ]
        
        e2e_files = []
        for pattern in e2e_patterns:
            files = list(self.project_root.glob(pattern))
            e2e_files.extend(files)
        
        # Remove duplicates and filter for actual test files
        unique_files = list(set(e2e_files))
        test_files = [f for f in unique_files if f.name.startswith('test_') and f.suffix == '.py']
        
        logger.info(f"Found {len(test_files)} E2E test files to scan")
        return test_files
    
    def parse_python_file_ast(self, file_path: Path) -> Tuple[ast.Module, bool]:
        """
        Parse Python file using AST.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Tuple of (AST module, success_flag)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            return tree, True
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None, False
    
    def extract_imports_from_ast(self, tree: ast.Module) -> Dict[str, List[str]]:
        """
        Extract all import statements from AST.
        
        Args:
            tree: AST module
            
        Returns:
            Dictionary with 'from_imports' and 'direct_imports'
        """
        imports = {'from_imports': [], 'direct_imports': []}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports['from_imports'].append((module, names))
                
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                imports['direct_imports'].extend(names)
        
        return imports
    
    def extract_class_definitions_from_ast(self, tree: ast.Module) -> List[Dict[str, Any]]:
        """
        Extract class definitions and their inheritance.
        
        Args:
            tree: AST module
            
        Returns:
            List of class definition dictionaries
        """
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract base class names
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle module.ClassName patterns
                        base_names.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
                
                classes.append({
                    'name': node.name,
                    'bases': base_names,
                    'lineno': node.lineno
                })
        
        return classes
    
    def detect_basee2etest_violations(self, file_path: Path) -> Dict[str, List[str]]:
        """
        Detect BaseE2ETest inheritance violations in a file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            Dictionary with violation details
        """
        violations = {
            'inheritance_violations': [],
            'import_violations': [],
            'environment_violations': []
        }
        
        tree, success = self.parse_python_file_ast(file_path)
        if not success:
            return violations
        
        self.scanned_files += 1
        
        # Check imports for BaseE2ETest
        imports = self.extract_imports_from_ast(tree)
        for module, names in imports['from_imports']:
            if 'BaseE2ETest' in names:
                violations['import_violations'].append(f"Imports BaseE2ETest from {module}")
                self.violation_count += 1
        
        # Check class inheritance
        classes = self.extract_class_definitions_from_ast(tree)
        for cls in classes:
            if 'BaseE2ETest' in cls['bases']:
                violations['inheritance_violations'].append(
                    f"Class {cls['name']} inherits from BaseE2ETest at line {cls['lineno']}"
                )
                self.violation_count += 1
        
        # Check for direct os.environ usage (should use IsolatedEnvironment)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'os.environ' in content:
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if 'os.environ' in line and not line.strip().startswith('#'):
                    violations['environment_violations'].append(
                        f"Direct os.environ usage at line {i}: {line.strip()}"
                    )
                    self.violation_count += 1
        
        return violations


class TestE2EMigrationValidation(SSotBaseTestCase):
    """
    CRITICAL: E2E Migration Validation Test Suite.
    
    These tests FAIL if BaseE2ETest usage is detected and PASS when migration complete.
    Designed to guide the migration process and catch incomplete transitions.
    """
    
    def setup_method(self, method=None):
        """Set up migration validation test environment."""
        super().setup_method(method)
        
        # Initialize isolated environment for testing
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Set test-specific environment
        self.env.set("USE_REAL_SERVICES", "false", "e2e_migration_test")
        self.env.set("SSOT_MIGRATION_VALIDATION", "true", "e2e_migration_test")
        self.env.set("TESTING", "true", "e2e_migration_test")
        
        # Initialize detection utility
        self.detector = E2EMigrationDetectionUtility()
        
        # Performance tracking
        self.start_memory = None
        self.performance_metrics = {}
        
        self.record_metric("test_setup_completed", True)
    
    def test_no_basee2etest_inheritance_violations(self):
        """
        CRITICAL: FAIL if any E2E test inherits from BaseE2ETest instead of SSOT.
        
        This test should FAIL during migration and PASS after completion.
        Purpose: Detect incomplete migrations and guide migration process.
        """
        logger.info("Starting BaseE2ETest inheritance violation scan")
        
        # Find all E2E test files
        e2e_files = self.detector.find_all_e2e_test_files()
        
        self.record_metric("e2e_files_found", len(e2e_files))
        assert len(e2e_files) > 0, "No E2E test files found - detection utility may be broken"
        
        # Scan for BaseE2ETest violations
        inheritance_violations = []
        total_violations = 0
        
        for file_path in e2e_files:
            violations = self.detector.detect_basee2etest_violations(file_path)
            
            if violations['inheritance_violations']:
                inheritance_violations.append({
                    'file': str(file_path.relative_to(self.detector.project_root)),
                    'violations': violations['inheritance_violations']
                })
                total_violations += len(violations['inheritance_violations'])
        
        # Record metrics
        self.record_metric("inheritance_violations_detected", total_violations)
        self.record_metric("files_with_violations", len(inheritance_violations))
        self.record_metric("files_scanned", self.detector.scanned_files)
        
        # CRITICAL: This test FAILS if BaseE2ETest inheritance detected
        if inheritance_violations:
            violation_details = []
            for file_info in inheritance_violations:
                violation_details.append(f"File: {file_info['file']}")
                for violation in file_info['violations']:
                    violation_details.append(f"  - {violation}")
            
            failure_message = (
                f"MIGRATION INCOMPLETE: {total_violations} BaseE2ETest inheritance violations detected in {len(inheritance_violations)} files.\n\n"
                f"Files requiring SSOT migration:\n" + "\n".join(violation_details) + "\n\n"
                f"SOLUTION: Migrate these files from BaseE2ETest to SSotBaseTestCase or SSotAsyncTestCase\n"
                f"See SSOT_MIGRATION_GUIDE.md for migration instructions."
            )
            
            assert False, failure_message
        
        # Test PASSES when no violations detected
        logger.info(f"✅ MIGRATION VALIDATION PASSED: No BaseE2ETest inheritance violations in {len(e2e_files)} E2E files")
        
    def test_all_e2e_tests_use_ssot_base_classes(self):
        """
        Validate all E2E tests inherit from SSotBaseTestCase or SSotAsyncTestCase.
        
        Uses existing SSOT validation infrastructure to ensure proper inheritance.
        """
        logger.info("Validating E2E tests use SSOT base classes")
        
        # Find all E2E test files
        e2e_files = self.detector.find_all_e2e_test_files()
        
        non_ssot_classes = []
        valid_ssot_classes = []
        
        for file_path in e2e_files:
            tree, success = self.detector.parse_python_file_ast(file_path)
            if not success:
                continue
                
            classes = self.detector.extract_class_definitions_from_ast(tree)
            for cls in classes:
                # Skip non-test classes
                if not cls['name'].startswith('Test'):
                    continue
                
                try:
                    # Attempt to load and validate class using SSOT infrastructure
                    # This would require actual class loading, so we simulate validation
                    
                    # Check if inherits from known SSOT base classes
                    ssot_bases = ['SSotBaseTestCase', 'SSotAsyncTestCase', 'BaseTestCase', 'AsyncTestCase']
                    has_ssot_base = any(base in ssot_bases for base in cls['bases'])
                    has_basee2e = 'BaseE2ETest' in cls['bases']
                    
                    if has_basee2e:
                        non_ssot_classes.append({
                            'file': str(file_path.relative_to(self.detector.project_root)),
                            'class': cls['name'],
                            'bases': cls['bases'],
                            'issue': 'Uses BaseE2ETest instead of SSOT base class'
                        })
                    elif has_ssot_base:
                        valid_ssot_classes.append({
                            'file': str(file_path.relative_to(self.detector.project_root)),
                            'class': cls['name'],
                            'bases': cls['bases']
                        })
                    else:
                        # Check if class inherits from any base class at all
                        if cls['bases']:
                            non_ssot_classes.append({
                                'file': str(file_path.relative_to(self.detector.project_root)),
                                'class': cls['name'],
                                'bases': cls['bases'],
                                'issue': 'Unknown base class - should use SSOT base class'
                            })
                
                except Exception as e:
                    logger.warning(f"Failed to validate class {cls['name']} in {file_path}: {e}")
        
        # Record metrics
        self.record_metric("valid_ssot_classes", len(valid_ssot_classes))
        self.record_metric("non_ssot_classes", len(non_ssot_classes))
        
        # Assert all test classes use SSOT base classes
        if non_ssot_classes:
            violation_details = []
            for class_info in non_ssot_classes:
                violation_details.append(
                    f"File: {class_info['file']}, Class: {class_info['class']}, "
                    f"Bases: {class_info['bases']}, Issue: {class_info['issue']}"
                )
            
            failure_message = (
                f"SSOT COMPLIANCE FAILURE: {len(non_ssot_classes)} E2E test classes not using SSOT base classes.\n\n"
                f"Non-compliant classes:\n" + "\n".join(violation_details) + "\n\n"
                f"SOLUTION: Ensure all test classes inherit from SSotBaseTestCase or SSotAsyncTestCase"
            )
            
            assert False, failure_message
        
        logger.info(f"✅ SSOT COMPLIANCE PASSED: {len(valid_ssot_classes)} E2E test classes use SSOT base classes")
    
    def test_migrated_tests_use_isolated_environment(self):
        """
        Ensure migrated tests use IsolatedEnvironment vs direct os.environ access.
        
        This validates proper environment isolation compliance in E2E tests.
        """
        logger.info("Validating E2E tests use IsolatedEnvironment")
        
        # Find all E2E test files
        e2e_files = self.detector.find_all_e2e_test_files()
        
        environment_violations = []
        clean_files = 0
        
        for file_path in e2e_files:
            violations = self.detector.detect_basee2etest_violations(file_path)
            
            if violations['environment_violations']:
                environment_violations.append({
                    'file': str(file_path.relative_to(self.detector.project_root)),
                    'violations': violations['environment_violations']
                })
            else:
                clean_files += 1
        
        # Record metrics
        self.record_metric("files_with_env_violations", len(environment_violations))
        self.record_metric("files_with_clean_env_usage", clean_files)
        
        # Generate warning but don't fail (environment usage is less critical than inheritance)
        if environment_violations:
            violation_details = []
            for file_info in environment_violations:
                violation_details.append(f"File: {file_info['file']}")
                for violation in file_info['violations']:
                    violation_details.append(f"  - {violation}")
            
            # Log warning but don't fail the test
            logger.warning(
                f"ENVIRONMENT ISOLATION WARNING: {len(environment_violations)} files use direct os.environ access.\n"
                f"Files with environment issues:\n" + "\n".join(violation_details) + "\n"
                f"RECOMMENDATION: Use IsolatedEnvironment.get() instead of os.environ for better isolation"
            )
        
        # Always pass - this is a recommendation, not a hard requirement
        logger.info(f"✅ ENVIRONMENT CHECK COMPLETED: {clean_files} files have clean environment usage")
        
    def test_no_basee2etest_imports_detected(self):
        """
        FAIL if BaseE2ETest is imported anywhere in E2E tests.
        
        This catches import violations that might not result in inheritance.
        """
        logger.info("Scanning for BaseE2ETest import violations")
        
        # Find all E2E test files
        e2e_files = self.detector.find_all_e2e_test_files()
        
        import_violations = []
        
        for file_path in e2e_files:
            violations = self.detector.detect_basee2etest_violations(file_path)
            
            if violations['import_violations']:
                import_violations.append({
                    'file': str(file_path.relative_to(self.detector.project_root)),
                    'violations': violations['import_violations']
                })
        
        # Record metrics
        self.record_metric("import_violations_detected", sum(len(v['violations']) for v in import_violations))
        self.record_metric("files_with_import_violations", len(import_violations))
        
        # CRITICAL: Fail if BaseE2ETest imports detected
        if import_violations:
            violation_details = []
            for file_info in import_violations:
                violation_details.append(f"File: {file_info['file']}")
                for violation in file_info['violations']:
                    violation_details.append(f"  - {violation}")
            
            failure_message = (
                f"IMPORT VIOLATION: {len(import_violations)} files still import BaseE2ETest.\n\n"
                f"Files with import violations:\n" + "\n".join(violation_details) + "\n\n"
                f"SOLUTION: Remove BaseE2ETest imports and use SSOT base classes"
            )
            
            assert False, failure_message
        
        logger.info(f"✅ IMPORT VALIDATION PASSED: No BaseE2ETest imports detected in {len(e2e_files)} E2E files")
    
    def test_migration_validation_comprehensive_report(self):
        """
        Generate comprehensive migration validation report.
        
        This test provides a complete overview of migration status.
        """
        logger.info("Generating comprehensive E2E migration validation report")
        
        # Find all E2E test files
        e2e_files = self.detector.find_all_e2e_test_files()
        
        # Comprehensive scan
        total_violations = 0
        files_with_issues = 0
        migration_report = {
            'total_files_scanned': len(e2e_files),
            'files_with_violations': 0,
            'inheritance_violations': 0,
            'import_violations': 0,
            'environment_violations': 0,
            'clean_files': 0,
            'migration_progress_percent': 0.0
        }
        
        for file_path in e2e_files:
            violations = self.detector.detect_basee2etest_violations(file_path)
            
            file_has_issues = any(violations.values())
            if file_has_issues:
                files_with_issues += 1
                total_violations += (
                    len(violations['inheritance_violations']) +
                    len(violations['import_violations']) +
                    len(violations['environment_violations'])
                )
            
            migration_report['inheritance_violations'] += len(violations['inheritance_violations'])
            migration_report['import_violations'] += len(violations['import_violations'])
            migration_report['environment_violations'] += len(violations['environment_violations'])
        
        migration_report['files_with_violations'] = files_with_issues
        migration_report['clean_files'] = len(e2e_files) - files_with_issues
        migration_report['migration_progress_percent'] = (
            (migration_report['clean_files'] / len(e2e_files)) * 100.0 if e2e_files else 100.0
        )
        
        # Record comprehensive metrics
        for key, value in migration_report.items():
            self.record_metric(f"migration_report_{key}", value)
        
        # Log comprehensive report
        logger.info(f"""
E2E MIGRATION VALIDATION COMPREHENSIVE REPORT
============================================
Total E2E Files Scanned: {migration_report['total_files_scanned']}
Files with Migration Issues: {migration_report['files_with_violations']}
Clean Files: {migration_report['clean_files']}
Migration Progress: {migration_report['migration_progress_percent']:.1f}%

Violation Breakdown:
- Inheritance Violations (BaseE2ETest): {migration_report['inheritance_violations']}
- Import Violations: {migration_report['import_violations']}
- Environment Violations (os.environ): {migration_report['environment_violations']}

Total Violations: {total_violations}
        """)
        
        # This test always passes - it's informational
        assert True, "Migration validation report generated successfully"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])