"""
Test Suite: WebSocket Authentication Pattern Violations Detection
Issue #1186: UserExecutionEngine SSOT Consolidation - WebSocket Auth Component

PURPOSE: Expose and validate WebSocket authentication pattern violations.
These tests are DESIGNED TO FAIL initially to demonstrate current violations.

Business Impact: 5 WebSocket authentication violations with 4 different validation
patterns prevent consistent authentication, blocking $500K+ ARR WebSocket reliability.

EXPECTED BEHAVIOR:
- All tests SHOULD FAIL initially (demonstrating violations)
- All tests SHOULD PASS after SSOT consolidation is complete
"""

import ast
import re
import sys
import pytest
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class WebSocketAuthViolation:
    """Container for WebSocket authentication violation data."""
    file_path: str
    pattern_type: str
    line_number: int
    code_snippet: str
    violation_severity: str


@dataclass
class AuthPatternAnalysis:
    """Container for authentication pattern analysis results."""
    total_violations: int
    patterns_found: Set[str]
    target_pattern: str
    violations_by_type: Dict[str, List[WebSocketAuthViolation]]
    severity: str


@pytest.mark.unit
@pytest.mark.ssot_consolidation
@pytest.mark.websocket_auth
class TestWebSocketAuthenticationPatternViolations(SSotBaseTestCase):
    """
    Test class to detect and validate WebSocket authentication pattern violations.
    
    This test suite exposes the current authentication chaos and validates SSOT consolidation.
    """
    
    def setup_method(self, method):
        """Setup test environment with SSOT base."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # Define SSOT authentication patterns (what SHOULD be used)
        self.ssot_auth_pattern = "from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot"
        self.ssot_authenticator_pattern = "from netra_backend.app.websocket_core.unified_websocket_auth import UnifiedWebSocketAuthenticator"
        
        # Define violation patterns (what should NOT be used)
        self.violation_patterns = {
            'legacy_auth_class': r'class\s+WebSocketAuthenticator\s*\(',
            'duplicate_auth_functions': r'def\s+authenticate_websocket_connection\s*\(',
            'token_validation_fragments': r'def\s+validate_websocket_token.*\(',
            'extraction_utility_duplicates': r'def\s+.*extract.*token.*websocket\s*\(',
        }
        
    def test_detect_websocket_auth_pattern_violations(self):
        """
        TEST 1: Detect all WebSocket authentication pattern violations.
        
        EXPECTED TO FAIL: Should find 5+ authentication violations (audit baseline).
        TARGET: Should find 0 violations after SSOT consolidation.
        """
        print("\n🔍 TEST 1: Detecting WebSocket authentication pattern violations...")
        
        auth_analysis = self._analyze_websocket_auth_patterns()
        
        # Track metrics for business analysis
        self.record_metric("websocket_auth_violations", auth_analysis.total_violations)
        self.record_metric("auth_patterns_found", len(auth_analysis.patterns_found))
        self.record_metric("auth_violation_severity", auth_analysis.severity)
        
        print(f"\n📊 WEBSOCKET AUTH PATTERN ANALYSIS:")
        print(f"   Total violations: {auth_analysis.total_violations}")
        print(f"   Unique patterns found: {len(auth_analysis.patterns_found)}")
        print(f"   Target pattern: {auth_analysis.target_pattern}")
        print(f"   Severity: {auth_analysis.severity}")
        
        # Print violations by type
        for pattern_type, violations in auth_analysis.violations_by_type.items():
            print(f"\n   {pattern_type}: {len(violations)} violations")
            for violation in violations[:3]:  # Show first 3
                print(f"     • {violation.file_path}:{violation.line_number}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert auth_analysis.total_violations == 0, (
            f"❌ EXPECTED FAILURE: Found {auth_analysis.total_violations} WebSocket authentication pattern violations. "
            f"SSOT requires exactly 1 canonical authentication pattern.\n"
            f"Severity: {auth_analysis.severity}\n"
            f"Violations by type:\n" + 
            '\n'.join([f"  • {pattern_type}: {len(violations)} violations" 
                      for pattern_type, violations in auth_analysis.violations_by_type.items()]) +
            f"\n\n🎯 Target: Use SSOT pattern: {auth_analysis.target_pattern}"
        )
    
    def test_detect_legacy_websocket_authenticator_classes(self):
        """
        TEST 2: Detect legacy WebSocketAuthenticator class implementations.
        
        EXPECTED TO FAIL: Should find multiple WebSocketAuthenticator classes.
        TARGET: Should find only UnifiedWebSocketAuthenticator after consolidation.
        """
        print("\n🔍 TEST 2: Detecting legacy WebSocketAuthenticator classes...")
        
        authenticator_classes = self._scan_websocket_authenticator_classes()
        legacy_classes = [cls for cls in authenticator_classes if cls['is_legacy']]
        
        # Track metrics
        self.record_metric("legacy_authenticator_classes", len(legacy_classes))
        self.record_metric("total_authenticator_classes", len(authenticator_classes))
        
        print(f"\n📊 WEBSOCKET AUTHENTICATOR CLASS ANALYSIS:")
        print(f"   Total authenticator classes: {len(authenticator_classes)}")
        print(f"   Legacy classes: {len(legacy_classes)}")
        print(f"   Target: 1 SSOT class (UnifiedWebSocketAuthenticator)")
        
        for cls in authenticator_classes:
            status = "❌ LEGACY" if cls['is_legacy'] else "✅ SSOT"
            print(f"   {status} {cls['class_name']} in {cls['file_path']}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(legacy_classes) == 0, (
            f"❌ EXPECTED FAILURE: Found {len(legacy_classes)} legacy WebSocketAuthenticator classes. "
            f"SSOT requires only UnifiedWebSocketAuthenticator.\n"
            f"Legacy classes found:\n" + 
            '\n'.join([f"  • {cls['class_name']} in {cls['file_path']}" 
                      for cls in legacy_classes]) +
            f"\n\n🎯 Target: Only UnifiedWebSocketAuthenticator should exist."
        )
    
    def test_detect_duplicate_auth_functions(self):
        """
        TEST 3: Detect duplicate authentication function implementations.
        
        EXPECTED TO FAIL: Should find 4+ different authentication functions.
        TARGET: Should find only authenticate_websocket_ssot after consolidation.
        """
        print("\n🔍 TEST 3: Detecting duplicate authentication functions...")
        
        auth_functions = self._scan_authentication_functions()
        duplicate_functions = [func for func in auth_functions if func['is_duplicate']]
        
        # Track metrics
        self.record_metric("duplicate_auth_functions", len(duplicate_functions))
        self.record_metric("total_auth_functions", len(auth_functions))
        
        print(f"\n📊 AUTHENTICATION FUNCTION ANALYSIS:")
        print(f"   Total auth functions: {len(auth_functions)}")
        print(f"   Duplicate functions: {len(duplicate_functions)}")
        print(f"   Target: 1 SSOT function (authenticate_websocket_ssot)")
        
        for func in auth_functions:
            status = "❌ DUPLICATE" if func['is_duplicate'] else "✅ SSOT"
            print(f"   {status} {func['function_name']} in {func['file_path']}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(duplicate_functions) == 0, (
            f"❌ EXPECTED FAILURE: Found {len(duplicate_functions)} duplicate authentication functions. "
            f"SSOT requires only authenticate_websocket_ssot.\n"
            f"Duplicate functions found:\n" + 
            '\n'.join([f"  • {func['function_name']} in {func['file_path']}" 
                      for func in duplicate_functions]) +
            f"\n\n🎯 Target: Only authenticate_websocket_ssot should exist."
        )
    
    def test_detect_token_validation_pattern_violations(self):
        """
        TEST 4: Detect token validation pattern violations.
        
        EXPECTED TO FAIL: Should find multiple token validation patterns.
        TARGET: Should find validation integrated into SSOT auth flow only.
        """
        print("\n🔍 TEST 4: Detecting token validation pattern violations...")
        
        validation_patterns = self._scan_token_validation_patterns()
        
        # Track metrics
        self.record_metric("token_validation_violations", len(validation_patterns))
        
        print(f"\n📊 TOKEN VALIDATION PATTERN ANALYSIS:")
        print(f"   Token validation violations: {len(validation_patterns)}")
        
        for pattern_type, violations in validation_patterns.items():
            print(f"   {pattern_type}: {len(violations)} violations")
            for violation in violations[:2]:  # Show first 2
                print(f"     • {violation}")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert len(validation_patterns) == 0, (
            f"❌ EXPECTED FAILURE: Found {sum(len(v) for v in validation_patterns.values())} token validation pattern violations. "
            f"Token validation should be integrated into SSOT authentication flow.\n"
            f"Violations by pattern:\n" + 
            '\n'.join([f"  • {pattern}: {len(violations)} violations" 
                      for pattern, violations in validation_patterns.items()]) +
            f"\n\n🎯 Target: Token validation integrated into authenticate_websocket_ssot only."
        )
    
    def test_validate_ssot_auth_usage_percentage(self):
        """
        TEST 5: Validate percentage of code using SSOT authentication patterns.
        
        EXPECTED TO FAIL: Most code should NOT use SSOT patterns yet.
        TARGET: 95%+ of authentication code should use SSOT patterns.
        """
        print("\n🔍 TEST 5: Validating SSOT authentication pattern usage...")
        
        ssot_usage = self._analyze_ssot_auth_usage()
        
        # Track metrics
        self.record_metric("ssot_auth_usage_percentage", ssot_usage['percentage'])
        self.record_metric("ssot_auth_files", ssot_usage['ssot_files'])
        self.record_metric("total_auth_files", ssot_usage['total_files'])
        
        print(f"\n📊 SSOT AUTHENTICATION USAGE ANALYSIS:")
        print(f"   Files using SSOT auth: {ssot_usage['ssot_files']}")
        print(f"   Total auth files: {ssot_usage['total_files']}")
        print(f"   SSOT usage percentage: {ssot_usage['percentage']:.1f}%")
        print(f"   Target: 95%+ SSOT usage")
        
        # ASSERTION DESIGNED TO FAIL INITIALLY
        assert ssot_usage['percentage'] >= 95.0, (
            f"❌ EXPECTED FAILURE: Only {ssot_usage['percentage']:.1f}% of authentication code uses SSOT patterns. "
            f"SSOT requires 95%+ canonical usage.\n"
            f"SSOT files: {ssot_usage['ssot_files']}/{ssot_usage['total_files']}\n"
            f"Non-SSOT examples:\n" + 
            '\n'.join([f"  • {path}" for path in ssot_usage['non_ssot_files'][:5]]) +
            f"\n\n🎯 Target: Use authenticate_websocket_ssot for all authentication."
        )
    
    def _analyze_websocket_auth_patterns(self) -> AuthPatternAnalysis:
        """Analyze WebSocket authentication patterns and violations."""
        violations_by_type = defaultdict(list)
        patterns_found = set()
        total_violations = 0
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern_type, pattern in self.violation_patterns.items():
                        if re.search(pattern, line):
                            violation = WebSocketAuthViolation(
                                file_path=str(py_file),
                                pattern_type=pattern_type,
                                line_number=line_num,
                                code_snippet=line.strip(),
                                violation_severity="HIGH"
                            )
                            violations_by_type[pattern_type].append(violation)
                            patterns_found.add(pattern_type)
                            total_violations += 1
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        # Determine severity
        if total_violations > 10:
            severity = "CRITICAL"
        elif total_violations > 5:
            severity = "HIGH"
        elif total_violations > 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        return AuthPatternAnalysis(
            total_violations=total_violations,
            patterns_found=patterns_found,
            target_pattern=self.ssot_auth_pattern,
            violations_by_type=dict(violations_by_type),
            severity=severity
        )
    
    def _scan_websocket_authenticator_classes(self) -> List[Dict[str, any]]:
        """Scan for WebSocketAuthenticator class implementations."""
        authenticator_classes = []
        
        class_patterns = [
            r'class\s+WebSocketAuthenticator\s*\(',
            r'class\s+UnifiedWebSocketAuthenticator\s*\(',
            r'class\s+.*WebSocket.*Auth.*\s*\(',
        ]
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in class_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        class_name = match.group().split()[1].split('(')[0]
                        is_legacy = class_name != "UnifiedWebSocketAuthenticator"
                        
                        authenticator_classes.append({
                            'class_name': class_name,
                            'file_path': str(py_file),
                            'is_legacy': is_legacy,
                            'pattern_matched': pattern
                        })
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return authenticator_classes
    
    def _scan_authentication_functions(self) -> List[Dict[str, any]]:
        """Scan for authentication function implementations."""
        auth_functions = []
        
        function_patterns = [
            r'def\s+authenticate_websocket_connection\s*\(',
            r'def\s+authenticate_websocket_ssot\s*\(',
            r'def\s+authenticate_websocket.*\s*\(',
            r'async\s+def\s+authenticate_websocket.*\s*\(',
        ]
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in function_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        func_name = match.group().split('def ')[-1].split('(')[0].strip()
                        is_duplicate = func_name != "authenticate_websocket_ssot"
                        
                        auth_functions.append({
                            'function_name': func_name,
                            'file_path': str(py_file),
                            'is_duplicate': is_duplicate,
                            'is_async': 'async' in match.group()
                        })
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return auth_functions
    
    def _scan_token_validation_patterns(self) -> Dict[str, List[str]]:
        """Scan for token validation pattern violations."""
        validation_patterns = {
            'standalone_validation_functions': [],
            'jwt_decode_duplicates': [],
            'token_extraction_utilities': [],
            'validation_method_duplicates': []
        }
        
        patterns = {
            'standalone_validation_functions': r'def\s+validate.*token.*\(',
            'jwt_decode_duplicates': r'jwt\.decode\(',
            'token_extraction_utilities': r'def\s+.*extract.*token.*\(',
            'validation_method_duplicates': r'def\s+.*validate.*jwt.*\(',
        }
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern_type, pattern in patterns.items():
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        validation_patterns[pattern_type].append(f"{py_file}: {match}")
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return validation_patterns
    
    def _analyze_ssot_auth_usage(self) -> Dict[str, any]:
        """Analyze SSOT authentication pattern usage."""
        ssot_files = set()
        non_ssot_files = set()
        total_files = set()
        
        ssot_patterns = [
            'authenticate_websocket_ssot',
            'UnifiedWebSocketAuthenticator',
            'from netra_backend.app.websocket_core.unified_websocket_auth'
        ]
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check if file contains authentication code
                if any(auth_keyword in content for auth_keyword in ['websocket', 'auth', 'token']):
                    total_files.add(str(py_file))
                    
                    # Check if file uses SSOT patterns
                    if any(ssot_pattern in content for ssot_pattern in ssot_patterns):
                        ssot_files.add(str(py_file))
                    else:
                        non_ssot_files.add(str(py_file))
                        
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        percentage = (len(ssot_files) / max(1, len(total_files))) * 100
        
        return {
            'ssot_files': len(ssot_files),
            'total_files': len(total_files),
            'percentage': percentage,
            'non_ssot_files': list(non_ssot_files)
        }
    
    def _get_websocket_related_files(self) -> List[Path]:
        """Get all WebSocket-related Python files for analysis."""
        websocket_files = []
        
        # Search paths that likely contain WebSocket authentication code
        search_paths = [
            self.project_root / 'netra_backend' / 'app' / 'websocket_core',
            self.project_root / 'netra_backend' / 'app' / 'routes',
            self.project_root / 'netra_backend' / 'app' / 'services',
            self.project_root / 'auth_service',
            self.project_root / 'tests' / 'websocket',
            self.project_root / 'tests' / 'integration',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    # Include files that likely contain WebSocket or auth code
                    if any(keyword in str(py_file).lower() for keyword in 
                           ['websocket', 'auth', 'token', 'jwt', 'connection']):
                        websocket_files.append(py_file)
        
        return websocket_files


if __name__ == '__main__':
    print("🚨 Issue #1186 WebSocket Authentication Pattern Violations Detection")
    print("=" * 80)
    print("⚠️  WARNING: These tests are DESIGNED TO FAIL to demonstrate current violations")
    print("📊 Expected: Multiple test failures exposing auth pattern violations")
    print("🎯 Goal: Baseline measurement before SSOT consolidation")
    print("=" * 80)
    
    unittest.main(verbosity=2)