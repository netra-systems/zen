"""
Import Fragmentation Detection Test for Issue #1186

Tests for detecting import fragmentation violations in UserExecutionEngine patterns
across the codebase. This test suite identifies the 275+ violations that need
to be addressed as part of SSOT consolidation.

Business Value: Platform/Internal - System Stability & Development Velocity
Prevents cascade failures from duplicated import patterns and ensures reliable
SSOT compliance for the $500K+ ARR Golden Path.

Expected: FAIL initially (detects 275+ violations)
Target: 100% SSOT compliance with zero import fragmentation violations

CRITICAL: This test MUST fail initially to demonstrate current violations.
Only passes when SSOT consolidation is complete.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class ImportViolation:
    """Container for import fragmentation violations."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str
    severity: str
    pattern_type: str
    

@dataclass
class FragmentationStats:
    """Statistics for import fragmentation analysis."""
    total_violations: int
    critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    patterns_detected: Set[str]
    files_affected: Set[str]
    duplicate_imports: Dict[str, int]


class TestUserExecutionEngineImportFragmentation(SSotBaseTestCase):
    """
    Test class to detect and validate UserExecutionEngine import fragmentation.
    
    This test suite exposes the current import chaos and validates SSOT consolidation.
    """
    
    def setup_method(self, method):
        """Setup test environment with SSOT base."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.canonical_import = "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
        self.violation_threshold = 5  # Target: <5 violations
        
    def test_detect_user_execution_engine_import_patterns(self):
        """
        TEST 1: Detect all UserExecutionEngine import patterns across codebase.
        
        EXPECTED TO FAIL: Should find 4+ different import patterns (current state).
        TARGET: Should find exactly 1 canonical pattern after consolidation.
        """
        print("\n🔍 TEST 1: Detecting UserExecutionEngine import patterns...")
        
        import_patterns = self._scan_all_import_patterns()
        unique_patterns = set(import_patterns.keys())
        
        # Track metrics for business analysis
        self.record_metric("import_patterns_found", len(unique_patterns))
        self.record_metric("total_import_usages", sum(len(files) for files in import_patterns.values()))
        
        # Log patterns for analysis
        print(f"\n📊 IMPORT PATTERN ANALYSIS:")
        for pattern, files in import_patterns.items():
            print(f"   Pattern: {pattern}")
            print(f"   Files: {len(files)}")
            print(f"   Examples: {files[:3]}")
            print()
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(unique_patterns) <= 1, (
            f"❌ EXPECTED FAILURE: Found {len(unique_patterns)} different UserExecutionEngine import patterns. "
            f"SSOT requires exactly 1 canonical pattern. Found patterns:\n" + 
            '\n'.join([f"  • '{pattern}' used in {len(files)} files" 
                      for pattern, files in import_patterns.items()]) +
            f"\n\n🎯 Target: Use canonical pattern: {self.canonical_import}"
        )
        
    def test_measure_import_fragmentation_violations(self):
        """
        TEST 2: Measure total import fragmentation violations.
        
        EXPECTED TO FAIL: Should find 275+ violations (audit baseline).
        TARGET: Should find <5 violations after consolidation.
        """
        print("\n🔍 TEST 2: Measuring import fragmentation violations...")
        
        fragmentation_result = self._analyze_import_fragmentation()
        
        # Track metrics for business analysis
        self.record_metric("fragmentation_violations", fragmentation_result.total_violations)
        self.record_metric("fragmentation_severity", fragmentation_result.severity)
        
        print(f"\n📊 FRAGMENTATION ANALYSIS:")
        print(f"   Total violations: {fragmentation_result.total_violations}")
        print(f"   Unique patterns: {len(fragmentation_result.unique_patterns)}")
        print(f"   Canonical pattern: {fragmentation_result.canonical_pattern}")
        print(f"   Severity: {fragmentation_result.severity}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert fragmentation_result.total_violations < self.violation_threshold, (
            f"❌ EXPECTED FAILURE: Found {fragmentation_result.total_violations} import fragmentation violations. "
            f"Target is <{self.violation_threshold} violations for SSOT compliance.\n"
            f"Severity: {fragmentation_result.severity}\n"
            f"Sample violations:\n" + 
            '\n'.join([f"  • {path}: {pattern}" 
                      for path, pattern in fragmentation_result.fragmented_imports[:5]]) +
            (f"\n  ... and {fragmentation_result.total_violations - 5} more" 
             if fragmentation_result.total_violations > 5 else "")
        )
        
    def test_validate_canonical_import_usage(self):
        """
        TEST 3: Validate canonical import pattern usage across codebase.
        
        EXPECTED TO FAIL: Most files should NOT use canonical pattern yet.
        TARGET: 95%+ files should use canonical pattern after consolidation.
        """
        print("\n🔍 TEST 3: Validating canonical import pattern usage...")
        
        canonical_usage = self._analyze_canonical_import_usage()
        total_files = canonical_usage['total_files_with_imports']
        canonical_files = canonical_usage['canonical_pattern_files']
        usage_percentage = (canonical_files / max(1, total_files)) * 100
        
        # Track metrics
        self.record_metric("canonical_usage_percentage", usage_percentage)
        self.record_metric("canonical_pattern_files", canonical_files)
        self.record_metric("total_import_files", total_files)
        
        print(f"\n📊 CANONICAL USAGE ANALYSIS:")
        print(f"   Files using canonical pattern: {canonical_files}")
        print(f"   Total files with imports: {total_files}")
        print(f"   Usage percentage: {usage_percentage:.1f}%")
        print(f"   Target: 95%+ canonical usage")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert usage_percentage >= 95.0, (
            f"❌ EXPECTED FAILURE: Only {usage_percentage:.1f}% of files use canonical import pattern. "
            f"SSOT requires 95%+ canonical usage.\n"
            f"Canonical pattern: {self.canonical_import}\n"
            f"Files using canonical: {canonical_files}/{total_files}\n"
            f"Non-canonical examples:\n" + 
            '\n'.join([f"  • {path}" for path in canonical_usage['non_canonical_files'][:5]])
        )
        
    def test_detect_cross_service_import_violations(self):
        """
        TEST 4: Detect cross-service import boundary violations.
        
        EXPECTED TO FAIL: Should find cross-service imports violating boundaries.
        TARGET: Zero cross-service imports after consolidation.
        """
        print("\n🔍 TEST 4: Detecting cross-service import violations...")
        
        boundary_violations = self._scan_cross_service_violations()
        
        # Track metrics
        self.record_metric("cross_service_violations", len(boundary_violations))
        
        print(f"\n📊 CROSS-SERVICE ANALYSIS:")
        print(f"   Cross-service violations: {len(boundary_violations)}")
        for service, violations in boundary_violations.items():
            print(f"   {service}: {len(violations)} violations")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(boundary_violations) == 0, (
            f"❌ EXPECTED FAILURE: Found {len(boundary_violations)} cross-service import violations. "
            f"Each service should have independent UserExecutionEngine access.\n"
            f"Violations by service:\n" + 
            '\n'.join([f"  • {service}: {len(violations)} violations" 
                      for service, violations in boundary_violations.items()]) +
            f"\n\nServices should use service-specific factory patterns, not direct imports."
        )
        
    def test_detect_legacy_import_patterns(self):
        """
        TEST 5: Detect legacy import patterns that should be eliminated.
        
        EXPECTED TO FAIL: Should find legacy patterns still in use.
        TARGET: Zero legacy patterns after consolidation.
        """
        print("\n🔍 TEST 5: Detecting legacy import patterns...")
        
        legacy_patterns = self._scan_legacy_import_patterns()
        
        # Track metrics
        self.record_metric("legacy_pattern_violations", len(legacy_patterns))
        
        print(f"\n📊 LEGACY PATTERN ANALYSIS:")
        print(f"   Legacy pattern violations: {len(legacy_patterns)}")
        for pattern_type, occurrences in legacy_patterns.items():
            print(f"   {pattern_type}: {len(occurrences)} occurrences")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(legacy_patterns) == 0, (
            f"❌ EXPECTED FAILURE: Found {sum(len(occs) for occs in legacy_patterns.values())} legacy import patterns. "
            f"All legacy patterns should be eliminated for SSOT compliance.\n"
            f"Legacy patterns found:\n" + 
            '\n'.join([f"  • {pattern}: {len(occurrences)} occurrences" 
                      for pattern, occurrences in legacy_patterns.items()]) +
            f"\n\nLegacy patterns must be migrated to SSOT canonical imports."
        )
    
    def _scan_all_import_patterns(self) -> Dict[str, List[str]]:
        """Scan codebase for all UserExecutionEngine import patterns."""
        import_patterns = defaultdict(list)
        
        # Search patterns for UserExecutionEngine imports
        search_patterns = [
            r'from\s+.*\.user_execution_engine\s+import\s+UserExecutionEngine',
            r'from\s+.*\.execution_engine\s+import\s+UserExecutionEngine',
            r'from\s+.*supervisor.*\s+import\s+.*UserExecutionEngine',
            r'import\s+.*UserExecutionEngine.*',
            r'from\s+.*agents.*\s+import\s+.*UserExecutionEngine',
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in search_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        normalized_match = ' '.join(match.split())  # Normalize whitespace
                        import_patterns[normalized_match].append(str(py_file))
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return dict(import_patterns)
    
    def _analyze_import_fragmentation(self) -> ImportFragmentationResult:
        """Analyze import fragmentation and return structured results."""
        import_patterns = self._scan_all_import_patterns()
        unique_patterns = set(import_patterns.keys())
        
        # Count total violations (non-canonical imports)
        total_violations = 0
        fragmented_imports = []
        
        for pattern, files in import_patterns.items():
            if pattern != self.canonical_import:
                total_violations += len(files)
                for file_path in files:
                    fragmented_imports.append((file_path, pattern))
        
        # Determine severity
        if total_violations > 200:
            severity = "CRITICAL"
        elif total_violations > 50:
            severity = "HIGH"
        elif total_violations > 10:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        return ImportFragmentationResult(
            total_violations=total_violations,
            fragmented_imports=fragmented_imports,
            unique_patterns=unique_patterns,
            canonical_pattern=self.canonical_import,
            severity=severity
        )
    
    def _analyze_canonical_import_usage(self) -> Dict[str, any]:
        """Analyze canonical import pattern usage."""
        import_patterns = self._scan_all_import_patterns()
        
        canonical_files = set()
        non_canonical_files = set()
        total_files = set()
        
        for pattern, files in import_patterns.items():
            total_files.update(files)
            if pattern == self.canonical_import:
                canonical_files.update(files)
            else:
                non_canonical_files.update(files)
        
        return {
            'canonical_pattern_files': len(canonical_files),
            'total_files_with_imports': len(total_files),
            'non_canonical_files': list(non_canonical_files),
            'canonical_files': list(canonical_files)
        }
    
    def _scan_cross_service_violations(self) -> Dict[str, List[str]]:
        """Scan for cross-service import boundary violations."""
        violations = defaultdict(list)
        services = ['netra_backend', 'auth_service', 'frontend']
        
        for service in services:
            service_path = self.project_root / service
            if not service_path.exists():
                continue
                
            for py_file in self._get_python_files_in_path(service_path):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for imports from other services
                    for other_service in services:
                        if other_service != service:
                            cross_import_pattern = f'from {other_service}.*UserExecutionEngine'
                            if re.search(cross_import_pattern, content):
                                violations[service].append(f"Cross-import from {other_service} in {py_file}")
                                
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
                    
        return dict(violations)
    
    def _scan_legacy_import_patterns(self) -> Dict[str, List[str]]:
        """Scan for legacy import patterns that should be eliminated."""
        legacy_patterns = {
            'execution_engine_imports': [],
            'alias_imports': [],
            'relative_imports': [],
            'wildcard_imports': []
        }
        
        patterns = {
            'execution_engine_imports': r'from.*execution_engine.*import.*UserExecutionEngine',
            'alias_imports': r'import.*UserExecutionEngine.*as.*',
            'relative_imports': r'from\s*\..*UserExecutionEngine',
            'wildcard_imports': r'from.*UserExecutionEngine.*import\s*\*'
        }
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern_type, pattern in patterns.items():
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        legacy_patterns[pattern_type].append(f"{py_file}: {match}")
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return legacy_patterns
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the project for analysis."""
        python_files = []
        
        # Focus on main source directories
        search_paths = [
            self.project_root / 'netra_backend' / 'app',
            self.project_root / 'tests',
            self.project_root / 'auth_service',
            self.project_root / 'shared',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                python_files.extend(self._get_python_files_in_path(search_path))
                
        return python_files
    
    def _get_python_files_in_path(self, path: Path) -> List[Path]:
        """Get Python files in a specific path."""
        try:
            return list(path.rglob('*.py'))
        except (OSError, PermissionError):
            return []


if __name__ == '__main__':
    print("🚨 Issue #1186 UserExecutionEngine Import Fragmentation Detection")
    print("=" * 80)
    print("⚠️  WARNING: These tests are DESIGNED TO FAIL to demonstrate current violations")
    print("📊 Expected: Multiple test failures exposing import fragmentation")
    print("🎯 Goal: Baseline measurement before SSOT consolidation")
    print("=" * 80)
    
    unittest.main(verbosity=2)