"""
Unittest Migration Compliance Tests - Issue #1097 Test Plan Implementation

These tests track and validate the migration progress from legacy unittest.TestCase
to SSOT base classes. They count remaining violations and measure compliance.

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures consistent test infrastructure and tracks migration progress.

CRITICAL: These tests follow SSOT patterns and use SSotBaseTestCase.
They are designed to FAIL initially to document the current state.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict

# SSOT imports following project requirements
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUnittestMigrationCompliance(SSotBaseTestCase):
    """
    Migration compliance tests for Issue #1097.
    
    These tests track the progress of migrating from legacy unittest.TestCase
    patterns to SSOT base classes. They provide metrics and identify remaining
    work to complete the migration.
    
    Expected to FAIL initially to document current migration state.
    """

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.repo_root = Path("/Users/anthony/Desktop/netra-apex")
        
        # Define all test directories in the codebase
        self.test_directories = [
            self.repo_root / "tests",
            self.repo_root / "netra_backend" / "tests", 
            self.repo_root / "auth_service" / "tests",
            self.repo_root / "frontend" / "tests",
            self.repo_root / "test_framework" / "tests",
            self.repo_root / "shared" / "tests",
        ]
        
        # Migration target thresholds
        self.target_ssot_compliance_percentage = 85.0  # Initial realistic target
        self.critical_files_max_violations = 0  # Critical files must be 100% compliant
        
    def _find_all_test_files(self) -> List[Path]:
        """Find all Python test files across the entire codebase."""
        test_files = []
        
        for test_dir in self.test_directories:
            if test_dir.exists():
                # Find various test file patterns
                patterns = ["test_*.py", "*_test.py", "*_tests.py"]
                for pattern in patterns:
                    test_files.extend(test_dir.rglob(pattern))
        
        # Also find files in subdirectories that contain test classes
        for test_dir in self.test_directories:
            if test_dir.exists():
                for py_file in test_dir.rglob("*.py"):
                    if py_file not in test_files and self._file_contains_test_classes(py_file):
                        test_files.append(py_file)
        
        return list(set(test_files))  # Remove duplicates
    
    def _file_contains_test_classes(self, file_path: Path) -> bool:
        """Check if a Python file contains test classes."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a test class
                    if (node.name.startswith('Test') or 
                        node.name.endswith('Test') or 
                        'Test' in node.name):
                        return True
                        
                    # Check if it inherits from test base classes
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if 'Test' in base.id:
                                return True
                        elif isinstance(base, ast.Attribute):
                            if 'Test' in base.attr:
                                return True
            
            return False
            
        except Exception:
            return False
    
    def _analyze_test_class_inheritance(self, file_path: Path) -> Dict[str, any]:
        """
        Analyze a test file for inheritance patterns and compliance.
        
        Returns:
            Dictionary with analysis results including violations and compliance status
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analysis = {
                'file_path': str(file_path.relative_to(self.repo_root)),
                'test_classes': [],
                'has_ssot_imports': False,
                'has_unittest_imports': False,
                'ssot_compliant_classes': 0,
                'legacy_unittest_classes': 0,
                'double_inheritance_classes': 0,
                'violations': []
            }
            
            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'unittest' in alias.name:
                            analysis['has_unittest_imports'] = True
                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'test_framework.ssot' in node.module:
                        analysis['has_ssot_imports'] = True
                    elif node.module and 'unittest' in node.module:
                        analysis['has_unittest_imports'] = True
            
            # Analyze class inheritance
            ssot_base_classes = {
                'SSotBaseTestCase', 'SSotAsyncTestCase',
                'BaseTestCase', 'AsyncTestCase'
            }
            
            unittest_classes = {
                'unittest.TestCase', 'TestCase'
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip non-test classes
                    if not (node.name.startswith('Test') or 'Test' in node.name):
                        continue
                    
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            if isinstance(base.value, ast.Name):
                                base_classes.append(f"{base.value.id}.{base.attr}")
                    
                    # Classify the class
                    has_ssot_base = any(base in ssot_base_classes for base in base_classes)
                    has_unittest_base = any(base in unittest_classes for base in base_classes)
                    
                    class_info = {
                        'name': node.name,
                        'base_classes': base_classes,
                        'has_ssot_base': has_ssot_base,
                        'has_unittest_base': has_unittest_base
                    }
                    
                    analysis['test_classes'].append(class_info)
                    
                    if has_ssot_base and has_unittest_base:
                        analysis['double_inheritance_classes'] += 1
                        analysis['violations'].append(
                            f"Double inheritance: {node.name} inherits from both SSOT and unittest classes"
                        )
                    elif has_ssot_base:
                        analysis['ssot_compliant_classes'] += 1
                    elif has_unittest_base:
                        analysis['legacy_unittest_classes'] += 1
                        analysis['violations'].append(
                            f"Legacy unittest: {node.name} uses unittest.TestCase without SSOT"
                        )
            
            return analysis
            
        except Exception as e:
            return {
                'file_path': str(file_path.relative_to(self.repo_root)),
                'error': str(e),
                'violations': [f"Failed to analyze file: {e}"]
            }
    
    def test_measure_overall_ssot_compliance(self):
        """
        Test to measure overall SSOT compliance across the codebase.
        
        This provides a baseline measurement and tracks migration progress.
        EXPECTED TO FAIL INITIALLY with current compliance percentage.
        """
        test_files = self._find_all_test_files()
        total_test_classes = 0
        ssot_compliant_classes = 0
        legacy_unittest_classes = 0
        double_inheritance_classes = 0
        
        file_violations = []
        
        for file_path in test_files:
            analysis = self._analyze_test_class_inheritance(file_path)
            
            if 'error' in analysis:
                continue
                
            total_test_classes += len(analysis['test_classes'])
            ssot_compliant_classes += analysis['ssot_compliant_classes']
            legacy_unittest_classes += analysis['legacy_unittest_classes']
            double_inheritance_classes += analysis['double_inheritance_classes']
            
            if analysis['violations']:
                file_violations.append({
                    'file': analysis['file_path'],
                    'violations': analysis['violations']
                })
        
        # Calculate compliance metrics
        compliance_percentage = (
            (ssot_compliant_classes / total_test_classes * 100) 
            if total_test_classes > 0 else 100
        )
        
        # Record comprehensive metrics
        self.record_metric("total_test_files", len(test_files))
        self.record_metric("total_test_classes", total_test_classes)
        self.record_metric("ssot_compliant_classes", ssot_compliant_classes)
        self.record_metric("legacy_unittest_classes", legacy_unittest_classes)
        self.record_metric("double_inheritance_classes", double_inheritance_classes)
        self.record_metric("compliance_percentage", compliance_percentage)
        self.record_metric("files_with_violations", len(file_violations))
        
        # Determine if we meet the target
        meets_target = compliance_percentage >= self.target_ssot_compliance_percentage
        
        if not meets_target or legacy_unittest_classes > 0 or double_inheritance_classes > 0:
            # Create detailed failure message
            failure_parts = [
                f"SSOT Migration Compliance Report:",
                f"  Total test files: {len(test_files)}",
                f"  Total test classes: {total_test_classes}",
                f"  SSOT compliant classes: {ssot_compliant_classes}",
                f"  Legacy unittest classes: {legacy_unittest_classes}",
                f"  Double inheritance violations: {double_inheritance_classes}",
                f"  Current compliance: {compliance_percentage:.1f}%",
                f"  Target compliance: {self.target_ssot_compliance_percentage}%",
                f"  Files with violations: {len(file_violations)}",
                ""
            ]
            
            if file_violations:
                failure_parts.append("Sample violations (first 5 files):")
                for i, violation in enumerate(file_violations[:5]):
                    failure_parts.append(f"  {violation['file']}:")
                    for v in violation['violations'][:3]:  # Limit violations per file
                        failure_parts.append(f"    - {v}")
                    if len(violation['violations']) > 3:
                        failure_parts.append(f"    - ... and {len(violation['violations']) - 3} more")
                
                if len(file_violations) > 5:
                    failure_parts.append(f"  ... and {len(file_violations) - 5} more files with violations")
            
            failure_message = "\n".join(failure_parts)
            
            # This test is EXPECTED TO FAIL initially
            self.fail(failure_message)
        
        # If we get here, compliance target is met
        self.logger.info(f"SSOT compliance target achieved: {compliance_percentage:.1f}% >= {self.target_ssot_compliance_percentage}%")
    
    def test_critical_files_must_be_fully_compliant(self):
        """
        Test that critical/mission-critical files have zero unittest violations.
        
        Critical files must be 100% SSOT compliant for business value protection.
        """
        critical_patterns = [
            "**/test_websocket_agent_events_suite.py",
            "**/test_mission_critical_*.py", 
            "**/test_golden_path_*.py",
            "**/test_*_critical.py",
            "**/tests/mission_critical/**/*.py",
            "**/tests/critical/**/*.py",
        ]
        
        critical_files = []
        for pattern in critical_patterns:
            critical_files.extend(self.repo_root.glob(pattern))
        
        critical_violations = []
        total_critical_classes = 0
        
        for file_path in critical_files:
            if not file_path.exists():
                continue
                
            analysis = self._analyze_test_class_inheritance(file_path)
            
            if 'error' in analysis:
                critical_violations.append({
                    'file': analysis['file_path'],
                    'error': analysis['error']
                })
                continue
            
            total_critical_classes += len(analysis['test_classes'])
            
            if analysis['violations']:
                critical_violations.append({
                    'file': analysis['file_path'],
                    'violations': analysis['violations']
                })
        
        # Record metrics
        self.record_metric("critical_files_count", len(critical_files))
        self.record_metric("critical_test_classes", total_critical_classes)
        self.record_metric("critical_files_with_violations", len(critical_violations))
        
        if critical_violations:
            failure_parts = [
                f"CRITICAL: {len(critical_violations)} critical files have SSOT violations:",
                ""
            ]
            
            for violation in critical_violations:
                failure_parts.append(f"  {violation['file']}:")
                if 'error' in violation:
                    failure_parts.append(f"    ERROR: {violation['error']}")
                else:
                    for v in violation['violations']:
                        failure_parts.append(f"    - {v}")
                failure_parts.append("")
            
            failure_parts.extend([
                "Critical files MUST be 100% SSOT compliant for business value protection.",
                "These files handle $500K+ ARR functionality and cannot have test infrastructure inconsistencies."
            ])
            
            failure_message = "\n".join(failure_parts)
            
            # Critical files MUST be fully compliant
            self.fail(failure_message)
        
        self.logger.info(f"All {len(critical_files)} critical files are fully SSOT compliant!")
    
    def test_track_migration_progress_by_directory(self):
        """
        Test to track migration progress broken down by directory.
        
        This helps identify which areas of the codebase need focus.
        """
        test_files = self._find_all_test_files()
        directory_stats = defaultdict(lambda: {
            'files': 0,
            'classes': 0,
            'ssot_compliant': 0,
            'legacy_unittest': 0,
            'double_inheritance': 0,
            'compliance_percentage': 0.0
        })
        
        for file_path in test_files:
            # Determine directory category
            relative_path = file_path.relative_to(self.repo_root)
            if str(relative_path).startswith('tests/'):
                directory = 'tests (root)'
            elif str(relative_path).startswith('netra_backend/tests/'):
                directory = 'netra_backend/tests'
            elif str(relative_path).startswith('auth_service/tests/'):
                directory = 'auth_service/tests'
            elif str(relative_path).startswith('frontend/tests/'):
                directory = 'frontend/tests'
            elif str(relative_path).startswith('test_framework/tests/'):
                directory = 'test_framework/tests'
            else:
                directory = 'other'
            
            analysis = self._analyze_test_class_inheritance(file_path)
            
            if 'error' in analysis:
                continue
            
            stats = directory_stats[directory]
            stats['files'] += 1
            stats['classes'] += len(analysis['test_classes'])
            stats['ssot_compliant'] += analysis['ssot_compliant_classes']
            stats['legacy_unittest'] += analysis['legacy_unittest_classes']
            stats['double_inheritance'] += analysis['double_inheritance_classes']
        
        # Calculate compliance percentages
        directories_below_target = []
        
        for directory, stats in directory_stats.items():
            if stats['classes'] > 0:
                stats['compliance_percentage'] = (
                    stats['ssot_compliant'] / stats['classes'] * 100
                )
                
                if stats['compliance_percentage'] < self.target_ssot_compliance_percentage:
                    directories_below_target.append((directory, stats))
        
        # Record detailed metrics
        for directory, stats in directory_stats.items():
            self.record_metric(f"directory_{directory.replace('/', '_')}_compliance", 
                             stats['compliance_percentage'])
        
        self.record_metric("directories_below_target", len(directories_below_target))
        
        if directories_below_target:
            failure_parts = [
                f"Migration Progress by Directory:",
                f"Target compliance: {self.target_ssot_compliance_percentage}%",
                ""
            ]
            
            for directory, stats in directory_stats.items():
                status = "✓" if stats['compliance_percentage'] >= self.target_ssot_compliance_percentage else "✗"
                failure_parts.append(
                    f"  {status} {directory}: {stats['compliance_percentage']:.1f}% "
                    f"({stats['ssot_compliant']}/{stats['classes']} classes, "
                    f"{stats['files']} files)"
                )
            
            failure_parts.append("")
            failure_parts.append(f"Directories below target ({len(directories_below_target)}):")
            
            for directory, stats in directories_below_target:
                failure_parts.extend([
                    f"  {directory}:",
                    f"    - Files: {stats['files']}",
                    f"    - Classes: {stats['classes']}",
                    f"    - SSOT compliant: {stats['ssot_compliant']}",
                    f"    - Legacy unittest: {stats['legacy_unittest']}",
                    f"    - Double inheritance: {stats['double_inheritance']}",
                    f"    - Compliance: {stats['compliance_percentage']:.1f}%",
                    ""
                ])
            
            failure_message = "\n".join(failure_parts)
            
            # This may fail initially if directories are below target
            self.fail(failure_message)
        
        self.logger.info("All directories meet SSOT compliance targets!")
    
    def test_detect_high_priority_migration_candidates(self):
        """
        Test to identify high-priority files for migration.
        
        This helps prioritize migration efforts by identifying files with the most
        legacy unittest usage and potential business impact.
        """
        test_files = self._find_all_test_files()
        migration_candidates = []
        
        for file_path in test_files:
            analysis = self._analyze_test_class_inheritance(file_path)
            
            if 'error' in analysis:
                continue
            
            # Calculate priority score
            priority_score = 0
            
            # High priority for files with many legacy classes
            priority_score += analysis['legacy_unittest_classes'] * 10
            
            # Very high priority for double inheritance violations
            priority_score += analysis['double_inheritance_classes'] * 50
            
            # Higher priority for files in critical paths
            file_path_str = str(file_path).lower()
            if any(keyword in file_path_str for keyword in 
                   ['websocket', 'agent', 'auth', 'critical', 'mission']):
                priority_score += 25
            
            # Higher priority for files with many test classes
            if len(analysis['test_classes']) > 5:
                priority_score += 15
            
            if priority_score > 0:
                migration_candidates.append({
                    'file': analysis['file_path'],
                    'priority_score': priority_score,
                    'legacy_classes': analysis['legacy_unittest_classes'],
                    'double_inheritance': analysis['double_inheritance_classes'],
                    'total_classes': len(analysis['test_classes']),
                    'violations': analysis['violations']
                })
        
        # Sort by priority score
        migration_candidates.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Record metrics
        self.record_metric("migration_candidates_count", len(migration_candidates))
        self.record_metric("high_priority_candidates", 
                          len([c for c in migration_candidates if c['priority_score'] >= 50]))
        
        if migration_candidates:
            failure_parts = [
                f"High-Priority Migration Candidates ({len(migration_candidates)} files):",
                ""
            ]
            
            # Show top 10 candidates
            for i, candidate in enumerate(migration_candidates[:10]):
                failure_parts.extend([
                    f"  {i+1}. {candidate['file']} (Priority: {candidate['priority_score']})",
                    f"     Legacy classes: {candidate['legacy_classes']}, "
                    f"Double inheritance: {candidate['double_inheritance']}, "
                    f"Total classes: {candidate['total_classes']}",
                ])
                
                if candidate['violations']:
                    failure_parts.append(f"     Issues: {', '.join(candidate['violations'][:2])}")
                failure_parts.append("")
            
            if len(migration_candidates) > 10:
                failure_parts.append(f"  ... and {len(migration_candidates) - 10} more candidates")
            
            failure_message = "\n".join(failure_parts)
            
            # This will fail if there are migration candidates
            self.fail(failure_message)
        
        self.logger.info("No high-priority migration candidates found - migration complete!")


if __name__ == "__main__":
    # Allow running this test file directly for quick validation
    import pytest
    pytest.main([__file__, "-v"])