"""Regression test for middleware context manager misuse.

This test ensures that middleware never incorrectly treats call_next as a context manager,
which would cause '_AsyncGeneratorContextManager' object has no attribute 'execute' errors.

Bug discovered: Sept 3, 2025
Issue: CORS middleware was checking if call_next had __aenter__ and trying to use it as context manager
Fix: Always call call_next directly as a function
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import inspect
import ast
import os
from pathlib import Path


class TestMiddlewareContextManagerRegression:
    """Regression tests to prevent context manager misuse in middleware."""
    
    def test_no_middleware_uses_call_next_as_context_manager(self):
        """Ensure no middleware tries to use call_next as a context manager."""
        middleware_dir = Path("netra_backend/app/middleware")
        errors = []
        
        for file_path in middleware_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for problematic patterns
            problematic_patterns = [
                "async with call_next",
                "async with.*call_next",
                "call_next.__aenter__",
                "hasattr(call_next, '__aenter__')",
                "if.*__aenter__.*call_next",
                "type(call_next).__name__.*AsyncGeneratorContextManager"
            ]
            
            for pattern in problematic_patterns:
                if pattern in content or pattern.replace(".*", "") in content:
                    errors.append(f"{file_path.name}: Contains pattern '{pattern}'")
        
        assert not errors, f"Middleware files with context manager misuse:\n" + "\n".join(errors)
    
    def test_all_middleware_call_next_directly(self):
        """Verify all middleware call call_next directly as a function."""
        middleware_dir = Path("netra_backend/app/middleware")
        middleware_files = []
        
        for file_path in middleware_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check if file contains a dispatch method (indicates it's middleware)
            if "async def dispatch" in content and "call_next" in content:
                # Verify it has the correct pattern
                if "await call_next(request)" in content:
                    middleware_files.append((file_path.name, True))
                else:
                    middleware_files.append((file_path.name, False))
        
        failures = [f for f, passed in middleware_files if not passed]
        assert not failures, f"Middleware not calling call_next directly: {failures}"
    
    @pytest.mark.asyncio
    async def test_call_next_behavior_with_mock(self):
        """Test that call_next works when called directly, fails if used as context manager."""
        
        # Create a mock that behaves like FastAPI's call_next
        mock_response = Response(content="test response")
        
        async def mock_call_next(request):
            """Mock call_next that returns a response."""
            return mock_response
        
        # Test direct call works
        request = Mock(spec=Request)
        response = await mock_call_next(request)
        assert response == mock_response
        
        # Verify it doesn't have context manager methods
        assert not hasattr(mock_call_next, '__aenter__')
        assert not hasattr(mock_call_next, '__aexit__')
        
        # If someone tried to use it as context manager, it would fail
        with pytest.raises(AttributeError):
            async with mock_call_next:  # This would fail
                pass
    
    def test_cors_fix_middleware_specifically(self):
        """Specific test for CORS fix middleware to prevent regression."""
        file_path = Path("netra_backend/app/middleware/cors_fix_middleware.py")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Ensure the fix is in place
        assert "await call_next(request)" in content, "CORS middleware must call call_next directly"
        
        # Ensure problematic patterns are not present
        problematic = [
            "async with call_next",
            "__aenter__",
            "AsyncGeneratorContextManager",
            "if hasattr(call_next",
            "if type(call_next)"
        ]
        
        for pattern in problematic:
            assert pattern not in content, f"CORS middleware contains problematic pattern: {pattern}"
    
    @pytest.mark.asyncio
    async def test_middleware_error_handling_pattern(self):
        """Ensure middleware error handling doesn't involve context managers."""
        
        class TestMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                """Correct pattern for middleware."""
                try:
                    # This is the correct way
                    response = await call_next(request)
                    return response
                except Exception as e:
                    # Handle error
                    return Response(content="Error", status_code=500)
        
        # Create instance and test
        app = Mock()
        middleware = TestMiddleware(app)
        
        mock_request = Mock(spec=Request)
        mock_response = Response(content="Success")
        mock_call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify call_next was called correctly
        mock_call_next.assert_called_once_with(mock_request)
        assert response == mock_response
    
    def test_no_type_checking_on_call_next(self):
        """Ensure no middleware does type checking on call_next."""
        middleware_dir = Path("netra_backend/app/middleware")
        errors = []
        
        for file_path in middleware_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for type checking patterns
            type_check_patterns = [
                "type(call_next)",
                "isinstance(call_next",
                "call_next.__class__",
                "type(call_next).__name__"
            ]
            
            for pattern in type_check_patterns:
                if pattern in content:
                    errors.append(f"{file_path.name}: Contains type checking '{pattern}'")
        
        assert not errors, f"Middleware with call_next type checking:\n" + "\n".join(errors)
    
    @pytest.mark.parametrize("middleware_file", [
        "cors_fix_middleware.py",
        "error_recovery_middleware.py",
        "logging_middleware.py",
        "security_headers_middleware.py"
    ])
    def test_critical_middleware_patterns(self, middleware_file):
        """Test critical middleware files for correct patterns."""
        file_path = Path(f"netra_backend/app/middleware/{middleware_file}")
        
        if not file_path.exists():
            pytest.skip(f"Middleware {middleware_file} not found")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        if "call_next" in content:
            # Must have correct await pattern
            assert "await call_next(request)" in content or "await call_next(req" in content, \
                f"{middleware_file} doesn't properly await call_next"
            
            # Must not have context manager pattern
            assert "async with call_next" not in content, \
                f"{middleware_file} incorrectly uses call_next as context manager"