#!/usr/bin/env python3
"""
Auth SSOT Compliance Check Script

This script detects violations of the auth service Single Source of Truth (SSOT) pattern
to prevent regression of JWT operations being added back to the backend service.

CRITICAL CONTEXT:
- We removed JWT decoding from backend to enforce auth service SSOT
- This prevents the "error behind the error" JWT secret mismatches
- Automated checks prevent developers from reintroducing JWT violations

Business Value:
- Prevents $50K MRR loss from auth regressions
- Ensures secure multi-user isolation
- Maintains clean service boundaries
- Automated enforcement prevents human error

Usage:
    python scripts/check_auth_ssot_compliance.py [--fix-mode] [--exclude-tests]
    
Exit codes:
    0 = All checks pass
    1 = SSOT violations found
    2 = Script error
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Violation:
    """Represents an SSOT compliance violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    description: str
    suggestion: str
    severity: str = "ERROR"


@dataclass
class ComplianceResult:
    """Results of compliance checking."""
    total_files_checked: int
    violations: List[Violation]
    warnings: List[Violation]
    allowed_exceptions: List[Tuple[str, str]]  # (file_path, reason)
    
    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class AuthSSOTComplianceChecker:
    """
    Automated compliance checker for auth service SSOT enforcement.
    
    This checker detects attempts to reintroduce JWT operations into the backend
    service, which would violate our architectural SSOT patterns and could cause
    the same JWT secret mismatch issues we previously fixed.
    """
    
    # Patterns that indicate JWT operations (forbidden in backend)
    JWT_PATTERNS = {
        "jwt_import": {
            "pattern": r"^import\s+jwt(?:\s|$)",
            "description": "Direct JWT library import",
            "suggestion": "Use auth service client instead of direct JWT operations"
        },
        "jwt_from_import": {
            "pattern": r"^from\s+jwt\s+import",
            "description": "JWT library component import", 
            "suggestion": "Use auth service client instead of direct JWT operations"
        },
        "jwt_decode": {
            "pattern": r"jwt\.decode\s*\(",
            "description": "JWT token decoding",
            "suggestion": "Use auth service /validate endpoint instead"
        },
        "jwt_encode": {
            "pattern": r"jwt\.encode\s*\(",
            "description": "JWT token encoding",
            "suggestion": "Use auth service /token endpoint instead"
        },
    }
    
    # Local validation patterns (should use auth service)
    LOCAL_AUTH_PATTERNS = {
        "decode_token_method": {
            "pattern": r"def\s+decode_token\s*\(",
            "description": "Local token decoding method",
            "suggestion": "Remove local validation, use auth service client"
        },
        "validate_jwt_method": {
            "pattern": r"def\s+validate_jwt\s*\(",
            "description": "Local JWT validation method", 
            "suggestion": "Remove local validation, use auth service client"
        },
        "validate_token_method": {
            "pattern": r"def\s+validate_token\s*\(",
            "description": "Local token validation method",
            "suggestion": "Remove local validation, use auth service client"
        },
        "verify_token_method": {
            "pattern": r"def\s+verify_token\s*\(",
            "description": "Local token verification method",
            "suggestion": "Remove local validation, use auth service client"
        },
    }
    
    # Fallback patterns that bypass auth service
    FALLBACK_PATTERNS = {
        "fallback_validation": {
            "pattern": r"fallback.*validation|validation.*fallback",
            "description": "Authentication fallback mechanism",
            "suggestion": "Remove fallbacks, use auth service with proper error handling"
        },
        "legacy_auth_check": {
            "pattern": r"legacy.*auth|auth.*legacy",
            "description": "Legacy authentication logic",
            "suggestion": "Remove legacy code, use auth service SSOT"
        },
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize compliance checker."""
        self.project_root = project_root or Path.cwd()
        self.backend_root = self.project_root / "netra_backend"
        self.shared_root = self.project_root / "shared"
        self.auth_service_root = self.project_root / "auth_service"
        
        # Files that are allowed to have JWT operations
        self.allowed_jwt_files = {
            # Auth service (SSOT for JWT operations)
            "auth_service/auth_core/core/jwt_handler.py",
            "auth_service/auth_core/core/jwt_cache.py", 
            "auth_service/auth_core/core/token_validator.py",
            
            # Shared JWT secret management (infrastructure only)
            "shared/jwt_secret_manager.py",
            
            # WebSocket context extractor (uses unified JWT secret manager SSOT)
            "netra_backend/app/websocket_core/user_context_extractor.py",
            
            # Test frameworks (for testing JWT flows)
            "test_framework/jwt_test_utils.py",
            "test_framework/fixtures/auth.py",
            
            # E2E test helpers (for creating test tokens)
            "test_framework/ssot/e2e_auth_helper.py",
            "tests/e2e/jwt_token_helpers.py",
            
            # Integration test helpers (testing only)
            "netra_backend/tests/integration/jwt_token_helpers.py",
        }
        
        # Exception markers that justify JWT usage
        self.exception_markers = [
            "@auth_ssot_exception:",
            "@jwt_allowed:",
            "# SSOT_EXCEPTION:",
            "# JWT_ALLOWED:",
        ]
    
    def is_file_allowed(self, file_path: str) -> bool:
        """Check if file is allowed to have JWT operations."""
        # Convert to relative path from project root
        try:
            rel_path = Path(file_path).relative_to(self.project_root)
            return str(rel_path).replace("\\", "/") in self.allowed_jwt_files
        except ValueError:
            return False
    
    def has_exception_marker(self, lines: List[str], line_idx: int) -> Optional[str]:
        """Check if violation has a valid exception marker."""
        # Check current line and 2 lines above for exception markers
        start_idx = max(0, line_idx - 2)
        check_lines = lines[start_idx:line_idx + 1]
        
        for line in check_lines:
            for marker in self.exception_markers:
                if marker in line:
                    # Extract justification after marker
                    parts = line.split(marker, 1)
                    if len(parts) > 1:
                        return parts[1].strip()
                    return "Exception marker found"
        return None
    
    def check_file_content(self, file_path: Path, content: str, exclude_tests: bool = False) -> List[Violation]:
        """Check file content for SSOT violations."""
        violations = []
        lines = content.splitlines()
        file_str = str(file_path)
        
        # Skip test files if requested
        if exclude_tests and ("/test" in file_str or "/tests/" in file_str):
            return violations
        
        # Check if file is in allowed list
        if self.is_file_allowed(file_str):
            return violations
        
        # Only check backend files for most violations
        is_backend = "netra_backend" in file_str
        is_shared = "shared" in file_str and "jwt_secret_manager.py" not in file_str
        
        if not is_backend and not is_shared:
            return violations
        
        # Check each line for violations
        for line_idx, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith("#"):
                continue
            
            # Check for exception markers first
            exception_reason = self.has_exception_marker(lines, line_idx)
            
            # CRITICAL: Focus on the most dangerous patterns
            # 1. Direct JWT operations (encoding/decoding) - HIGHEST RISK
            dangerous_patterns = {}
            if is_backend:
                dangerous_patterns = {
                    **self.JWT_PATTERNS,
                    **self.LOCAL_AUTH_PATTERNS
                }
                # Only check fallback patterns if they don't use unified JWT secret
                if not ("get_unified_jwt_secret" in content or "shared.jwt_secret_manager" in content):
                    dangerous_patterns.update(self.FALLBACK_PATTERNS)
            else:
                dangerous_patterns = self.JWT_PATTERNS
            
            for pattern_name, pattern_info in dangerous_patterns.items():
                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                    if exception_reason:
                        # This violation has a valid exception - skip it
                        continue
                        
                    violations.append(Violation(
                        file_path=file_str,
                        line_number=line_idx + 1,
                        line_content=line.rstrip(),
                        violation_type=pattern_name,
                        description=pattern_info["description"],
                        suggestion=pattern_info["suggestion"],
                        severity="ERROR"
                    ))
        
        return violations
    
    def scan_directory(self, directory: Path, exclude_tests: bool = False) -> List[Violation]:
        """Scan directory for Python files and check compliance."""
        violations = []
        
        if not directory.exists():
            return violations
        
        # Get all Python files
        python_files = list(directory.rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_violations = self.check_file_content(file_path, content, exclude_tests)
                    violations.extend(file_violations)
            except Exception as e:
                # Add violation for files we can't read
                violations.append(Violation(
                    file_path=str(file_path),
                    line_number=0,
                    line_content="",
                    violation_type="file_read_error",
                    description=f"Could not read file: {e}",
                    suggestion="Check file permissions and encoding",
                    severity="WARNING"
                ))
        
        return violations
    
    def check_websocket_specific_issues(self) -> List[Violation]:
        """Check for specific WebSocket JWT handling issues."""
        violations = []
        websocket_files = [
            self.backend_root / "app" / "routes" / "websocket.py",
            self.backend_root / "app" / "websocket_core" / "user_context_extractor.py",
            self.backend_root / "app" / "websocket" / "token_refresh_handler.py",
        ]
        
        for websocket_file in websocket_files:
            if not websocket_file.exists():
                continue
                
            try:
                with open(websocket_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                # Check for specific WebSocket JWT issues
                for line_idx, line in enumerate(lines):
                    # Look for local JWT validation in WebSocket code
                    if re.search(r"jwt\.decode.*websocket", line, re.IGNORECASE):
                        violations.append(Violation(
                            file_path=str(websocket_file),
                            line_number=line_idx + 1,
                            line_content=line.rstrip(),
                            violation_type="websocket_jwt_decode",
                            description="WebSocket performing local JWT decode",
                            suggestion="Use auth service validation through client",
                            severity="ERROR"
                        ))
                    
                    # Look for fallback validation that bypasses auth service
                    if re.search(r"fallback.*jwt|legacy.*jwt", line, re.IGNORECASE):
                        violations.append(Violation(
                            file_path=str(websocket_file),
                            line_number=line_idx + 1,
                            line_content=line.rstrip(),
                            violation_type="websocket_fallback_auth",
                            description="WebSocket using fallback JWT validation",
                            suggestion="Remove fallback, use auth service with proper error handling",
                            severity="ERROR"
                        ))
                        
            except Exception:
                continue
        
        return violations
    
    def run_compliance_check(self, exclude_tests: bool = False) -> ComplianceResult:
        """Run complete compliance check."""
        all_violations = []
        all_warnings = []
        allowed_exceptions = []
        
        # Check backend directory
        print("Scanning netra_backend for SSOT violations...")
        backend_violations = self.scan_directory(self.backend_root, exclude_tests)
        
        # Check shared directory (limited patterns)
        print("Scanning shared for JWT violations...")
        shared_violations = self.scan_directory(self.shared_root, exclude_tests)
        
        # Check WebSocket-specific issues
        print("Checking WebSocket-specific compliance...")
        websocket_violations = self.check_websocket_specific_issues()
        
        # Combine all violations
        all_violations.extend(backend_violations)
        all_violations.extend(shared_violations)
        all_violations.extend(websocket_violations)
        
        # Separate violations from warnings
        violations = [v for v in all_violations if v.severity == "ERROR"]
        warnings = [v for v in all_violations if v.severity == "WARNING"]
        
        # Count files checked
        backend_files = len(list(self.backend_root.rglob("*.py"))) if self.backend_root.exists() else 0
        shared_files = len(list(self.shared_root.rglob("*.py"))) if self.shared_root.exists() else 0
        total_files = backend_files + shared_files
        
        return ComplianceResult(
            total_files_checked=total_files,
            violations=violations,
            warnings=warnings,
            allowed_exceptions=allowed_exceptions
        )
    
    def print_results(self, result: ComplianceResult, verbose: bool = True):
        """Print compliance check results."""
        print("\n" + "="*80)
        print("AUTH SSOT COMPLIANCE CHECK RESULTS")
        print("="*80)
        
        print(f"\nFiles Checked: {result.total_files_checked}")
        print(f"Violations Found: {len(result.violations)}")
        print(f"Warnings: {len(result.warnings)}")
        print(f"Allowed Exceptions: {len(result.allowed_exceptions)}")
        
        if result.violations:
            print(f"\n[!] CRITICAL VIOLATIONS DETECTED ({len(result.violations)})")
            print("="*60)
            
            # Group violations by type
            violations_by_type = {}
            for v in result.violations:
                if v.violation_type not in violations_by_type:
                    violations_by_type[v.violation_type] = []
                violations_by_type[v.violation_type].append(v)
            
            for violation_type, violations in violations_by_type.items():
                print(f"\n{violation_type.upper()} ({len(violations)} instances):")
                for v in violations[:5]:  # Show first 5 of each type
                    print(f"  File: {v.file_path}:{v.line_number}")
                    print(f"     Issue: {v.description}")
                    print(f"     Fix: {v.suggestion}")
                    if verbose:
                        print(f"     Code: {v.line_content[:100]}")
                    print()
                if len(violations) > 5:
                    print(f"     ... and {len(violations) - 5} more instances")
        
        if result.warnings:
            print(f"\n[!] WARNINGS ({len(result.warnings)})")
            print("="*40)
            for w in result.warnings:
                print(f"  File: {w.file_path}:{w.line_number}")
                print(f"     Issue: {w.description}")
        
        if result.allowed_exceptions:
            print(f"\n[OK] ALLOWED EXCEPTIONS ({len(result.allowed_exceptions)})")
            print("="*40)
            for file_path, reason in result.allowed_exceptions:
                print(f"  File: {file_path}: {reason}")
        
        # Final verdict
        print("\n" + "="*80)
        if result.violations:
            print("[FAIL] COMPLIANCE CHECK FAILED")
            print("\nVIOLATIONS DETECTED: The backend contains JWT operations that violate")
            print("the auth service SSOT pattern. These must be removed to prevent:")
            print("- JWT secret mismatch errors")
            print("- WebSocket authentication failures")
            print("- Multi-user isolation issues")
            print("- Service boundary violations")
            
            print(f"\nBUSINESS IMPACT: These violations could cause $50K MRR loss")
            print("from WebSocket authentication failures and security issues.")
            
        else:
            print("[PASS] COMPLIANCE CHECK PASSED")
            print("\nAll checks passed! The backend properly delegates JWT operations")
            print("to the auth service, maintaining clean SSOT architecture.")
        
        print("="*80)


def main():
    """Main entry point for compliance checker."""
    parser = argparse.ArgumentParser(
        description="Check Auth SSOT compliance to prevent JWT regression",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/check_auth_ssot_compliance.py
  python scripts/check_auth_ssot_compliance.py --exclude-tests
  python scripts/check_auth_ssot_compliance.py --verbose
        """
    )
    
    parser.add_argument(
        "--exclude-tests",
        action="store_true",
        help="Exclude test files from compliance checking"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed output including line content"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize checker
        checker = AuthSSOTComplianceChecker(args.project_root)
        
        # Run compliance check
        result = checker.run_compliance_check(exclude_tests=args.exclude_tests)
        
        # Print results
        checker.print_results(result, verbose=args.verbose)
        
        # Exit with appropriate code
        if result.violations:
            print(f"\n[FAIL] Exiting with code 1 due to {len(result.violations)} violations")
            sys.exit(1)
        else:
            print(f"\n[PASS] Exiting with code 0 - no violations found")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Compliance check interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n[ERROR] Compliance check failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()