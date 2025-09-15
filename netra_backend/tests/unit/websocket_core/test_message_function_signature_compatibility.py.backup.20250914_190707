"""
WebSocket Message Function Signature Compatibility Tests

Purpose: Detect and prevent function signature mismatches between real and fallback implementations
that cause WebSocket message creation failures.

CRITICAL BUSINESS IMPACT:
- WebSocket errors break chat functionality (90% of platform value)
- Authentication failures not properly communicated to users
- Service initialization errors cause silent failures
- Error handling breaks during cleanup procedures

Root Cause: Function signature incompatibility between:
- Real implementation: create_error_message(error_code: str, error_message: str)
- Fallback implementation: create_error_message(error_code, message="Error")

This test suite will:
1. FAIL initially to prove the bug exists
2. PASS once the fixes are implemented
3. Prevent regression of signature mismatches
"""

import ast
import os
import importlib
import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketMessageFunctionSignatureCompatibility(SSotBaseTestCase):
    """
    CRITICAL: Test function signature compatibility between real and fallback implementations.
    
    These tests are designed to FAIL initially to prove the bug exists, then PASS once fixes are applied.
    """
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.websocket_ssot_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
        
    def test_create_error_message_real_implementation_signature_validation(self):
        """
        CRITICAL: Verify create_error_message real implementation requires both parameters.
        
        This test will FAIL initially because the real implementation requires 2 parameters
        but code is calling it with 1 parameter.
        """
        # Import real implementation from types.py
        from netra_backend.app.websocket_core.types import create_error_message as real_create_error_message
        
        # Test 1: Correct usage (should work)
        try:
            result = real_create_error_message("AUTH_FAILED", "Authentication failed")
            assert result is not None
            assert result.error_code == "AUTH_FAILED"
            assert result.error_message == "Authentication failed"
        except Exception as e:
            pytest.fail(f"Real implementation with correct parameters failed: {e}")
        
        # Test 2: Incorrect usage that EXISTS in websocket_ssot.py (THIS SHOULD FAIL)
        with pytest.raises(TypeError) as context:
            real_create_error_message("Authentication failed")  # Missing error_message parameter
        
        error_message = str(context.exception)
        assert "missing 1 required positional argument" in error_message
        assert "error_message" in error_message
        
    def test_create_error_message_fallback_implementation_signature_validation(self):
        """
        CRITICAL: Verify create_error_message fallback implementation accepts single parameter.
        
        This shows the fallback is more permissive than the real implementation.
        """
        # Import fallback implementation from __init__.py
        from netra_backend.app.websocket_core import create_error_message as fallback_create_error_message
        
        # Test 1: Single parameter (should work with fallback)
        try:
            result = fallback_create_error_message("Authentication failed")
            assert result is not None
            # Fallback returns dict, not pydantic model
            assert isinstance(result, dict)
            assert "error_code" in result
            assert result["error_code"] == "Authentication failed"
        except Exception as e:
            pytest.fail(f"Fallback implementation with single parameter failed: {e}")
        
        # Test 2: Two parameters (should also work with fallback)
        try:
            result = fallback_create_error_message("AUTH_FAILED", "Authentication failed")
            assert result is not None
            assert isinstance(result, dict)
            assert "error_code" in result
            assert result["error_code"] == "AUTH_FAILED"
        except Exception as e:
            pytest.fail(f"Fallback implementation with two parameters failed: {e}")
    
    def test_create_server_message_signature_compatibility(self):
        """
        CRITICAL: Test create_server_message signature compatibility.
        
        Real implementation requires both msg_type and data parameters.
        """
        # Import real implementation
        from netra_backend.app.websocket_core.types import create_server_message as real_create_server_message
        
        # Test 1: Correct usage (should work)
        try:
            result = real_create_server_message("test_type", {"key": "value"})
            assert result is not None
            assert result.type.value == "test_type"
            assert result.data == {"key": "value"}
        except Exception as e:
            pytest.fail(f"Real create_server_message with correct parameters failed: {e}")
        
        # Test 2: Missing data parameter (should fail)
        with pytest.raises(TypeError) as context:
            real_create_server_message("test_type")  # Missing data parameter
        
        error_message = str(context.exception)
        assert "missing 1 required positional argument" in error_message
        assert "data" in error_message
    
    def test_problematic_function_calls_in_websocket_ssot_py(self):
        """
        CRITICAL: Detect problematic calling patterns in actual code.
        
        This test scans websocket_ssot.py for single-parameter create_error_message calls
        that will fail with the real implementation. THIS TEST WILL FAIL INITIALLY.
        """
        if not os.path.exists(self.websocket_ssot_path):
            self.skipTest(f"websocket_ssot.py not found at {self.websocket_ssot_path}")
        
        with open(self.websocket_ssot_path, 'r') as f:
            content = f.read()
        
        # Parse AST to find function calls
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in websocket_ssot.py: {e}")
        
        problematic_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for create_error_message calls with only 1 argument
                if (isinstance(node.func, ast.Name) and 
                    node.func.id == 'create_error_message' and 
                    len(node.args) == 1):
                    problematic_calls.append(f"Line {node.lineno}: create_error_message({ast.unparse(node.args[0])})")
        
        # THIS WILL FAIL INITIALLY - we expect to find problematic calls
        if problematic_calls:
            failure_message = (
                f"Found {len(problematic_calls)} problematic single-parameter create_error_message calls "
                f"that will fail with real implementation:\n" + 
                "\n".join(problematic_calls) +
                "\n\nThese calls need to be fixed to use 2-parameter signature: "
                "create_error_message(error_code, error_message)"
            )
            pytest.fail(failure_message)
    
    def test_import_path_resolution_affects_function_signatures(self):
        """
        CRITICAL: Test that import resolution order affects which function signatures are used.
        
        Direct imports from types.py get strict implementation.
        Package imports from __init__.py may get fallback implementation.
        """
        # Test 1: Direct import from types.py (strict implementation)
        try:
            from netra_backend.app.websocket_core.types import create_error_message
            # This should be the strict implementation requiring 2 parameters
            with pytest.raises(TypeError):
                create_error_message("single_parameter")
        except ImportError:
            pytest.fail("Direct import from types.py failed")
        
        # Test 2: Package-level import from __init__.py
        try:
            # Clear the module from cache to force re-import
            import sys
            if 'netra_backend.app.websocket_core' in sys.modules:
                del sys.modules['netra_backend.app.websocket_core']
            
            from netra_backend.app.websocket_core import create_error_message as package_impl
            
            # The package import should resolve to the same strict implementation
            # unless there's an import failure that triggers fallback
            try:
                # Try strict signature first
                result = package_impl("AUTH_FAILED", "Authentication failed")
                assert result is not None
            except TypeError:
                # If strict signature fails, this might be the fallback implementation
                try:
                    result = package_impl("Authentication failed")
                    assert result is not None
                    # If this works, we got the fallback implementation
                except TypeError:
                    pytest.fail("Neither strict nor fallback signature worked for package import")
                    
        except ImportError:
            pytest.fail("Package-level import failed")
    
    def test_websocket_ssot_import_pattern_analysis(self):
        """
        CRITICAL: Analyze the import pattern used in websocket_ssot.py.
        
        The import pattern determines which implementation is used.
        """
        if not os.path.exists(self.websocket_ssot_path):
            self.skipTest(f"websocket_ssot.py not found at {self.websocket_ssot_path}")
        
        with open(self.websocket_ssot_path, 'r') as f:
            content = f.read()
        
        # Look for the import statement
        import_lines = []
        for i, line in enumerate(content.split('\n'), 1):
            if 'create_error_message' in line and ('import' in line or 'from' in line):
                import_lines.append(f"Line {i}: {line.strip()}")
        
        assert len(import_lines) > 0, "No import statements found for create_error_message"
        
        # Check if it's a direct import from types (strict) or package import (potentially fallback)
        direct_import_found = False
        package_import_found = False
        
        for import_line in import_lines:
            if 'from netra_backend.app.websocket_core.types import' in import_line:
                direct_import_found = True
            elif 'from netra_backend.app.websocket_core import' in import_line:
                package_import_found = True
        
        # Document what we found
        import_analysis = {
            "direct_imports_from_types": direct_import_found,
            "package_imports": package_import_found,
            "import_lines": import_lines
        }
        
        # Log the analysis for debugging
        print(f"Import analysis: {import_analysis}")
        
        # If direct import from types is used, that explains why strict signature is required
        if direct_import_found:
            assert True, "Direct import from types.py found - explains strict signature requirement"
        else:
            pytest.fail("Expected to find direct import from types.py that causes signature mismatch")
    
    def test_function_signature_documentation_validation(self):
        """
        Validate that function signatures match their documentation and expected usage patterns.
        """
        # Import both implementations
        from netra_backend.app.websocket_core.types import create_error_message as real_impl
        from netra_backend.app.websocket_core import create_error_message as package_impl
        
        # Test real implementation signature
        import inspect
        real_sig = inspect.signature(real_impl)
        real_params = list(real_sig.parameters.keys())
        
        # Real implementation should have error_code and error_message parameters
        assert 'error_code' in real_params
        assert 'error_message' in real_params
        
        # Both should be required (no default values)
        error_code_param = real_sig.parameters['error_code']
        error_message_param = real_sig.parameters['error_message']
        
        assert error_code_param.default == inspect.Parameter.empty, "error_code should be required parameter"
        assert error_message_param.default == inspect.Parameter.empty, "error_message should be required parameter"
    
    def test_regression_prevention_scan(self):
        """
        Prevent regression by scanning for new instances of problematic patterns.
        
        This test should be run in CI to catch new single-parameter calls.
        """
        # Search patterns that indicate signature mismatches
        problematic_patterns = [
            # Single-parameter create_error_message calls
            r'create_error_message\s*\(\s*"[^"]*"\s*\)',  # create_error_message("string")
            r'create_error_message\s*\(\s*f"[^"]*"\s*\)',  # create_error_message(f"string")
            # Single-parameter create_server_message calls  
            r'create_server_message\s*\(\s*"[^"]*"\s*\)',  # create_server_message("string")
        ]
        
        # Files to scan
        scan_files = [
            self.websocket_ssot_path,
            "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/websocket_manager.py",
        ]
        
        violations = []
        
        for file_path in scan_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                import re
                for pattern in problematic_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append(f"{file_path}:{line_num}: {match.group()}")
        
        if violations:
            pytest.fail(f"Found {len(violations)} potential signature violations:\n" + 
                     "\n".join(violations))


class TestWebSocketMessageCreationEdgeCases(SSotBaseTestCase):
    """Test edge cases in WebSocket message creation that could cause signature mismatches."""
    
    def test_error_message_with_none_values(self):
        """Test error message creation with None values."""
        from netra_backend.app.websocket_core.types import create_error_message
        
        # None values should be rejected
        with pytest.raises((TypeError, ValueError)):
            create_error_message(None, "message")
        
        with pytest.raises((TypeError, ValueError)):
            create_error_message("code", None)
    
    def test_error_message_with_empty_strings(self):
        """Test error message creation with empty strings."""
        from netra_backend.app.websocket_core.types import create_error_message
        
        # Empty strings should be rejected
        with pytest.raises(ValueError):
            create_error_message("", "message")
        
        with pytest.raises(ValueError):
            create_error_message("code", "")
    
    def test_server_message_with_invalid_data_types(self):
        """Test server message creation with invalid data types."""
        from netra_backend.app.websocket_core.types import create_server_message
        
        # Non-dict data should be rejected  
        with pytest.raises((TypeError, ValueError)):
            create_server_message("test", "not_a_dict")
        
        # None data should be rejected
        with pytest.raises((TypeError, ValueError)):
            create_server_message("test", None)


class TestWebSocketFunctionCompatibilityMatrix(SSotBaseTestCase):
    """Test all combinations of real vs fallback function calls systematically."""
    
    def setup_method(self):
        super().setup_method()
        # Test data for various scenarios
        self.test_cases = [
            {"error_code": "AUTH_FAILED", "error_message": "Authentication failed"},
            {"error_code": "SERVICE_INIT_FAILED", "error_message": "Service initialization failed"}, 
            {"error_code": "CLEANUP_FAILED", "error_message": "Error during cleanup"},
            {"error_code": "INVALID_JSON", "error_message": "Invalid JSON format"},
        ]
    
    def test_compatibility_matrix_real_vs_fallback(self):
        """
        Test compatibility matrix between real and fallback implementations.
        
        This systematically tests all combinations to ensure compatibility.
        """
        from netra_backend.app.websocket_core.types import create_error_message as real_impl
        from netra_backend.app.websocket_core import create_error_message as fallback_impl
        
        for test_case in self.test_cases:
            error_code = test_case["error_code"]
            error_message = test_case["error_message"]
            
            with self.subTest(error_code=error_code, error_message=error_message):
                # Test 1: Real implementation with correct signature
                try:
                    real_result = real_impl(error_code, error_message)
                    assert IsNotNone(real_result)
                    assert real_result.error_code == error_code
                    assert real_result.error_message == error_message
                except Exception as e:
                    pytest.fail(f"Real implementation failed with correct parameters: {e}")
                
                # Test 2: Fallback implementation with two parameters
                try:
                    fallback_result = fallback_impl(error_code, error_message)
                    assert IsNotNone(fallback_result)
                    # Fallback returns dict
                    assert IsInstance(fallback_result, dict)
                except Exception as e:
                    pytest.fail(f"Fallback implementation failed with two parameters: {e}")
                
                # Test 3: Real implementation with single parameter (should fail)
                with pytest.raises(TypeError):
                    real_impl(error_message)  # Single parameter should fail
                
                # Test 4: Fallback implementation with single parameter (should work)
                try:
                    fallback_single_result = fallback_impl(error_message)
                    assert IsNotNone(fallback_single_result)
                    assert IsInstance(fallback_single_result, dict)
                except Exception as e:
                    pytest.fail(f"Fallback implementation failed with single parameter: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])