"""
JWT SSOT Violation Detection Tests - Issue #1078
Purpose: Create FAILING tests to detect JWT SSOT violations in backend service
These tests should FAIL initially to prove violations exist, then PASS after remediation

Business Value Justification (BVJ):
- Segment: Platform/Enterprise (Security compliance) 
- Business Goal: Eliminate JWT secret mismatches causing 403 auth failures
- Value Impact: Ensures reliable authentication for $500K+ ARR protection
- Revenue Impact: Prevents authentication system failures blocking customer usage
"""
import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class JWTSSOTIssue1078ViolationsTests(SSotBaseTestCase):
    """Unit tests to detect JWT SSOT violations - Issue #1078"""
    
    def setup_method(self):
        super().setup_method()
        self.backend_path = Path(__file__).parent.parent.parent.parent / "netra_backend"
        self.auth_service_path = Path(__file__).parent.parent.parent.parent / "auth_service"
        self.violations_found = []
    
    def _scan_backend_files_for_patterns(self, patterns: List[str], exclude_tests: bool = True) -> List[Dict]:
        """
        Scan backend files for violation patterns.
        
        Args:
            patterns: List of regex patterns to search for
            exclude_tests: Whether to exclude test files from scan
            
        Returns:
            List of violation dictionaries with file, line, pattern, code
        """
        violations = []
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            return violations
        
        for python_file in backend_app_path.rglob("*.py"):
            # Skip test files and __pycache__ if requested
            if exclude_tests and ("test" in str(python_file) or "__pycache__" in str(python_file)):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                for i, line in enumerate(lines, 1):
                    # Skip commented lines
                    if line.strip().startswith("#"):
                        continue
                        
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append({
                                "file": str(python_file.relative_to(self.backend_path)),
                                "line": i,
                                "pattern": pattern,
                                "code": line.strip()[:100]  # First 100 chars
                            })
                            break  # One violation per line
                            
            except (UnicodeDecodeError, IOError):
                continue
                
        return violations
    
    def _scan_for_ast_function_names(self, function_names: Set[str]) -> Dict[str, List[str]]:
        """
        Use AST parsing to find function definitions.
        
        Args:
            function_names: Set of function names to search for
            
        Returns:
            Dictionary mapping function names to files where they're defined
        """
        functions_found = {}
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            return functions_found
        
        for python_file in backend_app_path.rglob("*.py"):
            if "test" in str(python_file) or "__pycache__" in str(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name in function_names:
                                file_path = str(python_file.relative_to(self.backend_path))
                                if node.name not in functions_found:
                                    functions_found[node.name] = []
                                functions_found[node.name].append(file_path)
                                
                except SyntaxError:
                    continue
                    
            except (UnicodeDecodeError, IOError):
                continue
                
        return functions_found
    
    def test_detect_backend_jwt_direct_imports(self):
        """
        FAILING TEST: Detect direct JWT imports in backend (Issue #1078)
        
        This test scans backend for direct JWT library imports that violate SSOT.
        Expected to FAIL with current implementation to prove violations exist.
        """
        jwt_import_patterns = [
            r"^import jwt\b",
            r"^from jwt\b", 
            r"^import PyJWT\b",
            r"^from PyJWT\b",
            r"import.*jwt.*as",
            r"from.*jwt.*import"
        ]
        
        violations = self._scan_backend_files_for_patterns(jwt_import_patterns)
        
        if violations:
            violation_details = [
                f"JWT DIRECT IMPORT VIOLATIONS DETECTED (Issue #1078):",
                f"Found {len(violations)} violations across {len(set(v['file'] for v in violations))} files:",
                ""
            ]
            
            # Group by file for better reporting
            files_with_violations = {}
            for v in violations[:15]:  # Show first 15
                if v['file'] not in files_with_violations:
                    files_with_violations[v['file']] = []
                files_with_violations[v['file']].append(v)
            
            for file_path, file_violations in files_with_violations.items():
                violation_details.append(f"  📄 {file_path}:")
                for v in file_violations[:3]:  # Max 3 per file
                    violation_details.append(f"    Line {v['line']}: {v['code']}")
                if len(file_violations) > 3:
                    violation_details.append(f"    ... and {len(file_violations) - 3} more violations")
                violation_details.append("")
            
            if len(violations) > 15:
                violation_details.append(f"  ... and {len(violations) - 15} more violations")
            
            violation_details.extend([
                "",
                "🚨 ARCHITECTURE VIOLATION:",
                "Backend should NOT directly import JWT libraries.",
                "All JWT operations MUST go through auth service SSOT.",
                "",
                "REMEDIATION REQUIRED:",
                "1. Remove all direct JWT imports from backend",
                "2. Use auth_client.validate_token_jwt() for all JWT operations", 
                "3. Delegate all JWT functions to auth service",
                "",
                "This test proves SSOT consolidation is urgently needed."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # If no violations found, this is unexpected given Issue #1078
        pytest.fail(
            "UNEXPECTED RESULT: No JWT direct imports found in backend.\n"
            "This may indicate:\n"
            "1. The violations have already been fixed\n" 
            "2. The scan missed some violation patterns\n"
            "3. Violations exist in different forms\n\n"
            "Please verify SSOT compliance manually or expand scan patterns."
        )
    
    def test_detect_jwt_secret_direct_access(self):
        """
        FAILING TEST: Detect JWT secret access in backend (Issue #1078)
        
        This test finds backend files directly accessing JWT secrets instead of
        using auth service. Expected to FAIL with current violations.
        """
        secret_access_patterns = [
            r"JWT_SECRET_KEY",
            r"JWT_SECRET_STAGING",
            r"JWT_SECRET_PRODUCTION", 
            r"get_jwt_secret",
            r"jwt_secret",
            r"os\.environ\.get.*JWT",
            r"env\.get.*JWT",
            r"getenv.*JWT",
            r"environ\[.*JWT",
            r"\.jwt_secret_key"
        ]
        
        violations = self._scan_backend_files_for_patterns(secret_access_patterns)
        
        if violations:
            violation_details = [
                f"JWT SECRET ACCESS VIOLATIONS DETECTED (Issue #1078):",
                f"Found {len(violations)} secret access violations:",
                ""
            ]
            
            # Group by pattern type for analysis
            pattern_groups = {}
            for v in violations:
                if v['pattern'] not in pattern_groups:
                    pattern_groups[v['pattern']] = []
                pattern_groups[v['pattern']].append(v)
            
            for pattern, pattern_violations in pattern_groups.items():
                violation_details.append(f"  🔑 Pattern '{pattern}' ({len(pattern_violations)} occurrences):")
                for v in pattern_violations[:3]:  # Max 3 per pattern
                    violation_details.append(f"    {v['file']}:{v['line']} - {v['code']}")
                if len(pattern_violations) > 3:
                    violation_details.append(f"    ... and {len(pattern_violations) - 3} more")
                violation_details.append("")
            
            violation_details.extend([
                "🚨 CRITICAL SECURITY VIOLATION:",
                "Backend should NOT directly access JWT secrets.",
                "Only auth service should access JWT configuration.",
                "",
                "SECURITY RISKS:",
                "- JWT secret mismatches between services",
                "- 403 authentication failures",
                "- Secret synchronization issues",
                "- HIPAA/SOC2/SEC compliance violations",
                "",
                "REMEDIATION REQUIRED:",
                "1. Remove all direct JWT secret access from backend",
                "2. Use auth service for all JWT secret operations",
                "3. Implement pure delegation pattern",
                "",
                "This proves SSOT secret management is critically needed."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # If no violations, this might be unexpected
        pytest.fail(
            "UNEXPECTED RESULT: No JWT secret access found in backend.\n"
            "This suggests either:\n"
            "1. SSOT secret management has been implemented\n"
            "2. Violations exist in different patterns\n"
            "3. Configuration access is abstracted\n\n"
            "Please verify auth service is the only JWT secret accessor."
        )
    
    def test_detect_duplicate_jwt_validation_functions(self):
        """
        FAILING TEST: Find duplicate JWT validation functions (Issue #1078)
        
        This test uses AST parsing to find duplicate JWT validation function
        definitions. Expected to FAIL with current multiple implementations.
        """
        jwt_function_names = {
            "validate_token",
            "decode_jwt", 
            "encode_jwt",
            "validate_jwt",
            "validate_and_decode_jwt",
            "extract_jwt_payload",
            "verify_jwt_signature",
            "create_access_token",
            "create_refresh_token",
            "blacklist_token"
        }
        
        functions_found = self._scan_for_ast_function_names(jwt_function_names)
        
        # Check for duplicates (multiple files defining same function)
        duplicate_functions = {
            name: files for name, files in functions_found.items() if len(files) > 1
        }
        
        if duplicate_functions:
            violation_details = [
                f"DUPLICATE JWT VALIDATION FUNCTIONS DETECTED (Issue #1078):",
                f"Found {len(duplicate_functions)} function names with multiple implementations:",
                ""
            ]
            
            for func_name, files in duplicate_functions.items():
                violation_details.append(f"  🔄 Function '{func_name}' found in {len(files)} files:")
                for file_path in files[:5]:  # Show first 5 files
                    violation_details.append(f"    - {file_path}")
                if len(files) > 5:
                    violation_details.append(f"    ... and {len(files) - 5} more files")
                violation_details.append("")
            
            violation_details.extend([
                "🚨 SSOT VIOLATION:",
                "Multiple JWT validation functions violate Single Source of Truth.",
                "Auth service should be the ONLY implementation of JWT operations.",
                "",
                "ARCHITECTURAL PROBLEMS:",
                "- Code duplication and maintenance burden",
                "- Inconsistent JWT validation logic",
                "- Secret synchronization issues",
                "- Testing complexity",
                "",
                "REMEDIATION REQUIRED:",
                "1. Consolidate all JWT functions in auth service JWTHandler",
                "2. Remove duplicate implementations from backend",
                "3. Use pure delegation pattern throughout",
                "",
                "This proves SSOT consolidation is essential."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # Even single JWT functions in backend are violations
        elif functions_found:
            violation_details = [
                f"JWT VALIDATION FUNCTIONS FOUND IN BACKEND (Issue #1078):",
                f"Found {len(functions_found)} JWT function types in backend:",
                ""
            ]
            
            for func_name, files in functions_found.items():
                violation_details.append(f"  ⚠️  Function '{func_name}' in:")
                for file_path in files:
                    violation_details.append(f"    - {file_path}")
                violation_details.append("")
            
            violation_details.extend([
                "🚨 ARCHITECTURE VIOLATION:",
                "Backend should not contain JWT validation functions.",
                "All JWT operations MUST be delegated to auth service SSOT.",
                "",
                "REMEDIATION:",
                "Replace backend JWT functions with auth_client calls."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # If no functions found, this is unexpected
        pytest.fail(
            "UNEXPECTED RESULT: No JWT validation functions found in backend.\n"
            "This suggests either:\n"
            "1. Functions have been renamed or moved\n"
            "2. SSOT consolidation has been implemented\n"
            "3. Function detection needs expanded patterns\n\n"
            "Please verify backend uses only auth service delegation."
        )
    
    def test_websocket_jwt_validation_uses_auth_service(self):
        """
        FAILING TEST: Verify WebSocket JWT uses auth service (Issue #1078)
        
        This test specifically checks WebSocket authentication for SSOT violations.
        Expected to FAIL with current direct JWT handling.
        """
        websocket_files = [
            self.backend_path / "app" / "websocket_core" / "user_context_extractor.py",
            self.backend_path / "app" / "websocket_core" / "auth.py",
            self.backend_path / "app" / "routes" / "websocket.py",
            self.backend_path / "app" / "websocket_core" / "manager.py",
            self.backend_path / "app" / "middleware" / "auth_middleware.py"
        ]
        
        websocket_violation_patterns = [
            r"jwt\.decode\(",
            r"validate_and_decode_jwt\(",
            r"JWT.*decode",
            r"get_unified_jwt_secret",
            r"jwt_secret",
            r"JWT_SECRET_KEY",
            r"decode.*jwt.*locally",
            r"direct.*jwt.*validation"
        ]
        
        websocket_violations = []
        
        for websocket_file in websocket_files:
            if not websocket_file.exists():
                continue
                
            try:
                with open(websocket_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                file_violations = []
                for i, line in enumerate(lines, 1):
                    if line.strip().startswith("#"):
                        continue
                        
                    for pattern in websocket_violation_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            file_violations.append({
                                "line": i,
                                "pattern": pattern,
                                "code": line.strip()[:80]
                            })
                
                if file_violations:
                    websocket_violations.append({
                        "file": str(websocket_file.relative_to(self.backend_path)),
                        "violations": file_violations
                    })
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        if websocket_violations:
            violation_details = [
                f"WEBSOCKET JWT SSOT VIOLATIONS DETECTED (Issue #1078):",
                f"Found {len(websocket_violations)} WebSocket files with JWT violations:",
                ""
            ]
            
            for item in websocket_violations:
                violation_details.append(f"  🔌 {item['file']}:")
                for v in item['violations'][:4]:  # Max 4 per file
                    violation_details.append(f"    Line {v['line']}: {v['code']}")
                if len(item['violations']) > 4:
                    violation_details.append(f"    ... and {len(item['violations']) - 4} more violations")
                violation_details.append("")
            
            violation_details.extend([
                "🚨 CRITICAL WEBSOCKET VIOLATION:",
                "WebSocket authentication bypasses auth service SSOT.",
                "",
                "CONSEQUENCES:",
                "- JWT secret mismatches causing 403 authentication failures",
                "- Inconsistent token validation between HTTP and WebSocket",
                "- Security vulnerabilities in real-time communications",
                "- User session inconsistencies",
                "",
                "REMEDIATION REQUIRED:",
                "1. Remove all direct JWT operations from WebSocket code", 
                "2. Use auth_client.validate_token_jwt() exclusively",
                "3. Ensure consistent JWT secret source",
                "",
                "This proves WebSocket SSOT compliance is critical for Issue #1078."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # If no violations found, verify auth service usage
        auth_service_usage_patterns = [
            r"auth_client\.validate_token_jwt",
            r"auth_service.*validate",
            r"AuthServiceClient",
            r"get_auth_service"
        ]
        
        auth_usage_found = False
        for websocket_file in websocket_files:
            if not websocket_file.exists():
                continue
                
            try:
                with open(websocket_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if any(re.search(pattern, content) for pattern in auth_service_usage_patterns):
                    auth_usage_found = True
                    break
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        if not auth_usage_found:
            pytest.fail(
                "WEBSOCKET AUTH SERVICE USAGE NOT DETECTED (Issue #1078):\n"
                "WebSocket files should use auth service for JWT validation.\n\n"
                "Expected patterns not found:\n"
                "- auth_client.validate_token_jwt()\n"
                "- AuthServiceClient usage\n"
                "- auth service delegation\n\n"
                "This suggests WebSocket may not be using proper SSOT delegation."
            )
        
        # If auth service usage found but no violations, this is good!
        # But for Issue #1078 testing, we expect some violations initially
        pytest.skip(
            "WebSocket appears to be using auth service correctly.\n"
            "This is good for SSOT compliance but unexpected for Issue #1078 testing.\n"
            "Manual verification recommended."
        )
    
    def test_jwt_configuration_environment_access_violations(self):
        """
        FAILING TEST: Detect non-SSOT environment access (Issue #1078)
        
        This test finds JWT configuration that doesn't use IsolatedEnvironment.
        Expected to FAIL with current direct os.environ access.
        """
        environment_violation_patterns = [
            r"os\.environ\.get.*JWT",
            r"os\.environ\[.*JWT",
            r"getenv.*JWT",
            r"environ\.get.*JWT",
            r"env\[.*JWT.*\]",  # Direct dict access
            r"os\.getenv.*JWT"
        ]
        
        violations = self._scan_backend_files_for_patterns(environment_violation_patterns)
        
        if violations:
            violation_details = [
                f"JWT ENVIRONMENT ACCESS VIOLATIONS DETECTED (Issue #1078):",
                f"Found {len(violations)} direct environment access violations:",
                ""
            ]
            
            # Group by file for reporting
            files_with_violations = {}
            for v in violations:
                if v['file'] not in files_with_violations:
                    files_with_violations[v['file']] = []
                files_with_violations[v['file']].append(v)
            
            for file_path, file_violations in files_with_violations.items():
                violation_details.append(f"  🌍 {file_path}:")
                for v in file_violations[:3]:
                    violation_details.append(f"    Line {v['line']}: {v['code']}")
                if len(file_violations) > 3:
                    violation_details.append(f"    ... and {len(file_violations) - 3} more")
                violation_details.append("")
            
            violation_details.extend([
                "🚨 CONFIGURATION SSOT VIOLATION:",
                "JWT configuration should use IsolatedEnvironment, not direct os.environ.",
                "",
                "PROBLEMS:",
                "- Bypasses SSOT environment management",
                "- Inconsistent configuration access patterns",
                "- Testing complications",
                "- Environment isolation violations",
                "",
                "REMEDIATION REQUIRED:",
                "1. Replace os.environ with IsolatedEnvironment.get()",
                "2. Use get_env() from shared.isolated_environment",
                "3. Implement SSOT configuration patterns",
                "",
                "This proves SSOT environment access is needed for Issue #1078."
            ])
            
            pytest.fail("\n".join(violation_details))
        
        # Check for proper SSOT environment usage
        ssot_environment_patterns = [
            r"IsolatedEnvironment",
            r"get_env\(\)",
            r"shared\.isolated_environment",
            r"from shared\.isolated_environment import"
        ]
        
        ssot_usage = self._scan_backend_files_for_patterns(ssot_environment_patterns)
        
        if not ssot_usage:
            pytest.fail(
                "NO SSOT ENVIRONMENT ACCESS DETECTED (Issue #1078):\n"
                "Backend should use IsolatedEnvironment for JWT configuration.\n\n"
                "Expected patterns not found:\n"
                "- from shared.isolated_environment import get_env\n" 
                "- env = get_env()\n"
                "- IsolatedEnvironment usage\n\n"
                "This suggests environment access may not be SSOT compliant."
            )
        
        # If SSOT usage found without violations, that's actually good
        pytest.skip(
            "SSOT environment access patterns detected without violations.\n"
            "This suggests JWT configuration may already be SSOT compliant.\n"
            "Manual verification recommended for Issue #1078."
        )
    
    def test_auth_service_canonical_implementation_exists(self):
        """
        VALIDATION TEST: Verify auth service has canonical JWT implementation
        
        This test ensures auth service provides the SSOT JWT implementation
        that backend should delegate to.
        """
        auth_jwt_handler_path = self.auth_service_path / "auth_core" / "core" / "jwt_handler.py"
        
        if not auth_jwt_handler_path.exists():
            pytest.fail(
                "AUTH SERVICE JWT HANDLER NOT FOUND (Issue #1078):\n"
                f"Expected: {auth_jwt_handler_path}\n\n"
                "Auth service must provide canonical JWT implementation.\n"
                "Without this, backend cannot delegate JWT operations properly."
            )
        
        # Verify JWT handler has required methods
        try:
            with open(auth_jwt_handler_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_methods = [
                "validate_token",
                "create_access_token", 
                "create_refresh_token",
                "extract_user_id"
            ]
            
            missing_methods = []
            for method in required_methods:
                if f"def {method}" not in content and f"async def {method}" not in content:
                    missing_methods.append(method)
            
            if missing_methods:
                pytest.fail(
                    f"AUTH SERVICE JWT HANDLER INCOMPLETE (Issue #1078):\n"
                    f"Missing required methods: {missing_methods}\n\n"
                    "Auth service JWT handler must provide complete JWT functionality\n"
                    "for backend delegation to work properly."
                )
            
            # This test should PASS if auth service is properly implemented
            assert True, "Auth service JWT handler appears complete"
            
        except (UnicodeDecodeError, IOError) as e:
            pytest.fail(f"Failed to read auth service JWT handler: {e}")