#!/usr/bin/env python3
"""
Quick analysis script to test Issue #169 SessionMiddleware problems directly.

This script reproduces the exact error conditions without relying on complex test infrastructure.
"""

import os
import sys
import traceback

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_get_session_secret():
    """Test get_session_secret directly."""
    print("=== Testing get_session_secret function ===")
    
    try:
        from netra_backend.app.core.unified_secret_manager import get_session_secret
        print("SUCCESS: Successfully imported get_session_secret")
        
        # Test 1: Missing SECRET_KEY in staging (Issue #169 reproduction)
        print("\n--- Test 1: Missing SECRET_KEY in staging ---")
        os.environ['ENVIRONMENT'] = 'staging'
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        if 'SESSION_SECRET' in os.environ:
            del os.environ['SESSION_SECRET']
            
        try:
            result = get_session_secret("staging")
            print(f"SUCCESS: get_session_secret succeeded: source={result.source.value}, length={result.length}")
            print(f"  Is fallback: {result.is_fallback}, Is generated: {result.is_generated}")
            if result.validation_notes:
                print(f"  Validation notes: {result.validation_notes}")
        except Exception as e:
            print(f"FAILED: get_session_secret failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
        # Test 2: Short SECRET_KEY (< 32 characters)
        print("\n--- Test 2: Short SECRET_KEY ---")
        os.environ['SECRET_KEY'] = 'short_key_123'  # Only 13 characters
        
        try:
            result = get_session_secret("staging")
            print(f"SUCCESS: get_session_secret succeeded with short key: length={result.length}")
            print(f"  Is fallback: {result.is_fallback}, Is generated: {result.is_generated}")
        except Exception as e:
            print(f"FAILED: get_session_secret failed with short key: {e}")
            
    except ImportError as e:
        print(f"FAILED: Failed to import get_session_secret: {e}")
        traceback.print_exc()

def test_middleware_setup():
    """Test middleware setup directly.""" 
    print("\n=== Testing middleware setup ===")
    
    try:
        from fastapi import FastAPI
        from netra_backend.app.core.middleware_setup import setup_session_middleware
        print("SUCCESS: Successfully imported setup_session_middleware")
        
        # Test 1: Setup with missing SECRET_KEY
        print("\n--- Test 1: setup_session_middleware with missing SECRET_KEY ---")
        app = FastAPI()
        os.environ['ENVIRONMENT'] = 'staging'
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
            
        try:
            setup_session_middleware(app)
            print("SUCCESS: setup_session_middleware succeeded")
            
            # Check if SessionMiddleware was actually added
            session_middleware_found = any(
                'SessionMiddleware' in str(middleware.cls) 
                for middleware in app.user_middleware
            )
            print(f"  SessionMiddleware in stack: {session_middleware_found}")
            
        except Exception as e:
            print(f"FAILED: setup_session_middleware failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
        # Test 2: Setup with valid SECRET_KEY
        print("\n--- Test 2: setup_session_middleware with valid SECRET_KEY ---")
        app2 = FastAPI()
        os.environ['SECRET_KEY'] = 'a' * 32 + 'valid_secret_for_testing'
        
        try:
            setup_session_middleware(app2)
            print("SUCCESS: setup_session_middleware succeeded with valid key")
            
            session_middleware_found = any(
                'SessionMiddleware' in str(middleware.cls) 
                for middleware in app2.user_middleware
            )
            print(f"  SessionMiddleware in stack: {session_middleware_found}")
            
        except Exception as e:
            print(f"FAILED: setup_session_middleware failed with valid key: {e}")
            
    except ImportError as e:
        print(f"FAILED: Failed to import middleware setup: {e}")
        traceback.print_exc()

def test_gcp_auth_middleware():
    """Test GCPAuthContextMiddleware defensive patterns."""
    print("\n=== Testing GCPAuthContextMiddleware defensive patterns ===")
    
    try:
        # Try multiple import paths
        middleware_class = None
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
            middleware_class = GCPAuthContextMiddleware
            import_path = "netra_backend.app.middleware"
        except ImportError:
            try:
                from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
                middleware_class = GCPAuthContextMiddleware
                import_path = "shared.middleware"
            except ImportError:
                print("FAILED: GCPAuthContextMiddleware not found in any expected location")
                return
                
        print(f"SUCCESS: Successfully imported GCPAuthContextMiddleware from {import_path}")
        
        middleware = middleware_class()
        
        # Test defensive session access
        print("\n--- Testing defensive session access ---")
        from unittest.mock import MagicMock
        
        request = MagicMock()
        # Remove session attribute to simulate missing SessionMiddleware
        if hasattr(request, 'session'):
            delattr(request, 'session')
            
        # Check if middleware has the expected method
        if hasattr(middleware, '_extract_auth_context'):
            print("SUCCESS: Found _extract_auth_context method")
            method_name = '_extract_auth_context'
        elif hasattr(middleware, 'extract_auth_context'):
            print("SUCCESS: Found extract_auth_context method")
            method_name = 'extract_auth_context'
        else:
            print("FAILED: No auth context extraction method found")
            return
            
        # Test the method (this would normally be async, but we'll try)
        try:
            import asyncio
            
            async def test_defensive():
                try:
                    method = getattr(middleware, method_name)
                    result = await method(request)
                    print(f"SUCCESS: Defensive session access worked: {type(result)}")
                    return True
                except Exception as e:
                    error_msg = str(e).lower()
                    if "sessionmiddleware must be installed" in error_msg:
                        print(f"FAILED: SessionMiddleware error NOT handled defensively: {e}")
                        return False
                    else:
                        print(f"WARNING:  Other error (may be expected): {e}")
                        return True
                        
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(test_defensive())
            loop.close()
            
        except Exception as e:
            print(f"FAILED: Error testing defensive patterns: {e}")
            
    except Exception as e:
        print(f"FAILED: Failed to test GCPAuthContextMiddleware: {e}")
        traceback.print_exc()

def main():
    """Run all tests."""
    print("Issue #169 SessionMiddleware Analysis")
    print("=" * 50)
    
    test_get_session_secret()
    test_middleware_setup()
    test_gcp_auth_middleware()
    
    print("\n" + "=" * 50)
    print("Analysis complete. Check output above for specific failures.")

if __name__ == "__main__":
    main()