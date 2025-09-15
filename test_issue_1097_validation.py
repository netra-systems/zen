#!/usr/bin/env python3
"""
Issue #1097 SSOT Migration Validation Test
Tests for remaining unittest.TestCase violations and migration progress
"""

import os
import ast
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import unittest

class TestCase1097SSotMigrationValidation(unittest.TestCase):
    """Validation tests for Issue #1097 SSOT migration progress."""
    
    def setUp(self):
        """Set up validation test."""
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.mission_critical_path = self.project_root / "tests" / "mission_critical"
        self.test_paths = [
            self.project_root / "tests",
            self.project_root / "netra_backend" / "tests", 
            self.project_root / "auth_service" / "tests",
        ]
        
    def test_count_unittest_testcase_violations(self):
        """Count remaining unittest.TestCase violations across test files."""
        violations = self._find_unittest_testcase_violations()
        
        print(f"\n=== Issue #1097 SSOT Migration Status ===")
        print(f"Total unittest.TestCase violations found: {len(violations)}")
        
        if violations:
            print(f"\nViolation breakdown by category:")
            
            # Categorize violations
            mission_critical = [v for v in violations if "mission_critical" in str(v['file'])]
            unit_tests = [v for v in violations if "/unit/" in str(v['file']) or "test_unit" in str(v['file'])]
            integration_tests = [v for v in violations if "/integration/" in str(v['file']) or "test_integration" in str(v['file'])]
            other_tests = [v for v in violations if v not in mission_critical + unit_tests + integration_tests]
            
            print(f"  Mission Critical: {len(mission_critical)} files")
            print(f"  Unit Tests: {len(unit_tests)} files")
            print(f"  Integration Tests: {len(integration_tests)} files") 
            print(f"  Other Test Files: {len(other_tests)} files")
            
            if mission_critical:
                print(f"\nMission Critical violations (HIGH PRIORITY):")
                for v in mission_critical[:10]:  # Show first 10
                    print(f"  - {v['file']}: line {v['line']}")
                if len(mission_critical) > 10:
                    print(f"  ... and {len(mission_critical) - 10} more")
                    
            if unit_tests:
                print(f"\nUnit test violations (MEDIUM PRIORITY):")
                for v in unit_tests[:5]:  # Show first 5
                    print(f"  - {v['file']}: line {v['line']}")
                if len(unit_tests) > 5:
                    print(f"  ... and {len(unit_tests) - 5} more")
        else:
            print("✅ SUCCESS: No unittest.TestCase violations found!")
            print("✅ Issue #1097 migration appears to be COMPLETE")
            
        return violations
        
    def test_ssot_import_compliance(self):
        """Test for proper SSOT import usage in test files."""
        violations = self._find_import_violations()
        
        print(f"\n=== SSOT Import Compliance Check ===")
        print(f"Import violations found: {len(violations)}")
        
        if violations:
            print(f"Files still using 'import unittest':")
            for v in violations[:10]:
                print(f"  - {v['file']}: line {v['line']}")
        else:
            print("✅ All test files using proper SSOT imports")
            
        return violations
        
    def test_migration_readiness_assessment(self):
        """Assess migration readiness and provide recommendations."""
        unittest_violations = self._find_unittest_testcase_violations()
        import_violations = self._find_import_violations()
        
        total_violations = len(unittest_violations) + len(import_violations)
        
        print(f"\n=== Migration Readiness Assessment ===")
        print(f"Total violations requiring migration: {total_violations}")
        
        if total_violations == 0:
            print("✅ MIGRATION COMPLETE: Issue #1097 ready for closure")
            status = "COMPLETE"
        elif total_violations <= 5:
            print("🔶 NEARLY COMPLETE: Few violations remaining")
            status = "NEARLY_COMPLETE"
        elif total_violations <= 23:
            print("🔄 IN PROGRESS: Original target violations or fewer")
            status = "IN_PROGRESS"
        else:
            print("⚠️  MORE WORK NEEDED: Additional violations discovered")
            status = "MORE_WORK_NEEDED"
            
        return {
            'status': status,
            'total_violations': total_violations,
            'unittest_violations': len(unittest_violations),
            'import_violations': len(import_violations)
        }
        
    def _find_unittest_testcase_violations(self) -> List[Dict]:
        """Find files still inheriting from unittest.TestCase."""
        violations = []
        
        for test_path in self.test_paths:
            if not test_path.exists():
                continue
                
            for py_file in test_path.rglob("test_*.py"):
                if py_file.is_file():
                    violations.extend(self._check_file_for_unittest_testcase(py_file))
                    
        return violations
        
    def _find_import_violations(self) -> List[Dict]:
        """Find files still importing unittest."""
        violations = []
        
        for test_path in self.test_paths:
            if not test_path.exists():
                continue
                
            for py_file in test_path.rglob("test_*.py"):
                if py_file.is_file():
                    violations.extend(self._check_file_for_unittest_import(py_file))
                    
        return violations
        
    def _check_file_for_unittest_testcase(self, file_path: Path) -> List[Dict]:
        """Check specific file for unittest.TestCase inheritance."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if (isinstance(base, ast.Attribute) and 
                            isinstance(base.value, ast.Name) and
                            base.value.id == 'unittest' and 
                            base.attr == 'TestCase'):
                            violations.append({
                                'file': file_path,
                                'line': node.lineno,
                                'class': node.name,
                                'violation_type': 'unittest.TestCase_inheritance'
                            })
                        elif (isinstance(base, ast.Name) and 
                              base.id == 'TestCase'):
                            # Check if TestCase is imported from unittest
                            if self._has_unittest_testcase_import(content):
                                violations.append({
                                    'file': file_path,
                                    'line': node.lineno,
                                    'class': node.name,
                                    'violation_type': 'TestCase_inheritance'
                                })
                                
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            
        return violations
        
    def _check_file_for_unittest_import(self, file_path: Path) -> List[Dict]:
        """Check specific file for unittest imports."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if (line_stripped.startswith('import unittest') or
                    line_stripped.startswith('from unittest')):
                    violations.append({
                        'file': file_path,
                        'line': i,
                        'import': line_stripped,
                        'violation_type': 'unittest_import'
                    })
                    
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            
        return violations
        
    def _has_unittest_testcase_import(self, content: str) -> bool:
        """Check if content has unittest.TestCase import."""
        lines = content.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if ('from unittest import' in line_stripped and 'TestCase' in line_stripped):
                return True
            if line_stripped == 'import unittest':
                return True
        return False

if __name__ == "__main__":
    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCase1097SSotMigrationValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with proper code
    sys.exit(0 if result.wasSuccessful() else 1)