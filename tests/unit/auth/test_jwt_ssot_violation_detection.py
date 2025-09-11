"""
JWT SSOT Violation Detection Tests - Unit Level
PURPOSE: Create tests that FAIL with current duplicate JWT implementations to prove consolidation is needed
These tests detect direct JWT imports and operations in backend that violate SSOT architecture
"""
import ast
import os
import pytest
from pathlib import Path
from typing import List, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestJWTSSOTViolationDetection(SSotBaseTestCase):
    """Unit tests to detect JWT SSOT violations in backend service"""
    
    def setUp(self):
        super().setUp()
        self.backend_path = Path(__file__).parent.parent.parent.parent / "netra_backend"
        self.auth_service_path = Path(__file__).parent.parent.parent.parent / "auth_service"
    
    def test_backend_should_not_have_jwt_imports(self):
        """REGRESSION TEST: Backend should not import JWT libraries - should FAIL currently
        
        This test scans backend code for direct JWT imports that violate SSOT architecture.
        Expected to FAIL with current duplicate implementations.
        """
        jwt_imports_found = []
        
        # Scan backend app directory for JWT imports (excluding test files)
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            pytest.skip(f"Backend app path not found: {backend_app_path}")
        
        for python_file in backend_app_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in str(python_file) or "__pycache__" in str(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for direct JWT imports
                if any(pattern in content for pattern in [
                    "import jwt",
                    "from jwt",
                    "import PyJWT",
                    "from PyJWT"
                ]):
                    jwt_imports_found.append(str(python_file.relative_to(self.backend_path)))
                    
            except (UnicodeDecodeError, IOError):
                # Skip files that can't be read
                continue
        
        # This test SHOULD FAIL with current implementation to prove violations exist
        if jwt_imports_found:
            violation_details = "\n".join([
                "JWT SSOT VIOLATIONS DETECTED:",
                f"Found {len(jwt_imports_found)} files with direct JWT imports in backend:",
                *[f"  - {file_path}" for file_path in jwt_imports_found[:10]],  # Show first 10
                "" if len(jwt_imports_found) <= 10 else f"  ... and {len(jwt_imports_found) - 10} more files",
                "",
                "ARCHITECTURE VIOLATION: Backend should NOT directly import JWT libraries.",
                "All JWT operations MUST go through auth service SSOT (JWTHandler).",
                "This proves SSOT consolidation is urgently needed."
            ])
            
            # Fail the test to prove violations exist
            pytest.fail(violation_details)
        else:
            # If no violations found, this is unexpected given known duplicates
            pytest.fail(
                "UNEXPECTED: No JWT imports found in backend. "
                "This may indicate the scan missed violations or they've been fixed. "
                "Please verify auth service SSOT compliance."
            )
    
    def test_backend_should_not_validate_jwt_tokens(self):
        """REGRESSION TEST: Backend should not validate JWT tokens - should FAIL currently
        
        This test scans for direct JWT decode/validate operations in backend.
        Expected to FAIL with current duplicate JWT validation logic.
        """
        jwt_operations_found = []
        
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            pytest.skip(f"Backend app path not found: {backend_app_path}")
        
        # Patterns that indicate direct JWT operations (SSOT violations)
        jwt_operation_patterns = [
            "jwt.decode(",
            "jwt.encode(",
            "PyJWT.decode(",
            "PyJWT.encode(",
            "def validate_token",
            "def decode_jwt",
            "def encode_jwt",
            "jwt_secret",
            "JWT_SECRET"
        ]
        
        for python_file in backend_app_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in str(python_file) or "__pycache__" in str(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for JWT operations
                found_operations = []
                for pattern in jwt_operation_patterns:
                    if pattern in content:
                        found_operations.append(pattern)
                
                if found_operations:
                    jwt_operations_found.append({
                        "file": str(python_file.relative_to(self.backend_path)),
                        "operations": found_operations
                    })
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        # This test SHOULD FAIL to prove SSOT violations exist
        if jwt_operations_found:
            violation_details = "\n".join([
                "JWT OPERATION VIOLATIONS DETECTED:",
                f"Found {len(jwt_operations_found)} files with direct JWT operations in backend:",
                *[f"  - {item['file']}: {', '.join(item['operations'])}" 
                  for item in jwt_operations_found[:10]],
                "" if len(jwt_operations_found) <= 10 else f"  ... and {len(jwt_operations_found) - 10} more files",
                "",
                "ARCHITECTURE VIOLATION: Backend should NOT perform direct JWT operations.",
                "All JWT validation MUST be delegated to auth service SSOT.",
                "This proves SSOT consolidation is critically needed."
            ])
            
            pytest.fail(violation_details)
        else:
            pytest.fail(
                "UNEXPECTED: No JWT operations found in backend. "
                "This suggests violations may have been fixed or scan missed them."
            )
    
    def test_websocket_should_use_auth_service_only(self):
        """REGRESSION TEST: WebSocket JWT should route through auth service - should FAIL currently
        
        This test specifically checks WebSocket authentication for SSOT violations.
        Expected to FAIL with current direct JWT handling in WebSocket code.
        """
        websocket_jwt_violations = []
        
        # Check WebSocket-specific files for JWT violations
        websocket_files = [
            self.backend_path / "app" / "websocket_core" / "user_context_extractor.py",
            self.backend_path / "app" / "websocket_core" / "auth.py", 
            self.backend_path / "app" / "routes" / "websocket.py",
            self.backend_path / "app" / "middleware" / "auth_middleware.py"
        ]
        
        websocket_violation_patterns = [
            "jwt.decode",
            "validate_and_decode_jwt",
            "JWT.*decode",
            "get_unified_jwt_secret",  # Should use auth service instead
            "jwt_secret",
            "JWT_SECRET_KEY"
        ]
        
        for websocket_file in websocket_files:
            if not websocket_file.exists():
                continue
                
            try:
                with open(websocket_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                found_violations = []
                for pattern in websocket_violation_patterns:
                    if pattern in content:
                        # Count occurrences for severity
                        count = content.count(pattern)
                        found_violations.append(f"{pattern} ({count} times)")
                
                if found_violations:
                    websocket_jwt_violations.append({
                        "file": str(websocket_file.relative_to(self.backend_path)),
                        "violations": found_violations
                    })
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        # This test SHOULD FAIL to prove WebSocket SSOT violations
        if websocket_jwt_violations:
            violation_details = "\n".join([
                "WEBSOCKET JWT SSOT VIOLATIONS DETECTED:",
                f"Found {len(websocket_jwt_violations)} WebSocket files with JWT violations:",
                *[f"  - {item['file']}: {', '.join(item['violations'])}" 
                  for item in websocket_jwt_violations],
                "",
                "CRITICAL VIOLATION: WebSocket authentication bypasses auth service SSOT.",
                "This creates JWT secret mismatches and 403 authentication failures.",
                "WebSocket must route ALL JWT operations through auth service."
            ])
            
            pytest.fail(violation_details)
        else:
            pytest.fail(
                "UNEXPECTED: No WebSocket JWT violations found. "
                "This suggests violations may have been fixed or require deeper analysis."
            )
    
    def test_detect_duplicate_jwt_validation_functions(self):
        """REGRESSION TEST: Detect duplicate JWT validation functions - should FAIL currently
        
        This test uses AST parsing to find duplicate JWT validation function definitions.
        Expected to FAIL with current multiple JWT validation implementations.
        """
        jwt_functions_found = {}
        
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            pytest.skip(f"Backend app path not found: {backend_app_path}")
        
        # Function names that indicate JWT validation (SSOT violations)
        jwt_function_names = {
            "validate_token",
            "decode_jwt", 
            "encode_jwt",
            "validate_jwt",
            "validate_and_decode_jwt",
            "extract_jwt_payload",
            "verify_jwt_signature"
        }
        
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
                            if node.name in jwt_function_names:
                                file_path = str(python_file.relative_to(self.backend_path))
                                if node.name not in jwt_functions_found:
                                    jwt_functions_found[node.name] = []
                                jwt_functions_found[node.name].append(file_path)
                                
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        # This test SHOULD FAIL to prove duplicate functions exist
        duplicate_functions = {name: files for name, files in jwt_functions_found.items() if len(files) > 1}
        
        if duplicate_functions:
            violation_details = "\n".join([
                "DUPLICATE JWT VALIDATION FUNCTIONS DETECTED:",
                f"Found {len(duplicate_functions)} function names with multiple implementations:",
                *[f"  - {func_name}: {len(files)} implementations in {', '.join(files[:3])}" + 
                  (f" + {len(files)-3} more" if len(files) > 3 else "")
                  for func_name, files in duplicate_functions.items()],
                "",
                "SSOT VIOLATION: Multiple JWT validation functions violate Single Source of Truth.",
                "All JWT operations should be consolidated in auth service JWTHandler.",
                "This proves SSOT consolidation is essential."
            ])
            
            pytest.fail(violation_details)
        elif jwt_functions_found:
            # Even single JWT functions in backend are violations
            violation_details = "\n".join([
                "JWT VALIDATION FUNCTIONS FOUND IN BACKEND:",
                f"Found {len(jwt_functions_found)} JWT function types:",
                *[f"  - {func_name}: in {', '.join(files)}"
                  for func_name, files in jwt_functions_found.items()],
                "",
                "ARCHITECTURE VIOLATION: Backend should not contain JWT validation functions.",
                "All JWT operations MUST be delegated to auth service SSOT."
            ])
            
            pytest.fail(violation_details)
        else:
            pytest.fail(
                "UNEXPECTED: No JWT validation functions found in backend. "
                "This may indicate violations have been fixed or scan limitations."
            )

    def test_jwt_secret_access_patterns_violation(self):
        """REGRESSION TEST: Detect JWT secret access patterns - should FAIL currently
        
        This test scans for code patterns that directly access JWT secrets,
        which violates SSOT architecture where only auth service should access secrets.
        """
        secret_access_violations = []
        
        backend_app_path = self.backend_path / "app"
        
        if not backend_app_path.exists():
            pytest.skip(f"Backend app path not found: {backend_app_path}")
        
        # Patterns indicating direct JWT secret access (SSOT violations)
        secret_access_patterns = [
            "JWT_SECRET_KEY",
            "JWT_SECRET_STAGING", 
            "JWT_SECRET_PRODUCTION",
            "get_jwt_secret",
            "jwt_secret",
            "os.environ.get.*JWT",
            "env.get.*JWT"
        ]
        
        for python_file in backend_app_path.rglob("*.py"):
            if "test" in str(python_file) or "__pycache__" in str(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                file_violations = []
                for i, line in enumerate(lines, 1):
                    for pattern in secret_access_patterns:
                        if pattern in line and not line.strip().startswith("#"):
                            file_violations.append({
                                "line": i,
                                "pattern": pattern,
                                "code": line.strip()[:100]  # First 100 chars
                            })
                
                if file_violations:
                    secret_access_violations.append({
                        "file": str(python_file.relative_to(self.backend_path)),
                        "violations": file_violations
                    })
                    
            except (UnicodeDecodeError, IOError):
                continue
        
        # This test SHOULD FAIL to prove secret access violations
        if secret_access_violations:
            violation_details = ["JWT SECRET ACCESS VIOLATIONS DETECTED:"]
            violation_count = sum(len(item['violations']) for item in secret_access_violations)
            violation_details.append(f"Found {violation_count} secret access violations in {len(secret_access_violations)} files:")
            
            for item in secret_access_violations[:5]:  # Show first 5 files
                violation_details.append(f"  - {item['file']}:")
                for violation in item['violations'][:3]:  # Show first 3 violations per file
                    violation_details.append(f"    Line {violation['line']}: {violation['pattern']} -> {violation['code']}")
                if len(item['violations']) > 3:
                    violation_details.append(f"    ... and {len(item['violations']) - 3} more violations")
            
            if len(secret_access_violations) > 5:
                violation_details.append(f"  ... and {len(secret_access_violations) - 5} more files")
            
            violation_details.extend([
                "",
                "CRITICAL SSOT VIOLATION: Backend directly accesses JWT secrets.",
                "Only auth service should access JWT configuration.",
                "This creates secret synchronization issues and violates SSOT architecture."
            ])
            
            pytest.fail("\n".join(violation_details))
        else:
            pytest.fail(
                "UNEXPECTED: No JWT secret access violations found in backend. "
                "This suggests violations may have been resolved or require deeper scanning."
            )