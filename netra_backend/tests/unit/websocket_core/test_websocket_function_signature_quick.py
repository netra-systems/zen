"""
Quick WebSocket Function Signature Test

This is a streamlined test to quickly validate that the WebSocket function signature 
issues are detected correctly using proper pytest syntax.
"""

import ast
import os
import pytest


def test_detect_single_parameter_create_error_message_calls():
    """
    CRITICAL: Detect single-parameter create_error_message calls that will fail.
    
    This test WILL FAIL initially to prove the bug exists.
    """
    websocket_ssot_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
    
    if not os.path.exists(websocket_ssot_path):
        pytest.skip(f"websocket_ssot.py not found at {websocket_ssot_path}", allow_module_level=True)
    
    with open(websocket_ssot_path, 'r') as f:
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


def test_real_implementation_requires_two_parameters():
    """
    CRITICAL: Verify that the real implementation requires both parameters.
    """
    from netra_backend.app.websocket_core.types import create_error_message as real_impl
    
    # Test 1: Correct usage (should work)
    result = real_impl("AUTH_FAILED", "Authentication failed")
    assert result is not None
    assert result.error_code == "AUTH_FAILED"
    assert result.error_message == "Authentication failed"
    
    # Test 2: Single parameter usage (should fail)
    with pytest.raises(TypeError) as exc_info:
        real_impl("Authentication failed")  # Missing error_message parameter
    
    error_message = str(exc_info.value)
    assert "missing 1 required positional argument" in error_message
    assert "error_message" in error_message


def test_fallback_implementation_accepts_single_parameter():
    """
    CRITICAL: Verify that fallback implementation is more permissive.
    """
    from netra_backend.app.websocket_core import create_error_message as fallback_impl
    
    # Test 1: Single parameter (should work with fallback)
    result = fallback_impl("Authentication failed")
    assert result is not None
    assert isinstance(result, dict)
    assert "error_code" in result
    
    # Test 2: Two parameters (should also work)
    result2 = fallback_impl("AUTH_FAILED", "Authentication failed")
    assert result2 is not None
    assert isinstance(result2, dict)


def test_server_message_signature_compatibility():
    """
    CRITICAL: Test create_server_message signature requirements.
    """
    from netra_backend.app.websocket_core.types import create_server_message as real_impl
    
    # Test 1: Correct usage (should work)
    result = real_impl("test_type", {"key": "value"})
    assert result is not None
    assert result.type.value == "test_type"
    assert result.data == {"key": "value"}
    
    # Test 2: Missing data parameter (should fail)
    with pytest.raises(TypeError) as exc_info:
        real_impl("test_type")  # Missing data parameter
    
    error_message = str(exc_info.value)
    assert "missing 1 required positional argument" in error_message
    assert "data" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])