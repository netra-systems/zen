"""Test Issue #1186: UserExecutionEngine SSOT Consolidation - Phase 1 Reproduction Tests

This test suite is designed to FAIL initially to expose the current UserExecutionEngine
import fragmentation and singleton violations. These tests demonstrate the problem
before SSOT consolidation is implemented.

Expected Behavior: These tests SHOULD FAIL to demonstrate:
1. Fragmented import paths across the codebase
2. Singleton violations in user isolation
3. Import path inconsistency
4. Multiple factory patterns for the same functionality

Business Impact: The fragmentation prevents enterprise-grade multi-user isolation
and violates SSOT principles, blocking $500K+ ARR chat functionality scalability.
"""

import ast
import os
import pytest
import re
import sys
import unittest
import pytest
from pathlib import Path
from typing import List, Set, Dict, Tuple
from collections import defaultdict


@pytest.mark.unit
class UserExecutionEngineImportFragmentationTests(unittest.TestCase):
    """Test class to expose UserExecutionEngine import fragmentation issues"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.expected_canonical_import = "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
        self.fragmented_patterns = []
        self.import_analysis = {}
        
    def test_1_detect_fragmented_import_paths(self):
        """
        Test 1: Detect fragmented UserExecutionEngine import paths across codebase
        
        EXPECTED TO FAIL: Should reveal 921+ fragmented import patterns
        """
        print("\n🔍 PHASE 1 TEST 1: Detecting UserExecutionEngine import fragmentation...")
        
        fragmented_imports = self._scan_for_fragmented_imports()
        
        # This test should FAIL to demonstrate the problem
        self.assertLess(
            len(fragmented_imports), 
            5, 
            f"X EXPECTED FAILURE: Found {len(fragmented_imports)} fragmented UserExecutionEngine imports. "
            f"This indicates severe import path fragmentation violating SSOT principles:\n"
            + '\n'.join([f"  - {path}: {pattern}" for path, pattern in fragmented_imports[:10]])
            + (f"\n  ... and {len(fragmented_imports) - 10} more" if len(fragmented_imports) > 10 else "")
        )
        
    def test_2_singleton_violation_detection(self):
        """
        Test 2: Detect singleton pattern violations in UserExecutionEngine usage
        
        EXPECTED TO FAIL: Should reveal multiple singleton instantiation patterns
        """
        print("\n🔍 PHASE 1 TEST 2: Detecting singleton violations...")
        
        singleton_violations = self._scan_for_singleton_violations()
        
        # This test should FAIL to demonstrate singleton violations
        self.assertEqual(
            len(singleton_violations),
            0,
            f"X EXPECTED FAILURE: Found {len(singleton_violations)} singleton violations in UserExecutionEngine usage. "
            f"This prevents proper user isolation required for enterprise deployment:\n"
            + '\n'.join([f"  - {path}: {violation}" for path, violation in singleton_violations[:5]])
            + (f"\n  ... and {len(singleton_violations) - 5} more" if len(singleton_violations) > 5 else "")
        )
        
    def test_3_import_path_consistency_validation(self):
        """
        Test 3: Validate import path consistency across all services
        
        EXPECTED TO FAIL: Should reveal inconsistent import patterns
        """
        print("\n🔍 PHASE 1 TEST 3: Validating import path consistency...")
        
        import_patterns = self._analyze_import_path_consistency()
        unique_patterns = set(import_patterns.keys())
        
        # This test should FAIL to demonstrate inconsistency
        self.assertLessEqual(
            len(unique_patterns),
            1,
            f"X EXPECTED FAILURE: Found {len(unique_patterns)} different import patterns for UserExecutionEngine. "
            f"SSOT requires exactly 1 canonical pattern. Found patterns:\n"
            + '\n'.join([f"  - '{pattern}' used in {len(files)} files" for pattern, files in import_patterns.items()])
        )
        
    def test_4_factory_pattern_duplication_detection(self):
        """
        Test 4: Detect factory pattern duplication for UserExecutionEngine
        
        EXPECTED TO FAIL: Should reveal multiple factory implementations
        """
        print("\n🔍 PHASE 1 TEST 4: Detecting factory pattern duplication...")
        
        factory_patterns = self._scan_for_factory_duplication()
        
        # This test should FAIL to demonstrate duplication
        self.assertLessEqual(
            len(factory_patterns),
            1,
            f"X EXPECTED FAILURE: Found {len(factory_patterns)} different factory patterns for UserExecutionEngine. "
            f"SSOT requires exactly 1 canonical factory. Found factories:\n"
            + '\n'.join([f"  - {path}: {factory_type}" for path, factory_type in factory_patterns])
        )
        
    def test_5_cross_service_import_boundary_validation(self):
        """
        Test 5: Validate service boundary violations in UserExecutionEngine imports
        
        EXPECTED TO FAIL: Should reveal cross-service import violations
        """
        print("\n🔍 PHASE 1 TEST 5: Validating service boundary compliance...")
        
        boundary_violations = self._check_service_boundary_violations()
        
        # This test should FAIL to demonstrate boundary violations
        self.assertEqual(
            len(boundary_violations),
            0,
            f"X EXPECTED FAILURE: Found {len(boundary_violations)} service boundary violations. "
            f"Each service should have independent UserExecutionEngine access:\n"
            + '\n'.join([f"  - {service}: {violation}" for service, violation in boundary_violations])
        )
    
    def _scan_for_fragmented_imports(self) -> List[Tuple[str, str]]:
        """Scan codebase for fragmented UserExecutionEngine imports"""
        fragmented_imports = []
        
        # Patterns that indicate fragmentation
        fragmentation_patterns = [
            r'from.*execution_engine.*import.*UserExecutionEngine',  # Legacy path
            r'from.*user_execution_engine.*import.*UserExecutionEngine as ExecutionEngine',  # Alias fragmentation
            r'from.*supervisor\.execution_engine.*import.*UserExecutionEngine',  # Old path
            r'import.*UserExecutionEngine.*as.*',  # Alias variations
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in fragmentation_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        fragmented_imports.append((str(py_file), match))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return fragmented_imports
    
    def _scan_for_singleton_violations(self) -> List[Tuple[str, str]]:
        """Scan for singleton pattern violations"""
        violations = []
        
        # Patterns that indicate singleton violations
        singleton_patterns = [
            r'UserExecutionEngine\(\)',  # Direct instantiation without factory
            r'_instance.*UserExecutionEngine',  # Instance caching
            r'global.*UserExecutionEngine',  # Global instance
            r'@.*singleton.*UserExecutionEngine',  # Singleton decorator
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in singleton_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        violations.append((str(py_file), match))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return violations
    
    def _analyze_import_path_consistency(self) -> Dict[str, List[str]]:
        """Analyze import path consistency across codebase"""
        import_patterns = defaultdict(list)
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find all UserExecutionEngine imports
                import_lines = re.findall(
                    r'from.*UserExecutionEngine.*|import.*UserExecutionEngine.*',
                    content,
                    re.MULTILINE
                )
                
                for import_line in import_lines:
                    normalized_import = import_line.strip()
                    import_patterns[normalized_import].append(str(py_file))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return dict(import_patterns)
    
    def _scan_for_factory_duplication(self) -> List[Tuple[str, str]]:
        """Scan for factory pattern duplication"""
        factories = []
        
        # Patterns that indicate factory implementations
        factory_patterns = [
            r'class.*ExecutionEngineFactory',
            r'class.*UserExecutionEngineFactory', 
            r'def.*create_execution_engine',
            r'def.*get_execution_engine',
            r'def.*execution_engine_factory',
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in factory_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        factories.append((str(py_file), match))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return factories
    
    def _check_service_boundary_violations(self) -> List[Tuple[str, str]]:
        """Check for service boundary violations"""
        violations = []
        
        # Service boundaries that should be independent
        services = ['netra_backend', 'auth_service', 'frontend']
        
        for service in services:
            service_path = self.project_root / service
            if not service_path.exists():
                continue
                
            for py_file in self._get_python_files_in_path(service_path):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for cross-service imports
                    for other_service in services:
                        if other_service != service:
                            cross_import_pattern = f'from {other_service}.*UserExecutionEngine'
                            if re.search(cross_import_pattern, content):
                                violations.append((service, f"Cross-service import from {other_service}"))
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
                    
        return violations
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the project"""
        python_files = []
        
        # Focus on main source directories to avoid timeout
        search_paths = [
            self.project_root / 'netra_backend' / 'app',
            self.project_root / 'tests' / 'unit',
            self.project_root / 'tests' / 'integration',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                python_files.extend(self._get_python_files_in_path(search_path))
                
        return python_files
    
    def _get_python_files_in_path(self, path: Path) -> List[Path]:
        """Get Python files in a specific path"""
        try:
            return list(path.rglob('*.py'))
        except (OSError, PermissionError):
            return []


@pytest.mark.unit
class UserExecutionEngineUserIsolationViolationsTests(unittest.TestCase):
    """Test class to expose user isolation violations in UserExecutionEngine"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        
    def test_6_shared_state_detection(self):
        """
        Test 6: Detect shared state violations that prevent user isolation
        
        EXPECTED TO FAIL: Should reveal shared state between users
        """
        print("\n🔍 PHASE 1 TEST 6: Detecting shared state violations...")
        
        shared_state_violations = self._scan_for_shared_state()
        
        # This test should FAIL to demonstrate shared state
        self.assertEqual(
            len(shared_state_violations),
            0,
            f"X EXPECTED FAILURE: Found {len(shared_state_violations)} shared state violations. "
            f"These prevent proper user isolation required for enterprise deployment:\n"
            + '\n'.join([f"  - {path}: {violation}" for path, violation in shared_state_violations[:5]])
        )
        
    def test_7_global_variable_contamination(self):
        """
        Test 7: Detect global variable contamination in UserExecutionEngine
        
        EXPECTED TO FAIL: Should reveal global variables that contaminate user sessions
        """
        print("\n🔍 PHASE 1 TEST 7: Detecting global variable contamination...")
        
        global_contamination = self._scan_for_global_contamination()
        
        # This test should FAIL to demonstrate contamination
        self.assertEqual(
            len(global_contamination),
            0,
            f"X EXPECTED FAILURE: Found {len(global_contamination)} global variable contamination issues. "
            f"These cause user session bleeding and security vulnerabilities:\n"
            + '\n'.join([f"  - {path}: {contamination}" for path, contamination in global_contamination])
        )
    
    def _scan_for_shared_state(self) -> List[Tuple[str, str]]:
        """Scan for shared state violations"""
        violations = []
        
        # Patterns that indicate shared state
        shared_state_patterns = [
            r'class.*UserExecutionEngine.*:.*\n.*_instance.*=',  # Class-level instance
            r'_shared_.*=',  # Shared variables
            r'cache.*=.*{}',  # Shared caches
            r'global.*execution.*engine',  # Global engine references
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in shared_state_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
                    for match in matches:
                        violations.append((str(py_file), match.strip()))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return violations
    
    def _scan_for_global_contamination(self) -> List[Tuple[str, str]]:
        """Scan for global variable contamination"""
        contamination = []
        
        # Patterns that indicate global contamination
        global_patterns = [
            r'global\s+.*execution.*engine',
            r'globals\(\).*UserExecutionEngine',
            r'setattr\(.*UserExecutionEngine',
            r'__dict__.*UserExecutionEngine',
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in global_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        contamination.append((str(py_file), match))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return contamination
    
    def _get_python_files(self) -> List[Path]:
        """Get Python files for analysis"""
        python_files = []
        
        # Focus on key directories
        search_paths = [
            self.project_root / 'netra_backend' / 'app' / 'agents',
            self.project_root / 'netra_backend' / 'app' / 'services',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                try:
                    python_files.extend(list(search_path.rglob('*.py')))
                except (OSError, PermissionError):
                    continue
                    
        return python_files


if __name__ == '__main__':
    print("🚨 Issue #1186 UserExecutionEngine SSOT Consolidation - Phase 1 Reproduction Tests")
    print("=" * 80)
    print("WARNING️  WARNING: These tests are DESIGNED TO FAIL to demonstrate current problems")
    print("📊 Expected: 7 test failures exposing import fragmentation and user isolation violations")
    print("🎯 Goal: Baseline measurement before SSOT consolidation implementation")
    print("=" * 80)
    
    unittest.main(verbosity=2)