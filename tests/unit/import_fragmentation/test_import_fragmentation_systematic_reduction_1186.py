"""Test Issue #1186: Import Fragmentation Systematic Reduction - Phase 1 Baseline Detection

This test suite is designed to FAIL initially to expose current import fragmentation
across the UserExecutionEngine SSOT consolidation. These tests demonstrate
specific violation counts and patterns before remediation.

Expected Behavior: These tests SHOULD FAIL to demonstrate:
1. 446 fragmented import violations (target: <5)
2. 87.5% canonical import usage (target: >95%)
3. Multiple import path patterns violating SSOT principles
4. Legacy execution engine import remnants

Business Impact: Import fragmentation prevents scalable SSOT architecture
and blocks enterprise-grade multi-user isolation for $500K+ ARR functionality.
"""

import ast
import os
import pytest
import re
import sys
import unittest
from pathlib import Path
from typing import List, Set, Dict, Tuple, Counter
from collections import defaultdict, Counter


@pytest.mark.unit
class ImportFragmentationSystematicReductionTests(unittest.TestCase):
    """Test class to detect and track import fragmentation with precise metrics"""
    
    def setUp(self):
        """Set up test environment with systematic tracking"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.canonical_import = "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
        self.target_fragmentation_count = 5  # SSOT target: <5 fragmented imports
        self.target_canonical_usage = 95.0  # Target: >95% canonical usage
        self.fragmentation_patterns = {}
        self.baseline_metrics = {}
        
    def test_01_baseline_fragmentation_count_detection(self):
        """
        Test 1: Detect precise count of fragmented UserExecutionEngine imports
        
        EXPECTED TO FAIL: Should reveal 446 fragmented import violations
        Target: Reduce to <5 fragmented imports
        """
        print("\n🔍 BASELINE TEST 1: Counting fragmented UserExecutionEngine imports...")
        
        fragmented_imports = self._scan_all_fragmented_import_patterns()
        total_fragmentation_count = len(fragmented_imports)
        
        print(f"📊 Fragmentation Analysis:")
        print(f"   - Total fragmented imports found: {total_fragmentation_count}")
        print(f"   - SSOT target: <{self.target_fragmentation_count}")
        print(f"   - Reduction needed: {total_fragmentation_count - self.target_fragmentation_count}")
        
        # Store baseline for tracking
        self.baseline_metrics['total_fragmented_imports'] = total_fragmentation_count
        
        # This test should FAIL to demonstrate the problem
        self.assertLess(
            total_fragmentation_count, 
            self.target_fragmentation_count, 
            f"X BASELINE VIOLATION: Found {total_fragmentation_count} fragmented UserExecutionEngine imports. "
            f"SSOT target is <{self.target_fragmentation_count}. "
            f"Reduction of {total_fragmentation_count - self.target_fragmentation_count} imports required.\n"
            f"Top 10 fragmentation sources:\n"
            + '\n'.join([f"  - {path}: {pattern}" for path, pattern in fragmented_imports[:10]])
            + (f"\n  ... and {len(fragmented_imports) - 10} more violations" if len(fragmented_imports) > 10 else "")
        )
        
    def test_02_canonical_import_usage_percentage_measurement(self):
        """
        Test 2: Measure canonical import usage percentage across codebase
        
        EXPECTED TO FAIL: Should reveal 87.5% canonical usage (target: >95%)
        """
        print("\n🔍 BASELINE TEST 2: Measuring canonical import usage percentage...")
        
        import_analysis = self._analyze_canonical_vs_fragmented_usage()
        canonical_count = import_analysis['canonical_count']
        total_imports = import_analysis['total_imports']
        canonical_percentage = (canonical_count / total_imports * 100) if total_imports > 0 else 0
        
        print(f"📊 Canonical Usage Analysis:")
        print(f"   - Canonical imports: {canonical_count}")
        print(f"   - Total imports: {total_imports}")
        print(f"   - Canonical usage: {canonical_percentage:.1f}%")
        print(f"   - Target: >{self.target_canonical_usage}%")
        print(f"   - Gap: {self.target_canonical_usage - canonical_percentage:.1f}%")
        
        # Store baseline for tracking
        self.baseline_metrics['canonical_percentage'] = canonical_percentage
        
        # This test should FAIL to demonstrate insufficient canonical usage
        self.assertGreater(
            canonical_percentage,
            self.target_canonical_usage,
            f"X BASELINE VIOLATION: Canonical import usage is {canonical_percentage:.1f}%. "
            f"SSOT target is >{self.target_canonical_usage}%. "
            f"Need to improve canonical usage by {self.target_canonical_usage - canonical_percentage:.1f}%.\n"
            f"Current breakdown:\n"
            f"  - Canonical imports: {canonical_count}\n"
            f"  - Non-canonical imports: {total_imports - canonical_count}\n"
            f"  - Total imports analyzed: {total_imports}"
        )
        
    def test_03_legacy_execution_engine_pattern_detection(self):
        """
        Test 3: Detect legacy execution engine import patterns for elimination
        
        EXPECTED TO FAIL: Should reveal legacy patterns requiring cleanup
        """
        print("\n🔍 BASELINE TEST 3: Detecting legacy execution engine patterns...")
        
        legacy_patterns = self._scan_for_legacy_execution_engine_imports()
        legacy_count = len(legacy_patterns)
        
        print(f"📊 Legacy Pattern Analysis:")
        print(f"   - Legacy patterns found: {legacy_count}")
        print(f"   - Target: 0 legacy patterns")
        
        # Store baseline for tracking
        self.baseline_metrics['legacy_patterns'] = legacy_count
        
        # This test should FAIL to demonstrate legacy patterns exist
        self.assertEqual(
            legacy_count,
            0,
            f"X BASELINE VIOLATION: Found {legacy_count} legacy execution engine import patterns. "
            f"SSOT consolidation requires elimination of all legacy patterns.\n"
            f"Legacy patterns detected:\n"
            + '\n'.join([f"  - {path}: {pattern}" for path, pattern in legacy_patterns[:10]])
            + (f"\n  ... and {len(legacy_patterns) - 10} more legacy patterns" if len(legacy_patterns) > 10 else "")
        )
        
    def test_04_import_path_diversity_consolidation_measurement(self):
        """
        Test 4: Measure import path diversity requiring consolidation
        
        EXPECTED TO FAIL: Should reveal multiple import paths violating SSOT
        """
        print("\n🔍 BASELINE TEST 4: Measuring import path diversity...")
        
        path_diversity = self._analyze_import_path_diversity()
        unique_paths = len(path_diversity.keys())
        total_usage = sum(path_diversity.values())
        
        print(f"📊 Import Path Diversity Analysis:")
        print(f"   - Unique import paths: {unique_paths}")
        print(f"   - Total import occurrences: {total_usage}")
        print(f"   - SSOT target: 1 canonical path")
        
        # Show top import paths by usage
        sorted_paths = sorted(path_diversity.items(), key=lambda x: x[1], reverse=True)
        print(f"   - Top import paths:")
        for i, (path, count) in enumerate(sorted_paths[:5]):
            print(f"     {i+1}. '{path}' ({count} uses)")
        
        # Store baseline for tracking
        self.baseline_metrics['unique_import_paths'] = unique_paths
        
        # This test should FAIL to demonstrate path diversity
        self.assertEqual(
            unique_paths,
            1,
            f"X BASELINE VIOLATION: Found {unique_paths} different import paths for UserExecutionEngine. "
            f"SSOT requires exactly 1 canonical import path.\n"
            f"Path consolidation required for {unique_paths - 1} non-canonical paths:\n"
            + '\n'.join([f"  - '{path}' used {count} times" for path, count in sorted_paths])
        )
        
    def test_05_service_boundary_import_violation_detection(self):
        """
        Test 5: Detect service boundary violations in UserExecutionEngine imports
        
        EXPECTED TO FAIL: Should reveal cross-service import violations
        """
        print("\n🔍 BASELINE TEST 5: Detecting service boundary violations...")
        
        boundary_violations = self._check_service_boundary_import_violations()
        violation_count = len(boundary_violations)
        
        print(f"📊 Service Boundary Analysis:")
        print(f"   - Boundary violations: {violation_count}")
        print(f"   - Target: 0 violations")
        
        # Store baseline for tracking
        self.baseline_metrics['boundary_violations'] = violation_count
        
        # This test should FAIL to demonstrate boundary violations
        self.assertEqual(
            violation_count,
            0,
            f"X BASELINE VIOLATION: Found {violation_count} service boundary violations. "
            f"Each service should use independent import patterns.\n"
            f"Boundary violations detected:\n"
            + '\n'.join([f"  - {service}: {violation}" for service, violation in boundary_violations])
        )
    
    def _scan_all_fragmented_import_patterns(self) -> List[Tuple[str, str]]:
        """Comprehensive scan for all fragmented UserExecutionEngine import patterns"""
        fragmented_imports = []
        
        # Extended fragmentation patterns for comprehensive detection
        fragmentation_patterns = [
            # Legacy path patterns
            r'from.*execution_engine.*import.*UserExecutionEngine',
            r'from.*execution_engine_consolidated.*import.*UserExecutionEngine',
            r'from.*\.execution_engine.*import.*UserExecutionEngine',
            
            # Alias fragmentation patterns
            r'from.*user_execution_engine.*import.*UserExecutionEngine as.*',
            r'from.*supervisor\.execution_engine.*import.*UserExecutionEngine',
            r'import.*UserExecutionEngine.*as.*Engine',
            r'import.*UserExecutionEngine.*as.*Executor',
            
            # Non-canonical path patterns
            r'from.*agents\.execution_engine.*import.*UserExecutionEngine',
            r'from.*services\.execution.*import.*UserExecutionEngine',
            r'from.*core\.execution.*import.*UserExecutionEngine',
            
            # Relative import patterns
            r'from \.\.*execution.*import.*UserExecutionEngine',
            r'from \.\.*supervisor.*import.*UserExecutionEngine',
        ]
        
        python_files = self._get_comprehensive_python_files()
        print(f"   - Scanning {len(python_files)} Python files...")
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in fragmentation_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        fragmented_imports.append((str(py_file.relative_to(self.project_root)), match.group()))
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return fragmented_imports
    
    def _analyze_canonical_vs_fragmented_usage(self) -> Dict[str, int]:
        """Analyze canonical vs fragmented import usage patterns"""
        canonical_count = 0
        total_imports = 0
        
        python_files = self._get_comprehensive_python_files()
        canonical_pattern = re.escape("from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine")
        
        # Any import containing UserExecutionEngine
        any_ue_import_pattern = r'.*UserExecutionEngine.*'
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Count all UserExecutionEngine imports
                all_ue_imports = re.findall(any_ue_import_pattern, content, re.MULTILINE)
                total_imports += len(all_ue_imports)
                
                # Count canonical imports
                canonical_imports = re.findall(canonical_pattern, content, re.MULTILINE)
                canonical_count += len(canonical_imports)
                
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return {
            'canonical_count': canonical_count,
            'total_imports': total_imports,
            'fragmented_count': total_imports - canonical_count
        }
    
    def _scan_for_legacy_execution_engine_imports(self) -> List[Tuple[str, str]]:
        """Scan for legacy execution engine import patterns"""
        legacy_patterns = []
        
        # Legacy patterns requiring elimination
        legacy_import_patterns = [
            r'from.*execution_engine_consolidated.*import',
            r'from.*\.execution_engine\b.*import',
            r'from.*legacy.*execution.*import',
            r'from.*deprecated.*execution.*import',
            r'import.*execution_engine_consolidated',
        ]
        
        python_files = self._get_comprehensive_python_files()
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in legacy_import_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        legacy_patterns.append((str(py_file.relative_to(self.project_root)), match.group()))
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return legacy_patterns
    
    def _analyze_import_path_diversity(self) -> Dict[str, int]:
        """Analyze diversity of import paths for UserExecutionEngine"""
        import_path_counts = defaultdict(int)
        
        python_files = self._get_comprehensive_python_files()
        
        # Pattern to capture full import statements
        import_pattern = r'(from [^\s]+ import [^;\n]*UserExecutionEngine[^;\n]*|import [^;\n]*UserExecutionEngine[^;\n]*)'
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matches = re.finditer(import_pattern, content, re.MULTILINE)
                for match in matches:
                    import_statement = match.group(1).strip()
                    # Normalize whitespace
                    normalized_import = ' '.join(import_statement.split())
                    import_path_counts[normalized_import] += 1
                    
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return dict(import_path_counts)
    
    def _check_service_boundary_import_violations(self) -> List[Tuple[str, str]]:
        """Check for service boundary violations in imports"""
        violations = []
        
        # Service boundaries
        services = {
            'netra_backend': self.project_root / 'netra_backend',
            'auth_service': self.project_root / 'auth_service',
            'frontend': self.project_root / 'frontend',
        }
        
        for service_name, service_path in services.items():
            if not service_path.exists():
                continue
                
            python_files = self._get_python_files_in_path(service_path)
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for cross-service UserExecutionEngine imports
                    for other_service in services:
                        if other_service != service_name:
                            cross_import_pattern = f'from {other_service}.*UserExecutionEngine'
                            if re.search(cross_import_pattern, content):
                                violations.append((
                                    service_name, 
                                    f"Cross-service import from {other_service}"
                                ))
                                
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
                    
        return violations
    
    def _get_comprehensive_python_files(self) -> List[Path]:
        """Get comprehensive list of Python files for analysis"""
        python_files = []
        
        # Comprehensive search paths
        search_paths = [
            self.project_root / 'netra_backend',
            self.project_root / 'auth_service',
            self.project_root / 'tests',
            self.project_root / 'shared',
            self.project_root / 'scripts',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                python_files.extend(self._get_python_files_in_path(search_path))
                
        print(f"   - Found {len(python_files)} Python files across {len(search_paths)} directories")
        return python_files
    
    def _get_python_files_in_path(self, path: Path) -> List[Path]:
        """Get Python files in a specific path"""
        try:
            # Exclude common non-source directories
            excluded_dirs = {'.venv', 'venv', '__pycache__', '.git', 'node_modules', 'google-cloud-sdk'}
            
            python_files = []
            for py_file in path.rglob('*.py'):
                # Skip if any parent directory is excluded
                if any(excluded_dir in py_file.parts for excluded_dir in excluded_dirs):
                    continue
                python_files.append(py_file)
                
            return python_files
        except (OSError, PermissionError):
            return []


if __name__ == '__main__':
    print("🚨 Issue #1186 Import Fragmentation Systematic Reduction - Baseline Detection")
    print("=" * 80)
    print("WARNING️  WARNING: These tests are DESIGNED TO FAIL to establish baseline metrics")
    print("📊 Expected: 5 test failures showing import fragmentation violations")
    print("🎯 Goal: Baseline measurement for 446-><5 fragmentation reduction")
    print("💰 Impact: Enables $500K+ ARR SSOT architecture consolidation")
    print("=" * 80)
    
    unittest.main(verbosity=2)