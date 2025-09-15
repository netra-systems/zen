"""
Unit Tests: Auth SSOT Compliance Validation

Business Value Justification (BVJ):
- Segment: Platform/Testing Infrastructure  
- Business Goal: Prevent auth SSOT violations in development
- Value Impact: Early detection of JWT violations prevents security issues
- Strategic Impact: Enables enterprise-grade auth compliance ($500K+ ARR protection)

This test suite validates that the codebase follows auth SSOT patterns by:
1. Detecting direct JWT operations that should delegate to auth service
2. Ensuring test infrastructure uses SSOT auth helpers
3. Validating removal of legacy auth patterns
4. Preventing regression of competing auth implementations

CRITICAL: These tests should FAIL initially (reproducing violations),
then PASS after auth SSOT remediation is complete.
"""

import os
import ast
import glob
import pytest
from pathlib import Path
from typing import List, Dict, Set, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase


class AuthSSOTViolationDetector:
    """Utility class to detect auth SSOT violations in Python files."""
    
    # Patterns that indicate SSOT violations
    VIOLATION_PATTERNS = {
        'jwt_import': ['import jwt', 'from jwt import'],
        'jwt_encode': ['jwt.encode(', 'jwt.encode '],
        'jwt_decode': ['jwt.decode(', 'jwt.decode '],
        'legacy_auth': ['validate_token_legacy', 'auth_fallback', 'token_validate_local'],
        'direct_validation': ['def validate_token(', 'def verify_token(', 'def validate_jwt('],
    }
    
    @classmethod
    def scan_file_for_violations(cls, file_path: str) -> Dict[str, List[int]]:
        """Scan a Python file for auth SSOT violations.
        
        Returns:
            Dict mapping violation types to line numbers where found
        """
        violations = {key: [] for key in cls.VIOLATION_PATTERNS.keys()}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_content = line.strip().lower()
                
                # Check for each violation pattern
                for violation_type, patterns in cls.VIOLATION_PATTERNS.items():
                    for pattern in patterns:
                        if pattern.lower() in line_content:
                            violations[violation_type].append(line_num)
                            
        except (UnicodeDecodeError, IOError):
            # Skip files that can't be read
            pass
            
        return violations
    
    @classmethod
    def get_test_files(cls, base_path: str) -> List[str]:
        """Get all Python test files to scan."""
        test_patterns = [
            f"{base_path}/**/test_*.py",
            f"{base_path}/**/*_test.py",
        ]
        
        test_files = []
        for pattern in test_patterns:
            test_files.extend(glob.glob(pattern, recursive=True))
            
        return [f for f in test_files if os.path.isfile(f)]
    
    @classmethod
    def get_production_files(cls, base_path: str) -> List[str]:
        """Get production Python files (non-test) to scan."""
        all_patterns = [
            f"{base_path}/**/*.py"
        ]
        
        all_files = []
        for pattern in all_patterns:
            all_files.extend(glob.glob(pattern, recursive=True))
            
        # Filter out test files and __pycache__
        production_files = []
        for f in all_files:
            if (os.path.isfile(f) and 
                not '/test' in f and 
                not 'test_' in os.path.basename(f) and
                not '_test.py' in f and
                not '__pycache__' in f):
                production_files.append(f)
                
        return production_files


class AuthSSOTComplianceValidationTests(SSotBaseTestCase):
    """
    Test suite for validating auth SSOT compliance across the codebase.
    
    These tests should FAIL initially (reproducing the 381 violations found),
    then PASS after auth SSOT remediation is complete.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set up paths for scanning
        self.repo_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_path = self.repo_root / "netra_backend"
        self.test_framework_path = self.repo_root / "test_framework"
        self.tests_path = self.repo_root / "tests"
        
        self.detector = AuthSSOTViolationDetector()
    
    @pytest.mark.unit
    def test_no_direct_jwt_imports_in_tests(self):
        """
        Test that test files don't import JWT library directly.
        
        EXPECTED: FAIL initially (44 JWT_IMPORT violations found)
        Should PASS after implementing SSOT auth test helpers.
        """
        test_files = self.detector.get_test_files(str(self.tests_path))
        test_files.extend(self.detector.get_test_files(str(self.netra_backend_path / "tests")))
        
        violations = []
        for test_file in test_files:
            file_violations = self.detector.scan_file_for_violations(test_file)
            if file_violations['jwt_import']:
                violations.append({
                    'file': test_file,
                    'lines': file_violations['jwt_import'],
                    'violation_type': 'Direct JWT import in test file'
                })
        
        # This should FAIL initially with 44+ violations
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} test files with direct JWT imports. "
                f"Tests should use SSOT auth helpers instead:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit
    def test_no_jwt_encode_operations_in_tests(self):
        """
        Test that test files don't perform JWT encoding directly.
        
        EXPECTED: FAIL initially (124 JWT_ENCODE violations found)
        Should PASS after using auth service /token endpoint.
        """
        test_files = self.detector.get_test_files(str(self.tests_path))
        test_files.extend(self.detector.get_test_files(str(self.netra_backend_path / "tests")))
        
        violations = []
        for test_file in test_files:
            file_violations = self.detector.scan_file_for_violations(test_file)
            if file_violations['jwt_encode']:
                violations.append({
                    'file': test_file,
                    'lines': file_violations['jwt_encode'],
                    'violation_type': 'Direct JWT encoding in test file'
                })
        
        # This should FAIL initially with 124+ violations  
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} test files with JWT encoding operations. "
                f"Tests should use auth service /token endpoint instead:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit  
    def test_no_jwt_decode_operations_in_tests(self):
        """
        Test that test files don't perform JWT decoding directly.
        
        EXPECTED: FAIL initially (90 JWT_DECODE violations found)
        Should PASS after using auth service /validate endpoint.
        """
        test_files = self.detector.get_test_files(str(self.tests_path))
        test_files.extend(self.detector.get_test_files(str(self.netra_backend_path / "tests")))
        
        violations = []
        for test_file in test_files:
            file_violations = self.detector.scan_file_for_violations(test_file)
            if file_violations['jwt_decode']:
                violations.append({
                    'file': test_file,
                    'lines': file_violations['jwt_decode'],
                    'violation_type': 'Direct JWT decoding in test file'
                })
        
        # This should FAIL initially with 90+ violations
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} test files with JWT decoding operations. "
                f"Tests should use auth service /validate endpoint instead:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit
    def test_backend_has_no_direct_jwt_operations(self):
        """
        Test that backend production code has no direct JWT operations.
        
        EXPECTED: FAIL initially (production code has JWT operations)
        Should PASS after delegating to auth service.
        """
        backend_files = self.detector.get_production_files(str(self.netra_backend_path))
        
        violations = []
        for backend_file in backend_files:
            file_violations = self.detector.scan_file_for_violations(backend_file)
            
            # Check for any JWT operations
            for violation_type in ['jwt_import', 'jwt_encode', 'jwt_decode']:
                if file_violations[violation_type]:
                    violations.append({
                        'file': backend_file,
                        'lines': file_violations[violation_type],
                        'violation_type': f'Backend {violation_type.upper()} violation'
                    })
        
        # This should FAIL initially with backend JWT violations
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} backend files with direct JWT operations. "
                f"Backend should delegate all auth operations to auth service:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit
    def test_legacy_auth_patterns_removed(self):
        """
        Test that legacy authentication patterns have been removed.
        
        EXPECTED: FAIL initially (35 LEGACY_AUTH_CHECK violations found)
        Should PASS after removing legacy auth code.
        """
        all_files = []
        all_files.extend(self.detector.get_test_files(str(self.tests_path)))
        all_files.extend(self.detector.get_test_files(str(self.netra_backend_path / "tests")))
        all_files.extend(self.detector.get_production_files(str(self.netra_backend_path)))
        
        violations = []
        for file_path in all_files:
            file_violations = self.detector.scan_file_for_violations(file_path)
            if file_violations['legacy_auth']:
                violations.append({
                    'file': file_path,
                    'lines': file_violations['legacy_auth'],
                    'violation_type': 'Legacy auth pattern'
                })
        
        # This should FAIL initially with 35+ violations
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} files with legacy auth patterns. "
                f"Legacy auth code should be removed:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit
    def test_no_local_token_validation_methods(self):
        """
        Test that local token validation methods have been removed.
        
        EXPECTED: FAIL initially (7 VALIDATE_TOKEN_METHOD + 4 VERIFY_TOKEN_METHOD violations)
        Should PASS after using auth service client.
        """
        backend_files = self.detector.get_production_files(str(self.netra_backend_path))
        
        violations = []
        for backend_file in backend_files:
            file_violations = self.detector.scan_file_for_violations(backend_file)
            if file_violations['direct_validation']:
                violations.append({
                    'file': backend_file,
                    'lines': file_violations['direct_validation'],
                    'violation_type': 'Local token validation method'
                })
        
        # This should FAIL initially with 11+ violations (7 + 4)
        # After remediation, should PASS with 0 violations
        if violations:
            violation_details = []
            for v in violations[:10]:  # Show first 10 for brevity
                violation_details.append(f"  {v['file']}:{v['lines']} - {v['violation_type']}")
            
            pytest.fail(
                f"Found {len(violations)} files with local token validation methods. "
                f"Should use auth service client instead:\n" + 
                "\n".join(violation_details) +
                (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            )
    
    @pytest.mark.unit
    def test_auth_integration_layer_is_pure_delegation(self):
        """
        Test that auth integration layer only contains delegation code.
        
        The auth integration layer should ONLY call auth service client,
        not perform any auth logic itself.
        """
        auth_integration_file = self.netra_backend_path / "app" / "auth_integration" / "auth.py"
        
        if not auth_integration_file.exists():
            pytest.skip("Auth integration file not found")
        
        violations = self.detector.scan_file_for_violations(str(auth_integration_file))
        
        # Check for any JWT operations in auth integration
        jwt_violations = []
        for violation_type in ['jwt_import', 'jwt_encode', 'jwt_decode', 'direct_validation']:
            if violations[violation_type]:
                jwt_violations.extend([
                    f"Line {line}: {violation_type.upper()} violation" 
                    for line in violations[violation_type]
                ])
        
        if jwt_violations:
            pytest.fail(
                f"Auth integration layer contains auth logic violations. "
                f"Should only delegate to auth service:\n" + 
                "\n".join(f"  {v}" for v in jwt_violations)
            )
    
    @pytest.mark.unit
    def test_ssot_auth_test_helpers_exist(self):
        """
        Test that SSOT auth test helpers exist and can be imported.
        
        EXPECTED: FAIL initially (SSOT auth helpers don't exist)
        Should PASS after creating SSOT auth test infrastructure.
        """
        try:
            # Try to import SSOT auth test helpers
            from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
            
            # Verify the helper has required methods
            required_methods = [
                'create_test_user_with_token',
                'validate_token_via_service', 
                'create_websocket_auth_token'
            ]
            
            for method in required_methods:
                if not hasattr(SSOTAuthTestHelper, method):
                    pytest.fail(f"SSOTAuthTestHelper missing required method: {method}")
                    
        except ImportError as e:
            pytest.fail(
                f"SSOT auth test helpers not found. "
                f"Create test_framework/ssot/auth_test_helpers.py with SSOTAuthTestHelper class. "
                f"Import error: {e}"
            )
    
    @pytest.mark.unit
    def test_compliance_script_detects_remaining_violations(self):
        """
        Test that auth SSOT compliance script correctly detects violations.
        
        This validates that the compliance script is working correctly
        and can be used for ongoing monitoring.
        """
        import subprocess
        import sys
        
        try:
            # Run the compliance script
            result = subprocess.run([
                sys.executable, 
                str(self.repo_root / "scripts" / "check_auth_ssot_compliance.py")
            ], capture_output=True, text=True, cwd=str(self.repo_root))
            
            # The script should detect violations initially
            # After remediation, it should report 0 violations
            if result.returncode == 0:
                # This means no violations found - should only happen after remediation
                self.logger.info("Auth SSOT compliance check passed - no violations found")
            else:
                # This means violations found - expected initially
                violation_count = 0
                if "violations found:" in result.stderr.lower():
                    try:
                        # Extract violation count from output
                        lines = result.stderr.split('\n')
                        for line in lines:
                            if "violations found:" in line.lower():
                                violation_count = int(line.split(':')[1].strip())
                                break
                    except (ValueError, IndexError):
                        pass
                
                if violation_count > 0:
                    pytest.fail(
                        f"Auth SSOT compliance script detected {violation_count} violations. "
                        f"Expected during initial testing, should be 0 after remediation."
                    )
                else:
                    pytest.fail(
                        f"Auth SSOT compliance script failed but couldn't extract violation count. "
                        f"Script output: {result.stderr[:500]}"
                    )
                    
        except FileNotFoundError:
            pytest.fail("Auth SSOT compliance script not found at scripts/check_auth_ssot_compliance.py")
        except Exception as e:
            pytest.fail(f"Error running auth SSOT compliance script: {e}")


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])