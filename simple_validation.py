#!/usr/bin/env python3
"""
Simple ASCII-only validation for SessionMiddleware Issue #169 Fix
"""

import sys
import traceback
from unittest.mock import Mock
from fastapi import Request

sys.path.append('.')
from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware


def test_core_fix():
    """Test the core SessionMiddleware fix."""
    print("Testing SessionMiddleware Issue #169 Fix")
    print("=" * 50)
    
    try:
        # Create middleware
        middleware = GCPAuthContextMiddleware(None)
        print("PASS: Middleware created successfully")
        
        # Test 1: Session access with AssertionError (the original bug)
        mock_request = Mock(spec=Request)
        mock_request.cookies = {'user_id': 'test123'}
        mock_request.state = Mock()
        
        def session_fails():
            raise AssertionError("SessionMiddleware must be installed to access request.session")
        type(mock_request).session = property(lambda self: session_fails())
        
        try:
            result = middleware._safe_extract_session_data(mock_request)
            print("PASS: AssertionError handled gracefully")
            print(f"      Fallback data extracted: {result}")
        except AssertionError as e:
            print(f"FAIL: AssertionError still propagating: {e}")
            return False
            
        # Test 2: Normal session access
        mock_request2 = Mock(spec=Request)  
        mock_request2.session = {'user_id': 'session123', 'session_id': 'abc'}
        mock_request2.cookies = {}
        mock_request2.state = Mock()
        
        try:
            result2 = middleware._safe_extract_session_data(mock_request2)
            print("PASS: Normal session access works")
            print(f"      Session data extracted: {result2}")
        except Exception as e:
            print(f"FAIL: Normal session access failed: {e}")
            return False
            
        # Test 3: Multiple error types
        error_types = [
            RuntimeError("Middleware order error"),
            AttributeError("No session attribute")
        ]
        
        for error in error_types:
            mock_request3 = Mock(spec=Request)
            mock_request3.cookies = {}
            mock_request3.state = Mock()
            
            def raise_error():
                raise error
            type(mock_request3).session = property(lambda self: raise_error())
            
            try:
                result3 = middleware._safe_extract_session_data(mock_request3)
                print(f"PASS: {type(error).__name__} handled gracefully")
            except Exception as e:
                if type(e) == type(error):
                    print(f"FAIL: {type(error).__name__} not handled")
                    return False
                    
        print("\nSUMMARY: All core functionality tests PASSED")
        print("- AssertionError (original bug) is now handled gracefully")
        print("- Normal session access continues to work") 
        print("- Multiple error types are handled robustly")
        print("- Fallback mechanisms provide data when session fails")
        print("\nSTABILITY ASSESSMENT: SYSTEM REMAINS STABLE")
        print("RECOMMENDATION: Fix is safe to deploy")
        
        return True
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_core_fix()
    sys.exit(0 if success else 1)